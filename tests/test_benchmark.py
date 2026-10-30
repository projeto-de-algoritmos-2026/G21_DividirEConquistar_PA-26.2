from radar.benchmark import run_benchmark


def test_benchmark_reports_each_size():
    rows = run_benchmark(sizes=(100, 200))
    assert [row["n"] for row in rows] == [100, 200]
    assert all(row["brute_comparisons"] > row["divide_comparisons"] for row in rows)
