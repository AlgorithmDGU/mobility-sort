from __future__ import annotations

import json
import math
import os
import datetime as _dt
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any

import requests
from dotenv import load_dotenv

@dataclass(slots=True)
class Point:
    x: float  # latitude
    y: float  # longitude


@dataclass(slots=True)
class Device:
    id: int
    provider: str
    lat: float
    lon: float
    battery: int
    price: int = field(init=False, default=0)
    dist: float = field(init=False, default=0.0)
    score: float = field(init=False, default=0.0)

    # dict 변환(helper)
    def asdict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "device_id": self.id,
            "provider": self.provider,
            "price": self.price,
            "distance_m": round(self.dist, 1),
            "location": (self.lat, self.lon),
        }


DATA_DIR = Path(__file__).with_suffix("").parent / "data"
RADIUS_METERS = 500
AVG_SCOOTER_SPEED_M_PER_MIN = 250  # ≈15 km/h

NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6

load_dotenv()
TMAP_KEY = os.getenv("TMAP_KEY", "")

PROVIDER_FEES: Dict[str, Dict[str, Any]] = {
    "alpaca":               {"base": 500,  "per_min": 150},
    "gcoo_day":             {"base": 800,  "per_min": 180},
    "gcoo_night":           {"base": 1200, "per_min": 180},
    "socarelecle_day":      {"base": 500,  "per_min": 150},
    "socarelecle_night":    {"base": 1500, "per_min": 150},
    "xingxing":             {"base": 1500, "per_min": 200},
    "kickgoing":            {"base": 1000, "per_min": 120},
    "swing":                {"base": 1200, "per_min": 150},
}


def getDistance(p1: Point, p2: Point) -> float:
    R = 6_371_000  # m
    phi1, phi2 = map(math.radians, (p1.x, p2.x))
    dphi = math.radians(p2.x - p1.x)
    dlambda = math.radians(p2.y - p1.y)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def isNight(now: _dt.datetime | None = None) -> bool:
    now = now or _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))
    return now.hour >= NIGHT_START_HOUR or now.hour < NIGHT_END_HOUR


def getRideMinutes(distance_m: float) -> float:
    return distance_m / AVG_SCOOTER_SPEED_M_PER_MIN


def calculateFee(provider: str, minutes: float, night: bool) -> int:
    """업체·시간대별 요금(원)."""
    key = provider
    if provider in {"gcoo", "socarelecle"}:
        key = f"{provider}_{'night' if night else 'day'}"
    fee = PROVIDER_FEES[key]
    return int(fee["base"] + fee["per_min"] * math.ceil(minutes))


def getTmapDistance(start: Point, end: Point, timeout: int = 5) -> float:
    if not TMAP_KEY:  # 키가 없으면 바로 보정값 반환
        return getDistance(start, end) * 1.2

    headers = {"appKey": TMAP_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "startX": str(start.y),
        "startY": str(start.x),
        "endX": str(end.y),
        "endY": str(end.x),
        "reqCoordType": "WGS84GEO",
        "startName": "출발",
        "endName": "도착",
        "searchOption": "30",
    }
    url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=timeout)
        res.raise_for_status()
        return res.json()["features"][0]["properties"]["totalDistance"]
    except Exception:
        return getDistance(start, end) * 1.2

class MobilityRecommender:
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.devices: List[Device] = self._load_devices(data_dir)

    @staticmethod
    def _load_devices(data_dir: Path) -> List[Device]:
        devices: List[Device] = []
        for json_f in data_dir.glob("*.json"):
            provider = json_f.stem  # alpaca, gcoo …
            with open(json_f, encoding="utf-8") as f:
                items = json.load(f)["response"]["body"]["items"]["item"]
                for it in items:
                    devices.append(
                        Device(
                            id=it["vehicleid"],
                            provider=provider,
                            lat=it["latitude"],
                            lon=it["longitude"],
                            battery=it["battery"],
                        )
                    )
        return devices

    def recommend(
        self,
        start: Point,
        end: Point,
        radius_m: float = RADIUS_METERS,
        battery_min: int = 10,
    ) -> List[Device]:
        path_m = getTmapDistance(start, end)
        minutes = getRideMinutes(path_m)
        night = isNight()

        candidates: List[Device] = []
        for dev in self.devices:
            if dev.battery < battery_min:
                continue
            dev.dist = getDistance(start, Point(dev.lat, dev.lon))
            if dev.dist > radius_m:
                continue
            dev.price = calculateFee(dev.provider, minutes, night)
            candidates.append(dev)

        if not candidates:
            return []  # 근처 기기 없음

        prices = [d.price for d in candidates]
        p_min, p_max = min(prices), max(prices)

        for d in candidates:
            price_score = 100 if p_max == p_min else (p_max - d.price) / (p_max - p_min) * 100
            dist_score = (radius_m - d.dist) / radius_m * 100
            d.score = price_score * 0.4 + dist_score * 0.6

        return self._quicksort(candidates)

    def _quicksort(self, arr: List[Device]) -> List[Device]:
        if len(arr) <= 1:
            return arr
        pivot = arr[len(arr) // 2].score
        left = [x for x in arr if x.score > pivot]
        mid = [x for x in arr if math.isclose(x.score, pivot)]
        right = [x for x in arr if x.score < pivot]
        return self._quicksort(left) + mid + self._quicksort(right)


if __name__ == "__main__":
    src = Point(36.501333, 127.243789)
    dst = Point(36.494690, 127.266267)

    recommender = MobilityRecommender()
    results = recommender.recommend(src, dst)

    if not results:
        print("추천 가능한 기기가 없습니다.")
    else:
        #for dev in results[:10]:
        for dev in results:
            d = dev.asdict()
            print(
                f"[{d['score']:5.1f}] {d['provider']:<12}"
                f"id={d['device_id']:<7} "
                f"₩{d['price']:<6} "
                f"{d['distance_m']:>5.1f} m  "
                f"{d['location']}"
            )
