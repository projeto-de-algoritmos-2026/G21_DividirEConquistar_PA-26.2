import pytest

from radar.bands import flight_level, group_by_band, scan
from radar.brute_force import closest_pair_brute
from radar.generator import generate_traffic, load_snapshot
from radar.geo import KM_PER_NM, haversine_km, project


def plane(callsign, lat, lon, altitude_ft):
    return {"callsign": callsign, "lat": lat, "lon": lon, "altitude_ft": altitude_ft}


def test_haversine_one_degree_of_latitude():
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.19, abs=0.01)


def test_project_preserves_latitude_distance():
    assert project(-14, -52)[1] - project(-15, -52)[1] == pytest.approx(111.19, abs=0.01)


def test_flight_level_rounds_to_thousand_feet():
    assert flight_level(36100) == 360
    assert flight_level(35900) == 360


def test_group_by_band_separates_levels():
    bands = group_by_band([plane("A", 0, 0, 36000), plane("B", 0, 0, 37000)])
    assert sorted(bands) == [360, 370]


def test_aircraft_in_different_levels_are_not_in_conflict():
    assert scan([plane("A", -15, -50, 36000), plane("B", -15, -50, 37000)]) == []


def test_alerts_below_separation():
    close = 4 * KM_PER_NM / 111.19
    report = scan([plane("A", -15, -50, 36000), plane("B", -15 + close, -50, 36000)])
    assert report[0]["alert"] is True
    assert report[0]["distance_nm"] == pytest.approx(4, abs=0.01)


def test_no_alert_above_separation():
    far = 6 * KM_PER_NM / 111.19
    assert scan([plane("A", -15, -50, 36000), plane("B", -15 + far, -50, 36000)])[0]["alert"] is False


def test_traffic_is_reproducible_by_seed():
    assert generate_traffic(50, seed=7) == generate_traffic(50, seed=7)
    assert generate_traffic(50, seed=7) != generate_traffic(50, seed=8)


def test_traffic_moves_with_time():
    assert generate_traffic(20, seed=7, minutes=10) != generate_traffic(20, seed=7)


@pytest.mark.parametrize("aircraft", [generate_traffic(600, seed=3), load_snapshot()])
def test_scan_matches_brute_force(aircraft):
    fast = scan(aircraft)
    slow = scan(aircraft, solver=closest_pair_brute)
    assert fast
    assert [r["distance_km"] for r in fast] == pytest.approx([r["distance_km"] for r in slow])
