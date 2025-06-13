import time
import statistics
import math
from typing import List
from mobility_sort_new import (
    Point, Device, loadDevicesFromJson, filterDevices,
    getPrices, computeScore, quicksort, getTmapDistance
)
import heapq
import copy
import random


def extract_scored_devices() -> List[Device]:
    src = Point(36.501333, 127.243789)
    dst = Point(36.494690, 127.266267)

    devices = loadDevicesFromJson()
    nearby = filterDevices(devices, src)
    if not nearby:
        return []

    try:
        path_m = getTmapDistance(src, dst)
    except:
        from mobility_sort_new import getDistance
        path_m = getDistance(src, dst) * 1.2

    getPrices(nearby, path_m)
    computeScore(nearby)

    return [dev for dev in nearby if hasattr(dev, 'score') and dev.score > 0]


def expand_devices_with_variation(base_devices: List[Device], target_size: int) -> List[Device]:
    """기존 기기 데이터를 기반으로 유사하지만 약간씩 다른 기기들을 생성"""
    expanded = []
    base_count = len(base_devices)

    for i in range(target_size):
        orig = base_devices[i % base_count]
        new_dev = Device(
            id=10_000_000 + i,
            provider=orig.provider,
            lat=orig.lat + random.uniform(-0.0005, 0.0005),
            lon=orig.lon + random.uniform(-0.0005, 0.0005),
            battery=max(0, min(100, orig.battery + random.randint(-5, 5)))
        )
        new_dev.dist = orig.dist * random.uniform(0.95, 1.05)
        new_dev.price = orig.price * random.uniform(0.95, 1.05)
        new_dev.score = orig.score * random.uniform(0.95, 1.05)
        expanded.append(new_dev)

    return expanded


def quick_sort_wrapper(devices):
    return quicksort(copy.deepcopy(devices))


def heap_sort_wrapper(devices):
    heap = [(-dev.score, i, dev) for i, dev in enumerate(devices)]
    heapq.heapify(heap)
    result = []
    while heap:
        _, _, dev = heapq.heappop(heap)
        result.append(dev)
    return result


def bucket_sort_wrapper(devices, bucket_count=10):
    if not devices:
        return []
    min_score = min(dev.score for dev in devices)
    max_score = max(dev.score for dev in devices)
    range_size = (max_score - min_score) / bucket_count or 1
    buckets: List[List[Device]] = [[] for _ in range(bucket_count)]
    for dev in devices:
        idx = int((dev.score - min_score) / range_size)
        if idx == bucket_count:
            idx -= 1
        buckets[idx].append(dev)
    sorted_devices: List[Device] = []
    for bucket in buckets:
        sorted_devices.extend(sorted(bucket, key=lambda d: d.score, reverse=True))
    return sorted_devices


def measure_sorting_time(sort_func, devices: List[Device]) -> float:
    test_devices = copy.deepcopy(devices)
    start_time = time.perf_counter()
    _ = sort_func(test_devices)
    end_time = time.perf_counter()
    return end_time - start_time


def run_tests(name: str, sort_func, devices: List[Device], theory_complexity: float, test_sizes=[100, 1000, 5000, 10000, 20000, 50000]):
    print(f"{name} 성능 분석\n" + "=" * 30)
    base_count = len(devices)
    datasets = {}
    for size in test_sizes:
        if size <= base_count:
            datasets[size] = random.sample(devices, size)
        else:
            datasets[size] = expand_devices_with_variation(devices, size)

    results = {}
    complexities = {}

    for i, size in enumerate(sorted(datasets.keys())):
        times = [measure_sorting_time(sort_func, datasets[size]) for _ in range(5)]
        avg_time = statistics.mean(times)
        results[size] = avg_time

        if i > 0:
            prev_size = sorted(datasets.keys())[i - 1]
            prev_time = results[prev_size]
            if avg_time > prev_time:
                r = math.log(avg_time / prev_time) / math.log(size / prev_size)
                complexities[size] = r

    print(f"{'Size':>6} {'Time(s)':>10} {'Complexity':>11}")
    print("-" * 30)
    for size in sorted(results):
        time_s = results[size]
        c = complexities.get(size, '-')
        if c != '-':
            print(f"{size:>6,} {time_s:>10.4f} {c:>11.2f}")
        else:
            print(f"{size:>6,} {time_s:>10.4f} {c:>11}")

    if complexities:
        avg_c = sum(complexities.values()) / len(complexities)
        print(f"\n평균 복잡도: {avg_c:.2f} (이론값: {theory_complexity:.2f})")
        status = "우수" if avg_c < theory_complexity else "양호"
        print(f"성능 평가: {status}")
    print()
    return results


def compare_all():
    devices = extract_scored_devices()
    if not devices:
        print("추천 가능한 기기가 없습니다.")
        return

    q = run_tests("QuickSort", quick_sort_wrapper, devices, theory_complexity=1.58)
    h = run_tests("HeapSort", heap_sort_wrapper, devices, theory_complexity=1.15)
    b = run_tests("BucketSort", bucket_sort_wrapper, devices, theory_complexity=1.00)

    def avg(d): return sum(d.values()) / len(d)

    print("[성능 요약 (단위: 초)]")
    print(f"QuickSort 평균시간:  {avg(q):.4f} s")
    print(f"HeapSort 평균시간:   {avg(h):.4f} s")
    print(f"BucketSort 평균시간: {avg(b):.4f} s")


if __name__ == '__main__':
    compare_all()
