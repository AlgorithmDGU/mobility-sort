import random

lat_min, lat_max = 36.460080, 36.563478
lon_min, lon_max = 127.240231, 127.346569

lat_center = (lat_min + lat_max) / 2
lon_center = (lon_min + lon_max) / 2

lat_std = (lat_max - lat_min) / 6
lon_std = (lon_max - lon_min) / 6

def generate_gauss_in_range(center: float, std: float, minimum: float, maximum: float) -> float:
    while True:
        val = random.gauss(center, std)
        if minimum <= val <= maximum:
            return val

random_coords = []
for _ in range(10):
    lat = generate_gauss_in_range(lat_center, lat_std, lat_min, lat_max)
    lon = generate_gauss_in_range(lon_center, lon_std, lon_min, lon_max)
    random_coords.append((lat, lon))

for idx, (lat, lon) in enumerate(random_coords, start=1):
    print(f"{idx}: {lat:.6f}, {lon:.6f}")
