import pytest

import app as app_module
from app import MAX_AIRCRAFT, app
from radar.generator import SnapshotError


@pytest.fixture
def client():
    return app.test_client()


def test_index_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Radar de Conflitos Aéreos" in response.get_data(as_text=True)


def test_health(client):
    data = client.get("/api/health").get_json()
    assert data["status"] == "ok" and data["snapshot"]["available"] is True


def test_scan_simulated(client):
    data = client.get("/api/scan?n=200&seed=4").get_json()
    assert len(data["aircraft"]) == 200
    assert data["bands"]
    assert data["source"]["kind"] == "sim" and data["source"]["seed"] == 4
    summary = data["summary"]
    assert summary["aircraft"] == 200
    assert summary["bands_analyzed"] == len(data["bands"])
    assert summary["comparisons"] == sum(band["comparisons"] for band in data["bands"])


def test_scan_is_deterministic(client):
    first = client.get("/api/scan?n=300&seed=9&minutes=12").get_json()
    second = client.get("/api/scan?n=300&seed=9&minutes=12").get_json()
    assert first["bands"] == second["bands"] and first["aircraft"] == second["aircraft"]


def test_scan_snapshot(client):
    data = client.get("/api/scan?source=opensky").get_json()
    assert data["bands"]
    assert data["source"]["kind"] == "opensky"
    assert data["source"]["captured_at_local"] == "2026-11-01T19:28:52-03:00"


def test_scan_model_parameters(client):
    strict = client.get("/api/scan?n=800&threshold_nm=0.5").get_json()["summary"]
    loose = client.get("/api/scan?n=800&threshold_nm=20").get_json()["summary"]
    assert strict["bands_below_threshold"] <= loose["bands_below_threshold"]
    assert client.get("/api/scan?n=800&band_ft=500").get_json()["model"]["band_ft"] == 500


def test_scan_all_pairs(client):
    data = client.get("/api/scan?n=1500&threshold_nm=10&all_pairs=1").get_json()
    assert data["summary"]["close_pairs"] == sum(len(band["close_pairs"]) for band in data["bands"])
    assert "close_pairs" not in client.get("/api/scan?n=100").get_json()["bands"][0]


@pytest.mark.parametrize("query", [
    "n=999999", "n=-5", "n=1", "n=abc", "seed=-1", "minutes=241", "threshold_nm=0.1", "threshold_nm=nan",
    "threshold_nm=inf", "band_ft=750", "source=live", "all_pairs=2",
])
def test_scan_rejects_invalid_parameters(client, query):
    response = client.get(f"/api/scan?{query}")
    assert response.status_code == 400
    assert response.get_json()["error"]


def test_scan_accepts_limits(client):
    assert len(client.get(f"/api/scan?n={MAX_AIRCRAFT}").get_json()["aircraft"]) == MAX_AIRCRAFT
    assert len(client.get("/api/scan?n=2").get_json()["aircraft"]) == 2


def test_snapshot_unavailable_returns_503(client, monkeypatch):
    def broken():
        raise SnapshotError("snapshot indisponível: FileNotFoundError")
    monkeypatch.setattr(app_module, "read_snapshot", broken)
    response = client.get("/api/scan?source=opensky")
    assert response.status_code == 503 and "snapshot" in response.get_json()["error"]
    assert client.get("/api/health").get_json()["snapshot"]["available"] is False
    assert client.get("/api/scan?source=sim").status_code == 200


def test_steps_end_with_combine_of_whole_input(client):
    data = client.get("/api/steps?n=400").get_json()
    assert data["steps"][-1]["kind"] == "combine"
    assert data["steps"][-1]["size"] == len(data["points"])
    assert data["verification"]["ok"] is True
    assert len(data["labels"]) == len(data["points"])


def test_steps_band_selection_and_sampling(client):
    data = client.get("/api/steps?n=3000").get_json()
    assert data["sampled"] is True and len(data["points"]) == 64 and data["band_size"] > 64
    level = data["bands"][0][0]
    chosen = client.get(f"/api/steps?n=3000&band={level}").get_json()
    assert chosen["flight_level"] == level
    assert client.get("/api/steps?n=400&band=999").status_code == 400


