import random
import json
import os
import math


def generate_dummy_data(
    providername: str = "gbike",
    # 36.563478, 127.346569  36.460080, 127.240231
    lat_range: tuple[float, float] = (36.460080, 36.563478),
    lon_range: tuple[float, float] = (127.240231, 127.346569),
    citycode: int = 12,
    cityname: str = "세종특별시",
    code: int = 1,
) -> dict:

    num_items = random.randint(400, 499)
    items = [
        {
            "battery": math.trunc(random.betavariate(5,3)*100.0),
            "citycode": citycode,
            "cityname": cityname,
            "latitude": round(random.uniform(*lat_range), 6),  
            "longitude": round(random.uniform(*lon_range), 6),
            "providername": providername,
            "vehicleid": random.randint(code*100_000, (code+1)*100_000 - 1),
        }
        for _ in range(num_items)
    ]

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

    os.makedirs("dummy", exist_ok=True)
    providers = [
        ("gcoo", 1),
        ("swing", 2),
        ("alpaca", 3),
        ("kickgoing", 4),
        ("xingxing", 5),
        ("socarelecle", 6),
    ]

    for name, code in providers:
        data = generate_dummy_data(providername=name, code=code)
        path = os.path.join("data", f"{name}.json")
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    