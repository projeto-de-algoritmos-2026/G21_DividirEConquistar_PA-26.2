import threading

import pytest

from lab import runner
from lab.runner import BusyError, LabError, compare_all, make_input, run_benchmark


def test_benchmark_reports_each_size():
    report = run_benchmark(sizes=(100, 200), repeats=2)
    rows = report["rows"]
    assert [row["n"] for row in rows] == [100, 200]
    for row in rows:
        assert len(row["dc"]["samples_ms"]) == 2 and len(row["reference"]["samples_ms"]) == 2
        assert row["dc"]["min_ms"] <= row["dc"]["median_ms"] <= row["dc"]["max_ms"]
        assert row["reference"]["comparisons"] == row["n"] * (row["n"] - 1) // 2
        assert row["reference"]["comparisons"] > row["dc"]["comparisons"]
        assert row["dc"]["verified"] is True
    assert report["environment"]["python"]


def test_benchmark_inputs_are_reproducible():
    assert make_input("closest_pair", "aleatorio", 50, 3) == make_input("closest_pair", "aleatorio", 50, 3)
    first = run_benchmark("inversions", sizes=(300,), repeats=1)
    second = run_benchmark("inversions", sizes=(300,), repeats=1)
    assert first["rows"][0]["dc"]["comparisons"] == second["rows"][0]["dc"]["comparisons"]


@pytest.mark.parametrize("algorithm", runner.ALGORITHMS)
def test_every_algorithm_benchmarks_and_verifies(algorithm):
    scenario = "aleatorio"
    report = run_benchmark(algorithm, sizes=(64, 128), repeats=1, scenario=scenario, params={"seed": 1})
    assert all(row["dc"]["verified"] for row in report["rows"])


def test_reference_skipped_above_limit_is_marked_not_invented():
    report = run_benchmark("merge_sort", sizes=(runner.REFERENCE_MAX_N + 1,), repeats=1, warmup=False)
    row = report["rows"][0]
    assert row["reference"] is None and row["reference_skipped"]
    assert row["dc"]["verified"] is None


def test_time_budget_marks_remaining_sizes_as_skipped():
    report = run_benchmark("merge_sort", sizes=(100, 200, 300), repeats=1, budget_s=0)
    assert report["rows"][0]["dc"] is not None
    assert all(row["skipped"] and row["dc"] is None for row in report["rows"][1:])


@pytest.mark.parametrize("kwargs", [
    {"sizes": ()},
    {"sizes": tuple(range(10, 100, 10))},
    {"sizes": (1,)},
    {"sizes": (runner.BENCH_MAX_N + 1,)},
    {"repeats": 0},
    {"repeats": 99},
    {"algorithm": "x"},
    {"algorithm": "quick_sort", "sizes": (5000,), "params": {"pivot": "ultimo"}},
])
def test_benchmark_rejects_invalid_requests(kwargs):
    with pytest.raises(LabError):
        run_benchmark(**{"sizes": (100,), **kwargs})


def test_quadratic_limit_depends_on_pivot_and_scenario():
    assert runner.max_bench_n("quick_sort", "aleatorio", {"pivot": "aleatorio"}) == runner.BENCH_MAX_N
    assert runner.max_bench_n("quick_sort", "iguais", {"pivot": "aleatorio"}) == runner.BENCH_QUADRATIC_MAX_N
    assert runner.max_bench_n("quickselect", "aleatorio", {"pivot": "ultimo"}) == runner.BENCH_QUADRATIC_MAX_N


def test_concurrent_benchmark_is_rejected():
    acquired = runner._bench_lock.acquire()
    try:
        with pytest.raises(BusyError):
            run_benchmark(sizes=(100,))
        with pytest.raises(BusyError):
            compare_all(n=50)
    finally:
        runner._bench_lock.release()
    assert acquired and not runner._bench_lock.locked()


def test_lock_is_released_after_error():
    with pytest.raises(LabError):
        run_benchmark(sizes=(0,))
    assert run_benchmark(sizes=(50,), repeats=1)["rows"]
    assert not runner._bench_lock.locked()
    assert threading.active_count() >= 1


def test_compare_all_rows():
    report = compare_all("invertido", n=200, seed=4, repeats=1)
    assert [row["algorithm"] for row in report["rows"]] == list(runner.ALGORITHMS)
    for row in report["rows"]:
        assert row["verified"] is True
        assert row["dc_comparisons"] > 0 and row["reference_comparisons"] > 0
    with pytest.raises(LabError):
        compare_all(n=runner.COMPARE_MAX_N + 1)


@pytest.mark.parametrize("algorithm", runner.ALGORITHMS)
def test_operation_counts_are_stable_across_runs(algorithm):
    first = run_benchmark(algorithm, sizes=(80, 160), repeats=1, warmup=False, params={"seed": 5})
    second = run_benchmark(algorithm, sizes=(80, 160), repeats=1, warmup=False, params={"seed": 5})
    for a, b in zip(first["rows"], second["rows"]):
        assert a["dc"]["comparisons"] == b["dc"]["comparisons"]
        assert a["reference"]["comparisons"] == b["reference"]["comparisons"]
        assert all(sample >= 0 for sample in a["dc"]["samples_ms"] + a["reference"]["samples_ms"])
