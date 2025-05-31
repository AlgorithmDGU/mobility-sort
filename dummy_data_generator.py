import random
import json


def generate_dummy_data(
    num_items: int = 214,
    providername: str = "GBIKE",
    lat_range: tuple[float, float] = (36.442401, 36.610608),
    lon_range: tuple[float, float] = (127.209986, 127.36581),
    citycode: int = 12,
    cityname: str = "세종특별시",
) -> dict:

    items = [
        {
            "battery": random.randint(1, 100),                 
            "citycode": citycode,                              
            "cityname": cityname,                              
            "latitude": round(random.uniform(*lat_range), 6),  
            "longitude": round(random.uniform(*lon_range), 6), 
            "providername": providername,                      
            "vehicleid": random.randint(100_000, 999_999),     
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
    dummy_json = generate_dummy_data()
    with open("dummy_sejong.json", "w", encoding="utf-8") as fp:
        json.dump(dummy_json, fp, ensure_ascii=False, indent=2)

    print("✅ dummy_sejong.json 파일이 생성되었습니다.")
