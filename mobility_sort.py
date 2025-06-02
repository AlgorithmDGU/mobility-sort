from __future__ import annotations
import argparse
import concurrent.futures as fut
import datetime as _dt
import json
import math
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
import requests
from dotenv import load_dotenv


DATA_DIR = Path(__file__).with_suffix("").parent / "data"
RADIUS_METERS = 100  # search radius around start position
AVG_SCOOTER_SPEED_M_PER_MIN = 250  # ≈15 km/h

# Day/night window (KST). 22:00‑06:00 is treated as “night”.
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6

load_dotenv()
TMAP_KEY = os.getenv("TMAP_KEY")

# Provider fee tables ---------------------------------------------------------
PROVIDER_FEES: Dict[str, Dict[str, Any]] = {
    "alpaca":       {"base": 500,  "per_min": 150},
    "gcoo_day":     {"base": 800,  "per_min": 180},
    "gcoo_night":   {"base": 1200, "per_min": 180},
    "socarelecle_day":   {"base": 500,  "per_min": 150},
    "socarelecle_night": {"base": 1500, "per_min": 150},
    "xingxing":     {"base": 1500, "per_min": 200},
    "kickgoing":    {"base": 1000, "per_min": 120},
    "swing":        {"base": 1200, "per_min": 150},
}

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000  # Earth radius in m
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def is_night(now: _dt.datetime | None = None) -> bool:
    now = now or _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))  # KST
    return now.hour >= NIGHT_START_HOUR or now.hour < NIGHT_END_HOUR


def estimate_ride_minutes(distance_m: int) -> float:
    """Convert route distance to ride time (minutes) given an average speed."""
    return distance_m / AVG_SCOOTER_SPEED_M_PER_MIN

def calc_fee(provider: str, ride_minutes: float, night: bool) -> int:
    key = provider
    if provider in {"gcoo", "socarelecle"}:
        key = f"{provider}_{'night' if night else 'day'}"
    fees = PROVIDER_FEES[key]
    return int(fees["base"] + fees["per_min"] * math.ceil(ride_minutes))





