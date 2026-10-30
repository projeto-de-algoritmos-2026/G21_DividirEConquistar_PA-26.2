"""Comparação empírica entre dividir e conquistar e força bruta."""
import random
import time

from radar.brute_force import closest_pair_brute
from radar.closest_pair import closest_pair

DEFAULT_SIZES = (250, 500, 1000, 2000, 4000)
REPEATS = 3


def measure(solver, points):
    """Retorna o menor tempo (ms) entre as repetições e as comparações feitas."""
    best_ms = float("inf")
    for _ in range(REPEATS):
        start = time.perf_counter()
        result = solver(points)
        best_ms = min(best_ms, (time.perf_counter() - start) * 1000)
    return best_ms, result.comparisons


def run_benchmark(sizes=DEFAULT_SIZES, seed=21):
    rng = random.Random(seed)
    rows = []
    for n in sizes:
        points = [(rng.uniform(0, 5000), rng.uniform(0, 5000)) for _ in range(n)]
        fast_ms, fast_comparisons = measure(closest_pair, points)
        brute_ms, brute_comparisons = measure(closest_pair_brute, points)
        rows.append({
            "n": n,
            "divide_ms": fast_ms,
            "divide_comparisons": fast_comparisons,
            "brute_ms": brute_ms,
            "brute_comparisons": brute_comparisons,
        })
    return rows
