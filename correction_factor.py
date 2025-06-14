import json
import os
from typing import List
from mobility_sort_new import Point, getDistance, getTmapDistance

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAGO_DIR = os.path.join(BASE_DIR, "tago_response")

DATA_PATHS = [
    os.path.join(TAGO_DIR, "tago_gbike.json"),
]

SRC = Point(36.501333, 127.243789)  # 기준 사용자 위치


def load_devices_from_file(file_path: str) -> List[Point]:
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            items = data["response"]["body"]["items"]["item"]
            return [Point(float(item["latitude"]), float(item["longitude"])) for item in items]
    except:
        return []


def calculate_correction_factors():
    ratios = []

    for path in DATA_PATHS:
        if not os.path.exists(path):
            continue

        devices = load_devices_from_file(path)
        for dev_point in devices:
            dist_hav = getDistance(SRC, dev_point)
            if dist_hav <= 5:
                continue

            dist_tmap = getTmapDistance(SRC, dev_point)
            ratios.append(dist_tmap / dist_hav)

    if not ratios:
        return None

    return sum(ratios) / len(ratios)


if __name__ == "__main__":
    correction_factor = calculate_correction_factors()
    if correction_factor:
        print(f"{correction_factor:.4f}")
