import itertools
import json

import pytest

from radar.bands import flight_level, group_by_band, scan
from radar.generator import SnapshotError, generate_traffic, load_snapshot, read_snapshot
from radar.geo import KM_PER_NM, haversine_km, project


def plane(callsign, lat, lon, altitude_ft, ident=None):
    return {"id": ident, "callsign": callsign, "lat": lat, "lon": lon, "altitude_ft": altitude_ft}


def test_haversine_one_degree_of_latitude():
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.19, abs=0.01)


def test_project_preserves_latitude_distance():
    assert project(-14, -52)[1] - project(-15, -52)[1] == pytest.approx(111.19, abs=0.01)


def test_flight_level_rounds_to_thousand_feet():
    assert flight_level(36100) == 360
    assert flight_level(35900) == 360


def test_flight_level_rounds_half_up_consistently():
    # round() do Python arredondava 36.500 para baixo e 37.500 para cima.
    assert flight_level(36500) == 370
    assert flight_level(37500) == 380
    assert flight_level(36499) == 360


def test_flight_level_with_other_band_widths():
    assert flight_level(36300, 500) == 365
    assert flight_level(36900, 2000) == 360
    assert flight_level(37000, 2000) == 380


def test_group_by_band_separates_levels():
    bands = group_by_band([plane("A", 0, 0, 36000), plane("B", 0, 0, 37000)])
    assert sorted(bands) == [360, 370]


def test_aircraft_in_different_levels_are_not_in_conflict():
    bands, summary = scan([plane("A", -15, -50, 36000), plane("B", -15, -50, 37000)])
    assert bands == []
    assert summary["bands_single"] == 2 and summary["min_distance_nm"] is None


def test_alerts_below_separation():
    close = 4 * KM_PER_NM / 111.19
    bands, summary = scan([plane("A", -15, -50, 36000), plane("B", -15 + close, -50, 36000)])
    assert bands[0]["alert"] is True
    assert bands[0]["distance_nm"] == pytest.approx(4, abs=0.01)
    assert summary["bands_below_threshold"] == 1


def test_no_alert_above_separation():
    far = 6 * KM_PER_NM / 111.19
    bands, _ = scan([plane("A", -15, -50, 36000), plane("B", -15 + far, -50, 36000)])
    assert bands[0]["alert"] is False


def test_threshold_is_configurable():
    far = 6 * KM_PER_NM / 111.19
    bands, summary = scan([plane("A", -15, -50, 36000), plane("B", -15 + far, -50, 36000)], separation_nm=8)
    assert bands[0]["alert"] is True and summary["separation_nm"] == 8


def test_band_width_changes_grouping():
    aircraft = [plane("A", -15, -50, 36000), plane("B", -15.01, -50, 36400)]
    assert scan(aircraft, band_ft=500)[0] == []
    assert len(scan(aircraft, band_ft=1000)[0]) == 1


def test_traffic_is_reproducible_by_seed():
    assert generate_traffic(50, seed=7) == generate_traffic(50, seed=7)
    assert generate_traffic(50, seed=7) != generate_traffic(50, seed=8)


def test_traffic_moves_with_time_but_keeps_flights():
    before, after = generate_traffic(20, seed=7), generate_traffic(20, seed=7, minutes=10)
    assert before != after
    assert [p["callsign"] for p in before] == [p["callsign"] for p in after]
    assert [p["id"] for p in before] == list(range(20))


def brute_band_minimum(planes):
    return min(haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) for a, b in itertools.combinations(planes, 2))


@pytest.mark.parametrize("aircraft", [generate_traffic(600, seed=3), generate_traffic(1500, seed=1), load_snapshot()])
def test_scan_matches_brute_force_geodesic(aircraft):
    bands, summary = scan(aircraft)
    assert bands
    groups = group_by_band(aircraft)
    for band in bands:
        assert band["distance_km"] == pytest.approx(brute_band_minimum(groups[band["flight_level"]]), abs=1e-9)
    assert summary["bands_analyzed"] == len(bands)
    assert summary["min_distance_nm"] == min(band["distance_nm"] for band in bands)


