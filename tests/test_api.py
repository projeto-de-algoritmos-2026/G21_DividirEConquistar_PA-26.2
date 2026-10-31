import pytest

from app import MAX_AIRCRAFT, app


@pytest.fixture
def client():
    return app.test_client()


def test_scan_simulated(client):
    data = client.get("/api/scan?n=200&seed=4").get_json()
    assert len(data["aircraft"]) == 200
    assert data["bands"]


def test_scan_snapshot(client):
    data = client.get("/api/scan?source=opensky").get_json()
    assert data["bands"]


def test_scan_limits_aircraft_count(client):
    assert len(client.get("/api/scan?n=999999").get_json()["aircraft"]) == MAX_AIRCRAFT
    assert len(client.get("/api/scan?n=-5").get_json()["aircraft"]) == 2


def test_scan_ignores_invalid_number(client):
    assert len(client.get("/api/scan?n=abc").get_json()["aircraft"]) == 400


def test_steps_end_with_combine_of_whole_input(client):
    data = client.get("/api/steps?n=400").get_json()
    assert data["steps"][-1]["kind"] == "combine"
    assert data["steps"][-1]["size"] == len(data["points"])


def test_steps_without_shared_band(client, monkeypatch):
    planes = [
        {"callsign": "A", "lat": -15, "lon": -50, "altitude_ft": 30000},
        {"callsign": "B", "lat": -16, "lon": -50, "altitude_ft": 32000},
    ]
    monkeypatch.setattr("app.generate_traffic", lambda *args: planes)
    assert client.get("/api/steps").status_code == 400