def test_steps_without_shared_band(client, monkeypatch):
    planes = [
        {"id": 0, "callsign": "A", "lat": -15, "lon": -50, "altitude_ft": 30000},
        {"id": 1, "callsign": "B", "lat": -16, "lon": -50, "altitude_ft": 32000},
    ]
    monkeypatch.setattr(app_module, "generate_traffic", lambda *args: planes)
    response = client.get("/api/steps")
    assert response.status_code == 400 and response.get_json()["error"]


def test_visualizer_cases(client):
    cases = client.get("/api/visualizer/cases").get_json()["cases"]
    for case in cases:
        data = client.post("/api/visualizer", json={"case": case["id"], "n": 12, "seed": 3}).get_json()
        assert data["verification"]["ok"] is True and data["steps"]


def test_visualizer_custom_points(client):
    data = client.post("/api/visualizer", json={"points": [[0, 0], [5, 5], [5, 6], [20, 1]]}).get_json()
    assert sorted(data["result"]["pair"]) == [1, 2] and data["result"]["distance"] == 1


@pytest.mark.parametrize("body", [
    {"points": [[0, 0]]},
    {"points": [[0, 0], [1]]},
    {"points": [[0, 0], [1, "x"]]},
    {"points": [[0, 0], [1, True]]},
    {"points": [[0, 0], [1, 1e7]]},
    {"points": [[0, 0]] * 65},
    {"case": "inexistente"},
    {"case": "nuvem", "n": 1000},
])
def test_visualizer_rejects_invalid_input(client, body):
    assert client.post("/api/visualizer", json=body).status_code == 400


def test_visualizer_rejects_non_finite_json(client):
    response = client.post("/api/visualizer", data='{"points": [[0, 0], [NaN, 1]]}',
                           content_type="application/json")
    assert response.status_code == 400


def test_catalog(client):
    data = client.get("/api/lab/catalog").get_json()
    ids = [algorithm["id"] for algorithm in data["algorithms"]]
    assert ids == ["closest_pair", "merge_sort", "quick_sort", "quickselect", "inversions", "max_subarray"]
    for algorithm in data["algorithms"]:
        for key in ("problem", "divide", "conquer", "combine", "base_case", "recurrence", "complexity", "pseudocode"):
            assert algorithm[key]


@pytest.mark.parametrize("algorithm", ["merge_sort", "quick_sort", "quickselect", "inversions", "max_subarray"])
def test_lab_run(client, algorithm):
    data = client.post("/api/lab/run", json={"algorithm": algorithm, "scenario": "duplicados", "n": 20,
                                             "seed": 5}).get_json()
    assert data["verification"]["ok"] is True and data["steps"]
    custom = client.post("/api/lab/run", json={"algorithm": algorithm, "values": [3, -1, 2, 2, 0]}).get_json()
    assert custom["input"] == [3, -1, 2, 2, 0] and custom["verification"]["ok"] is True


@pytest.mark.parametrize("body", [
    {"algorithm": "bogo"},
    {"algorithm": "merge_sort", "values": []},
    {"algorithm": "merge_sort", "values": [1, 2.5]},
    {"algorithm": "merge_sort", "scenario": "x"},
    {"algorithm": "merge_sort", "n": 0},
    {"algorithm": "quickselect", "values": [1, 2], "params": {"k": 3}},
    {"algorithm": "quick_sort", "values": [1, 2], "params": {"pivot": "x"}},
    {"algorithm": "quick_sort", "values": [1, 2], "params": [1]},
])
def test_lab_run_rejects_invalid_input(client, body):
    assert client.post("/api/lab/run", json=body).status_code == 400


def test_post_requires_json_object(client):
    assert client.post("/api/lab/run", data="texto").status_code == 400
    assert client.post("/api/lab/run", json=[1, 2]).status_code == 400