def test_scan_regression_projection_error():
    """Seed 1, n = 1500, FL280: a versão antiga relatava 12,508 km; o mínimo real é 12,470 km."""
    bands, summary = scan(generate_traffic(1500, seed=1))
    fl280 = next(band for band in bands if band["flight_level"] == 280)
    assert fl280["distance_km"] == pytest.approx(12.470, abs=0.001)
    assert summary["projection_corrections"] >= 1


def test_all_pairs_lists_every_pair_below_threshold():
    aircraft = generate_traffic(1200, seed=5)
    bands, summary = scan(aircraft, separation_nm=10, all_pairs=True)
    by_id = {p["id"]: p for p in aircraft}
    total = 0
    for band, (level, planes) in zip(bands, sorted((k, v) for k, v in group_by_band(aircraft).items() if len(v) > 1)):
        expected = {tuple(sorted((a["id"], b["id"]))) for a, b in itertools.combinations(planes, 2)
                    if haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) < 10 * KM_PER_NM}
        got = {tuple(sorted(pair["ids"])) for pair in band["close_pairs"]}
        assert got == expected
        assert band["alert"] == bool(expected)
        total += len(got)
        for pair in band["close_pairs"]:
            a, b = (by_id[i] for i in pair["ids"])
            assert pair["distance_nm"] < 10
    assert summary["close_pairs"] == total


def test_snapshot_metadata():
    aircraft, meta = read_snapshot()
    assert meta["kind"] == "opensky" and meta["records"] == len(aircraft) + meta["discarded"]
    assert meta["captured_at_utc"].startswith("2026-11-01T22:28:52")
    assert meta["captured_at_local"].endswith("-03:00")
    assert [p["id"] for p in aircraft] == list(range(len(aircraft)))


def test_snapshot_missing_or_invalid(tmp_path):
    with pytest.raises(SnapshotError):
        read_snapshot(tmp_path / "nao_existe.json")
    broken = tmp_path / "quebrado.json"
    broken.write_text("{nao é json", encoding="utf-8")
    with pytest.raises(SnapshotError):
        read_snapshot(broken)


def test_snapshot_discards_invalid_records(tmp_path):
    path = tmp_path / "snap.json"
    path.write_text(json.dumps({"aircraft": [
        {"callsign": "OK1", "lat": -15, "lon": -47, "altitude_ft": 30000},
        {"callsign": "NAN", "lat": "nan", "lon": -47, "altitude_ft": 30000},
        {"callsign": "FORA", "lat": 95, "lon": -47, "altitude_ft": 30000},
        {"callsign": "SEMALT", "lat": -15, "lon": -47},
    ]}), encoding="utf-8")
    aircraft, meta = read_snapshot(path)
    assert [p["callsign"] for p in aircraft] == ["OK1"]
    assert meta["discarded"] == 3 and "captured_at_utc" not in meta


@pytest.mark.parametrize("altitude,band,expected", [
    (36249, 500, 360), (36250, 500, 365), (36999, 2000, 360), (37000, 2000, 380), (-500, 1000, 0), (-501, 1000, -10),
    (0, 1000, 0), (499, 1000, 0), (500, 1000, 10),
])
def test_flight_level_boundaries(altitude, band, expected):
    assert flight_level(altitude, band) == expected


def test_distance_exactly_at_threshold_is_not_below_it():
    a, b = plane("A", -15, -50, 36000), plane("B", -15.05, -50, 36000)
    distance_nm = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) / KM_PER_NM
    bands, _ = scan([a, b], separation_nm=distance_nm)
    assert bands[0]["alert"] is False
    bands, _ = scan([a, b], separation_nm=distance_nm * 1.000001)
    assert bands[0]["alert"] is True


def test_units_are_consistent():
    bands, summary = scan(generate_traffic(500, seed=2))
    for band in bands:
        assert band["distance_km"] == pytest.approx(band["distance_nm"] * KM_PER_NM)
    assert summary["min_distance_nm"] == min(band["distance_nm"] for band in bands)


def test_all_pairs_without_any_close_pair():
    far = [plane("A", -10, -50, 30000, 0), plane("B", -20, -40, 30000, 1)]
    bands, summary = scan(far, all_pairs=True)
    assert bands[0]["close_pairs"] == [] and summary["close_pairs"] == 0 and summary["bands_below_threshold"] == 0


def test_empty_traffic():
    bands, summary = scan([])
    assert bands == [] and summary["bands_total"] == 0 and summary["min_distance_nm"] is None
