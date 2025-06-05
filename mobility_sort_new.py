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
MIN_BATTERY_PERCENTAGE = 10

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
    key = provider
    if provider in {"gcoo", "socarelecle"}:
        key = f"{provider}_{'night' if night else 'day'}"
    fee = PROVIDER_FEES[key]
    return int(fee["base"] + fee["per_min"] * math.ceil(minutes))


def getTmapDistance(start: Point, end: Point) -> float:
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
        res = requests.post(url, headers=headers, data=payload, timeout=5)
        res.raise_for_status()
        return res.json()["features"][0]["properties"]["totalDistance"]
    except Exception:
        return getDistance(start, end) * 1.2

def loadDevicesFromJson() -> List[Device]:
    devices: List[Device] = []
    for json_file in DATA_DIR.glob("*.json"):
        provider_name = json_file.stem
        with open(json_file, encoding="utf-8") as f:
            items = json.load(f)["response"]["body"]["items"]["item"]
            for it in items:
                devices.append(
                    Device(
                        id=it["vehicleid"],
                        provider=provider_name,
                        lat=it["latitude"],
                        lon=it["longitude"],
                        battery=it["battery"],
                    )
                )
    return devices

def filterDevices(devices: List[Device], start: Point) -> List[Device]:
    filtered: List[Device] = []
    for dev in devices:
        if dev.battery < MIN_BATTERY_PERCENTAGE:
            continue
        dev.dist = getDistance(start, Point(dev.lat, dev.lon))
        if dev.dist <= RADIUS_METERS:
            filtered.append(dev)
    return filtered


def getPrices(devices: List[Device], path_m: float, now: _dt.datetime):
    minutes = getRideMinutes(path_m)
    night_flag = isNight(now)
    for dev in devices:
        dev.price = calculateFee(dev.provider, minutes, night_flag)

def computeScore(devices: List[Device]):
    prices = [d.price for d in devices]
    p_min, p_max = min(prices), max(prices)
    price_span = p_max - p_min

    for dev in devices:
        if price_span == 0:
            price_score = 100.0
        else:
            price_score = (p_max - dev.price) / price_span * 100
        dist_score = max(0.0, (RADIUS_METERS - dev.dist) / RADIUS_METERS * 100)
        dev.score = price_score * 0.2 + dist_score * 0.8

def quicksort(devices: List[Device]) -> List[Device]:
    n = len(devices)
    if n <= 1:
        return devices
    pivot = devices[n // 2].score
    left = [d for d in devices if d.score > pivot]
    mid = [d for d in devices if math.isclose(d.score, pivot)]
    right = [d for d in devices if d.score < pivot]
    return quicksort(left) + mid + quicksort(right)

if __name__ == "__main__":
    src = Point(36.501333, 127.243789)
    dst = Point(36.494690, 127.266267)

    devices = loadDevicesFromJson()
    nearby = filterDevices(devices, src)

    if not nearby:
        print("추천 가능한 기기가 없습니다.")
    else:
        path_m = getTmapDistance(src, dst)
        getPrices(nearby, path_m)
        computeScore(nearby)

        for dev in quicksort(nearby):
            d = dev.asdict()
            print(
                f"[{d['score']:5.1f}] {d['provider']:<12}"
                f"id={d['device_id']:<7} "
                f"₩{d['price']:<6} "
                f"{d['distance_m']:>5.1f} m  "
                f"{d['location']}"
            )
