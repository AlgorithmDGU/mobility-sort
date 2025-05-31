import random
import json
import os


def generate_dummy_data(
    providername: str = "gbike",
    lat_range: tuple[float, float] = (36.406900, 36.601200),
    lon_range: tuple[float, float] = (127.128600, 127.370400),
    citycode: int = 12,
    cityname: str = "세종특별시",
    code: int = 1,
) -> dict:

    num_items = random.randint(200, 299)
    items = [
        {
            "battery": random.randint(1, 100),                 
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
        ("gbike", 1),
        ("swing", 2),
        ("alpaca", 3),
        ("kickgoing", 4),
        ("xingxing", 5),
        ("socarelecle", 6),
    ]

    for name, code in providers:
        data = generate_dummy_data(providername=name, code=code)
        path = os.path.join("dummy", f"{name}.json")
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    