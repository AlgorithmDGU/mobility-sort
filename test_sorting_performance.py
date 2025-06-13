#!/usr/bin/env python3
"""
모빌리티 추천 시스템 정렬 성능 분석
"""

import time
import statistics
from typing import List
from mobility_sort_new import (
    Point, Device, loadDevicesFromJson, filterDevices,
    getPrices, computeScore, quicksort, getTmapDistance
)


def extract_scored_devices() -> List[Device]:
    """실제 데이터에서 점수까지 계산된 기기 데이터 추출"""
    src = Point(36.501333, 127.243789)
    dst = Point(36.494690, 127.266267)

    print("데이터 로딩 중...")
    devices = loadDevicesFromJson()
    print(f"총 {len(devices):,}개 기기 로드")

    print("기기 필터링...")
    nearby = filterDevices(devices, src)
    print(f"필터링 후 {len(nearby):,}개 기기")

    if not nearby:
        print("추천 가능한 기기가 없습니다.")
        return []

    print("가격 및 점수 계산...")
    try:
        path_m = getTmapDistance(src, dst)
    except:
        from mobility_sort_new import getDistance
        path_m = getDistance(src, dst) * 1.2

    getPrices(nearby, path_m)
    computeScore(nearby)

    scored_devices = [dev for dev in nearby if hasattr(dev, 'score') and dev.score > 0]
    print(f"점수 계산 완료: {len(scored_devices):,}개 기기")

    return scored_devices


def measure_sorting_time(devices: List[Device]) -> float:
    """정렬 시간 측정"""
    test_devices = []
    for dev in devices:
        new_dev = Device(
            id=dev.id,
            provider=dev.provider,
            lat=dev.lat,
            lon=dev.lon,
            battery=dev.battery
        )
        new_dev.score = dev.score
        new_dev.dist = dev.dist
        new_dev.price = dev.price
        test_devices.append(new_dev)

    start_time = time.perf_counter()
    sorted_devices = quicksort(test_devices)
    end_time = time.perf_counter()

    return end_time - start_time


def create_test_datasets(base_devices: List[Device]) -> dict:
    """기존 데이터를 기반으로 다양한 크기의 테스트 데이터셋 생성"""
    import random

    datasets = {}
    test_sizes = [100, 500, 1000, 2000, 3000, 5000]
    base_count = len(base_devices)

    for size in test_sizes:
        if size <= base_count:
            datasets[size] = random.sample(base_devices, size)
        else:
            extended = []
            while len(extended) < size:
                remaining = size - len(extended)
                if remaining >= base_count:
                    extended.extend(base_devices)
                else:
                    extended.extend(random.sample(base_devices, remaining))

            for i, dev in enumerate(extended):
                dev.id = i + 1

            datasets[size] = extended

    return datasets


def run_performance_tests():
    """실제 데이터를 활용한 성능 테스트"""
    print("QuickSort 성능 분석")
    print("=" * 30)

    scored_devices = extract_scored_devices()
    if not scored_devices:
        return

    datasets = create_test_datasets(scored_devices)
    results = {}

    for size in sorted(datasets.keys()):
        devices = datasets[size]
        times = []

        # 5번 반복 측정
        for run in range(5):
            execution_time = measure_sorting_time(devices)
            times.append(execution_time)

        avg_time = statistics.mean(times)
        results[size] = avg_time

    # 시간 복잡도 계산
    import math
    sizes = sorted(results.keys())
    complexities = {}

    for i in range(1, len(sizes)):
        current_size = sizes[i]
        prev_size = sizes[i - 1]

        current_time = results[current_size]
        prev_time = results[prev_size]

        if prev_time > 0:
            time_ratio = current_time / prev_time
            size_ratio = current_size / prev_size
            actual_complexity = math.log(time_ratio) / math.log(size_ratio)
            complexities[current_size] = actual_complexity

    # 컴팩트 결과 출력
    print(f"\n{'Size':>6} {'Time(ms)':>10} {'Complexity':>11}")
    print("-" * 30)

    for size in sorted(results.keys()):
        time_ms = results[size] * 1000
        complexity = complexities.get(size, "-")
        if complexity != "-":
            print(f"{size:>6,} {time_ms:>10.3f} {complexity:>11.2f}")
        else:
            print(f"{size:>6,} {time_ms:>10.3f} {complexity:>11}")

    # 요약
    if complexities:
        avg_complexity = sum(complexities.values()) / len(complexities)
        print(f"\n평균 복잡도: {avg_complexity:.2f} (이론값: 1.58)")
        status = "우수" if avg_complexity < 1.5 else "양호"
        print(f"성능 평가: {status}")

    return results


if __name__ == "__main__":
    try:
        results = run_performance_tests()
        print("\n분석 완료")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()