def test_body_too_large(client):
    response = client.post("/api/lab/run", data="x" * (300 * 1024), content_type="application/json")
    assert response.status_code == 413 and response.get_json()["error"]


def test_compare(client):
    data = client.get("/api/compare?n=100&scenario=ordenado&repeats=1").get_json()
    assert len(data["rows"]) == 6 and all(row["verified"] for row in data["rows"])
    assert client.get("/api/compare?n=5000").status_code == 400


def test_benchmark(client):
    data = client.get("/api/benchmark?sizes=100,200&repeats=1").get_json()
    assert [row["n"] for row in data["rows"]] == [100, 200]
    quick = client.get("/api/benchmark?algorithm=quick_sort&sizes=100&pivot=aleatorio&scenario=ordenado").get_json()
    assert quick["params"]["pivot"] == "aleatorio" and quick["scenario"] == "ordenado"


@pytest.mark.parametrize("query", [
    "sizes=a,b", "sizes=", "sizes=100&repeats=0", "algorithm=x", "algorithm=merge_sort&scenario=grade",
    "algorithm=closest_pair&scenario=invertido", "algorithm=quick_sort&sizes=5000&pivot=ultimo",
    "algorithm=quick_sort&pivot=mediana_medianas",
])
def test_benchmark_rejects_invalid_parameters(client, query):
    assert client.get(f"/api/benchmark?{query}").status_code == 400


def test_benchmark_busy_returns_429(client):
    from lab import runner
    runner._bench_lock.acquire()
    try:
        assert client.get("/api/benchmark?sizes=100").status_code == 429
    finally:
        runner._bench_lock.release()


def test_exercises(client):
    exercise = client.get("/api/exercises/new?type=inversoes&seed=3").get_json()
    assert exercise["values"] and "expected" not in exercise
    wrong = client.post("/api/exercises/check", json={"type": "inversoes", "seed": 3, "answer": -1}).get_json()
    assert wrong["correct"] is False
    right = client.post("/api/exercises/check", json={"type": "inversoes", "seed": 3,
                                                      "answer": wrong["expected"]}).get_json()
    assert right["correct"] is True
    assert client.post("/api/exercises/check", json={"type": "x", "seed": 1, "answer": 1}).status_code == 400
    assert client.post("/api/exercises/check", json={"type": "inversoes", "seed": 1, "answer": "1"}).status_code == 400


def test_unknown_api_route_is_json_404(client):
    response = client.get("/api/nao-existe")
    assert response.status_code == 404 and response.get_json()["error"] == "recurso não encontrado"
    response = client.delete("/api/scan")
    assert response.status_code == 405 and response.get_json()["error"] == "método não permitido"


def test_internal_errors_do_not_leak_stack_traces(client, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("segredo interno")
    monkeypatch.setattr(app_module, "scan", explode)
    response = client.get("/api/scan?n=10")
    assert response.status_code == 500
    assert response.get_json() == {"error": "erro interno do servidor"}


def test_debug_is_off_by_default():
    assert app.debug is False


def test_health_reports_snapshot_capture(client):
    snapshot = client.get("/api/health").get_json()["snapshot"]
    assert snapshot["captured_at_local"] == "2026-11-01T19:28:52-03:00"


@pytest.mark.parametrize("query", ["threshold_nm=0.5", "threshold_nm=20", "band_ft=500", "band_ft=2000", "minutes=240",
                                   "seed=2147483647", "n=2&seed=0"])
def test_scan_accepts_boundary_values(client, query):
    response = client.get(f"/api/scan?{query}")
    assert response.status_code == 200
    data = response.get_json()
    for band in data["bands"]:
        assert band["alert"] == (band["distance_nm"] < data["model"]["separation_nm"])
        assert all(plane["flight_level"] == band["flight_level"] for plane in band["pair"])


def test_lab_run_rejects_oversized_trace_free_input(client):
    assert client.post("/api/lab/run", json={"algorithm": "merge_sort", "n": 2001}).status_code == 400
    assert client.post("/api/visualizer", json={"case": "nuvem", "n": 65}).status_code == 400
