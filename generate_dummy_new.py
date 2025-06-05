import random
import json
import os
import math


def generate_dummy_data(
    providername: str = "gbike",
    center: tuple[float, float] = (36.502055, 127.263816),  
    radius_km: float = 4.0,  
    citycode: int = 12,
    cityname: str = "세종특별시",
    code: int = 1,
) -> dict:

    def random_point_in_circle(lat0: float, lon0: float, radius_km: float) -> tuple[float, float]:
        theta = random.random() * 2 * math.pi
        u = random.random()
        r = radius_km * math.sqrt(u)
        R_earth = 6371.0
        delta_lat = (r / R_earth) * (180.0 / math.pi) * math.cos(theta)
        delta_lon = (r / R_earth) * (180.0 / math.pi) * math.sin(theta) / math.cos(lat0 * math.pi / 180.0)

        new_lat = lat0 + delta_lat
        new_lon = lon0 + delta_lon
        return new_lat, new_lon

    num_items = random.randint(400, 600)
    items = []
    for _ in range(num_items):
        
        lat, lon = random_point_in_circle(center[0], center[1], radius_km)

        item = {
            "battery": math.trunc(random.betavariate(5, 3) * 100.0),
            "citycode": citycode,
            "cityname": cityname,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "providername": providername,
            "vehicleid": random.randint(code * 100_000, (code + 1) * 100_000 - 1),
        }
        items.append(item)

    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "items": {"item": items},
                "numOfRows": num_items,
                "pageNo": 1,
                "totalCount": num_items,
            },
        }
    }


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    providers = [
        ("gcoo", 1),
        ("swing", 2),
        ("alpaca", 3),
        ("kickgoing", 4),
        ("xingxing", 5),
        ("socarelecle", 6),
    ]

    
    CENTER_POINT = (36.511779, 127.293400)
    RADIUS_KM = 5.0

    for name, code in providers:
        data = generate_dummy_data(
            providername=name,
            center=CENTER_POINT,
            radius_km=RADIUS_KM,
            code=code
        )
        path = os.path.join("data", f"{name}.json")
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