def tmap_distance_time(start: Tuple[float, float], end: Tuple[float, float], *, timeout: int = 5) -> Tuple[int, int]:
    headers = {"appKey": TMAP_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    body = {
        "startX": str(start[1]),
        "startY": str(start[0]),
        "endX": str(end[1]),
        "endY": str(end[0]),
        "reqCoordType": "WGS84GEO",
        "startName": "출발",
        "endName": "도착",
        "searchOption": "30",
    }
    try:
        _TMAP_URL = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
        r = requests.post(_TMAP_URL, headers=headers, data=body, timeout=timeout)
        r.raise_for_status()
        features = r.json()["features"]
        props = features[0]["properties"]
        return props["totalDistance"], props["totalTime"]
    except Exception:
        # Fallback: straight‑line * 1.2 safety factor, walk speed 4 km/h.
        dist = haversine(*start, *end) * 1.2
        sec = dist / (4_000 / 3600)
        return int(dist), int(sec)

def load_devices() -> List[Dict[str, Any]]:
    devices: List[Dict[str, Any]] = []
    for fp in DATA_DIR.glob("*.json"):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            for item in data["response"]["body"]["items"]["item"]:
                if item["battery"] <= 15:
                    continue  # battery gate
                devices.append(item)
        except Exception as e:
            print(f"⚠️  Skip {fp}: {e}")
    return devices


def weight_device(device: Dict[str, Any], walk_m: float, cost: int) -> float:
    """Composite weight: higher is better."""
    # Simple hyperparameters—tweak as needed.
    return 1_000 / (cost + 1) + 10_000 / (walk_m + 1)


def sort_devices(devices: List[Dict[str, Any]], *, algo: str = "built_in") -> List[Dict[str, Any]]:
    if algo == "bubble":
        arr = devices[:]
        n = len(arr)
        for i in range(n):
            for j in range(0, n - i - 1):
                if arr[j]["weight"] < arr[j + 1]["weight"]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
        return arr
    elif algo == "quick":
        if not devices:
            return []
        pivot = devices[0]
        less = [d for d in devices[1:] if d["weight"] >= pivot["weight"]]
        greater = [d for d in devices[1:] if d["weight"] < pivot["weight"]]
        return sort_devices(less, algo="quick") + [pivot] + sort_devices(greater, algo="quick")
    # built‑in Timsort fallback
    return sorted(devices, key=lambda d: d["weight"], reverse=True)


def recommend(start: Tuple[float, float], end: Tuple[float, float], *, algo: str = "built_in") -> List[Dict[str, Any]]:
    devices = load_devices()
    near: List[Dict[str, Any]] = []
    for dev in devices:
        d = haversine(start[0], start[1], dev["latitude"], dev["longitude"])
        if d <= RADIUS_METERS:
            near.append({**dev, "walk_dist": d})
    if not near:
        return []

    # Estimate ride time once per query.
    route_dist, _ = tmap_distance_time(start, end)  # sec not needed
    ride_min = estimate_ride_minutes(route_dist)
    night_flag = is_night()

    for dev in near:
        provider = dev["providername"].lower()
        cost = calc_fee(provider, ride_min, night_flag)
        dev["cost"] = cost
        dev["weight"] = weight_device(dev, dev["walk_dist"], cost)

    ranked = sort_devices(near, algo=algo)
    return ranked


# def _simulate_user(args: Tuple[int, Tuple[float, float], Tuple[float, float], str, str])) -> None:  # type: ignore
#     idx, start, end, algo, key = args
#     recommend(start, end, algo=algo)


# def load_test(n_users: int, start: Tuple[float, float], end: Tuple[float, float], *, algo: str) -> float:
#     """Spawn *n_users* parallel recommend() calls and return wall‑time (s)."""
#     args = [(i, start, end, algo) for i in range(n_users)]
#     t0 = time.perf_counter()
#     with fut.ThreadPoolExecutor() as ex:
#         list(ex.map(_simulate_user, args))
#     return time.perf_counter() - t0


def parse_latlon(text: str) -> Tuple[float, float]:
    try:
        lat, lon = map(float, text.split(","))
        return lat, lon
    except ValueError:
        raise argparse.ArgumentTypeError("Must be 'lat,lon' (float,float)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Shared mobility recommender")
    ap.add_argument("--start", type=parse_latlon, required=True, help="start 'lat,lon'")
    ap.add_argument("--end", type=parse_latlon, required=True, help="end 'lat,lon'")
    ap.add_argument("--algo", choices=["built_in", "bubble", "quick"], default="built_in")
    # ap.add_argument("--users", type=int, default=0, help="run N‑user load test")
    ns = ap.parse_args()
    recs = recommend(ns.start, ns.end, algo=ns.algo)
    if not recs:
        print("No available vehicles within 100 m.")
        exit(0)
    print("Top recommendations: (vehicleid | provider | walk_m | cost₩ | battery%)")
    for d in recs[:5]:
        print(f"{d['vehicleid']:<10} {d['providername']:<12} {d['walk_dist']:.1f}m  ₩{d['cost']}  {d['battery']}%")

    # if ns.users > 0:
    #     dur = load_test(ns.users, ns.start, ns.end, algo=ns.algo)
    #     print(f"🏁 {ns.users} users finished in {dur:.2f} s  (avg {dur/ns.users:.3f} s/user)")
    # else:
    #     recs = recommend(ns.start, ns.end, algo=ns.algo)
    #     if not recs:
    #         print("No available vehicles within 100 m.")
    #         exit(0)
    #     print("Top recommendations: (vehicleid | provider | walk_m | cost₩ | battery%)")
    #     for d in recs[:5]:
    #         print(f"{d['vehicleid']:<10} {d['providername']:<12} {d['walk_dist']:.1f}m  ₩{d['cost']}  {d['battery']}%")