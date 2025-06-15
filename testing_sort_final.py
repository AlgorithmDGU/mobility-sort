import time
import math
import random
import numpy as np
import gc
from statistics import mean
from typing import List, Callable, Dict

from mobility_sort_new import (
    Point, Device, loadDevicesFromJson, filterDevices,
    getPrices, computeScore, getTmapDistance, getDistance
)


def extract_scored_devices() -> List[Device]:
    src = Point(36.501333, 127.243789)
    dst = Point(36.494690, 127.266267)
    devices = filterDevices(loadDevicesFromJson(), src)
    try:
        path_m = getTmapDistance(src, dst)
    except Exception:
        path_m = getDistance(src, dst) * 1.2
    getPrices(devices, path_m)
    computeScore(devices)
    return [d for d in devices if d.score > 0]


def expand_devices(base: List[Device], target: int) -> List[Device]:
    base_n = len(base)
    if target <= base_n:
        return random.sample(base, target)

    extra = target - base_n
    idx = np.arange(extra) % base_n
    lat_off = np.random.uniform(-0.0005, 0.0005, extra)
    lon_off = np.random.uniform(-0.0005, 0.0005, extra)
    bat_off = np.random.randint(-5, 6, extra)
    mult = np.random.uniform(0.95, 1.05, (extra, 3))

    clones = []
    for i, src_idx in enumerate(idx):
        o = base[src_idx]
        d = Device(
            id=10_000_000 + i,
            provider=o.provider,
            lat=o.lat + lat_off[i],
            lon=o.lon + lon_off[i],
            battery=int(np.clip(o.battery + bat_off[i], 0, 100)),
        )
        d.dist = o.dist * mult[i, 0]
        d.price = o.price * mult[i, 1]
        d.score = o.score * mult[i, 2]
        clones.append(d)
    return base + clones


def quick_sort(arr: List[Device]) -> List[Device]:
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2].score
    left = [d for d in arr if d.score > pivot]
    mid = [d for d in arr if math.isclose(d.score, pivot)]
    right = [d for d in arr if d.score < pivot]
    return quick_sort(left) + mid + quick_sort(right)


def heap_sort(arr: List[Device]) -> List[Device]:
    import heapq
    h = [(-d.score, i, d) for i, d in enumerate(arr)]
    heapq.heapify(h)
    out = []
    while h:
        out.append(heapq.heappop(h)[2])
    return out


def bucket_sort(arr: List[Device], k: int = 10) -> List[Device]:
    if not arr:
        return []
    scores = np.fromiter((d.score for d in arr), float)
    s_min, s_max = scores.min(), scores.max()
    span = (s_max - s_min) / k or 1
    bins = np.clip(((scores - s_min) / span).astype(int), 0, k - 1)

    buckets: List[List[Device]] = [[] for _ in range(k)]
    for dev, b in zip(arr, bins):
        buckets[b].append(dev)

    out: List[Device] = []
    for b in buckets:
        out.extend(sorted(b, key=lambda d: d.score, reverse=True))
    return out


def measure(sort_fn: Callable[[List[Device]], List[Device]], data: List[Device]) -> float:
    gc.collect()
    start = time.perf_counter()
    sort_fn(data.copy())
    return time.perf_counter() - start


def run_tests(
    name: str,
    sort_fn: Callable[[List[Device]], List[Device]],
    base: List[Device],
    sizes=(100, 1_000, 10_000, 20_000, 100_000, 200_000, 500_000, 1_000_000, 2_000_000),
) -> Dict[int, float]:
    print(f"\n{name} 성능 분석\n" + "=" * 30)
    datasets = {
        n: (random.sample(base, n) if n <= len(base) else expand_devices(base, n))
        for n in sizes
    }
    times: Dict[int, float] = {}
    comp: Dict[int, float] = {}
    ordered = sorted(datasets)

    for i, n in enumerate(ordered):
        measures = [measure(sort_fn, datasets[n]) for _ in range(3)]
        times[n] = np.median(measures)
        if i:
            p = ordered[i - 1]
            comp[n] = math.log(times[n] / times[p]) / math.log(n / p)

    print(f"{'Size':>9} {'Time(s)':>10} {'Complexity':>11}")
    print("-" * 30)
    for n in ordered:
        c = comp.get(n, "-")
        print(f"{n:>9,} {times[n]:>10.4f} {c if c == '-' else f'{c:>11.3f}'}")
    if comp:
        print(f"\n평균 복잡도: {mean(comp.values()):.3f}\n")
    return times


if __name__ == "__main__":
    devices = extract_scored_devices()
    if not devices:
        print("추천 가능한 기기가 없습니다.")
    else:
        quick = run_tests("QuickSort", quick_sort, devices)
        heap = run_tests("HeapSort", heap_sort, devices)
        bucket = run_tests("BucketSort", bucket_sort, devices)

        def avg(d): return mean(d.values())

        print("[성능 요약 (단위: 초)]")
        print(f"QuickSort 평균시간:  {avg(quick):.5f} s")
        print(f"HeapSort 평균시간:   {avg(heap):.5f} s")
        print(f"BucketSort 평균시간: {avg(bucket):.5f} s")
