import random
import math

# 원의 중심점 (p0)
lat_center, lon_center = 36.502055, 127.263816

# 원의 반지름 (단위: km)
radius_km = 4.0

# 가우시안 표준편차: 반지름의 1/3 정도로 설정하면
# 대부분의 샘플이 반지름 이내에 밀집됩니다.
# 위·경도 1도당 대략 111km 정도이므로, radius_km를 위도로 환산:
radius_deg_lat = radius_km / 111.0
# 경도 표준편차는 위도 표준편차에서 위도별 보정을 해 줍니다.
lat_std = radius_deg_lat / 3
lon_std = radius_deg_lat / (3 * math.cos(math.radians(lat_center)))


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    두 지점(lat1, lon1)과 (lat2, lon2) 사이의 대원거리(km)를 구하는 하버사인 공식.
    """
    R = 6371.0  # 지구 반경(km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def generate_gauss_in_circle(
    center_lat: float,
    center_lon: float,
    lat_std: float,
    lon_std: float,
    radius_km: float,
) -> tuple[float, float]:
    """
    중심(center_lat, center_lon)을 평균으로 하는 2D 가우시안 분포에서
    하나의 점(lat, lon)을 샘플링하되, 반지름(radius_km) 이내에 들어올 때까지 재시도.
    """
    while True:
        # 가우시안으로 위도, 경도 각각 샘플링
        lat = random.gauss(center_lat, lat_std)
        lon = random.gauss(center_lon, lon_std)

        # 중심과의 거리를 계산
        dist = haversine_distance(center_lat, center_lon, lat, lon)
        if dist <= radius_km:
            return lat, lon


# 열 개의 좌표를 생성해서 리스트에 담기
random_coords = []
for _ in range(10):
    lat, lon = generate_gauss_in_circle(
        lat_center, lon_center, lat_std, lon_std, radius_km
    )
    random_coords.append((lat, lon))

# 결과 출력
for idx, (lat, lon) in enumerate(random_coords, start=1):
    print(f"{idx}: {lat:.6f}, {lon:.6f}")
