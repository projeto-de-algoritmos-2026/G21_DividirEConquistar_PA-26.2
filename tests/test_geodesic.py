import itertools
import math
import random

import pytest

from radar.brute_force import closest_pair_brute
from radar.geo import (TangentPlane, arc_to_chord_km, chord_to_arc_km, haversine_km, project, to_ecef)
from radar.geodesic import closest_pair_geodesic, pairs_within_km


def brute_geodesic(coords):
    return min(haversine_km(*a, *b) for a, b in itertools.combinations(coords, 2))


def counterexample():
    """A 33°S, um par leste-oeste de 10 km e outro norte-sul de 11 km."""
    lat = -33.0
    dlon = 10 / (111.195 * math.cos(math.radians(lat)))
    return [(lat, -60.0), (lat, -60.0 + dlon), (lat + 1, -55.0), (lat + 1 + 11 / 111.195, -55.0)]


def test_legacy_projection_picks_wrong_pair():
    coords = counterexample()
    legacy = closest_pair_brute([project(*c) for c in coords])
    assert {legacy.i, legacy.j} == {2, 3}  # o par de 11 km
    assert haversine_km(*coords[2], *coords[3]) > brute_geodesic(coords) + 0.5


def test_geodesic_pair_fixes_counterexample():
    result = closest_pair_geodesic(counterexample())
    assert {result.i, result.j} == {0, 1}
    assert result.distance_km == pytest.approx(10, abs=0.01)


def test_chord_arc_round_trip():
    for arc in (0.0, 1.0, 9.26, 500.0, 15000.0):
        assert chord_to_arc_km(arc_to_chord_km(arc)) == pytest.approx(arc, abs=1e-6)


def test_chord_matches_haversine():
    a, b = (-23.4, -46.5), (-3.0, -60.0)
    assert chord_to_arc_km(math.dist(to_ecef(*a), to_ecef(*b))) == pytest.approx(haversine_km(*a, *b))


@pytest.mark.parametrize("seed", range(10))
def test_tangent_projection_never_exceeds_chord(seed):
    rng = random.Random(seed)
    coords = [(rng.uniform(-80, 80), rng.uniform(-180, 180)) for _ in range(30)]
    plane = TangentPlane(coords)
    for a, b in itertools.combinations(coords, 2):
        planar = math.dist(plane.project(*a), plane.project(*b))
        assert planar <= math.dist(to_ecef(*a), to_ecef(*b)) * (1 + 1e-12) + 1e-9


@pytest.mark.parametrize("seed", range(25))
def test_matches_brute_force_haversine(seed):
    rng = random.Random(seed)
    spread = rng.choice((0.5, 5, 30, 170))  # de uma região pequena até o globo
    lat0, lon0 = rng.uniform(-60, 60), rng.uniform(-170, 170)
    coords = [(max(-89.0, min(89.0, lat0 + rng.uniform(-spread, spread) / 2)),
               (lon0 + rng.uniform(-spread, spread) + 180) % 360 - 180) for _ in range(rng.randint(2, 120))]
    result = closest_pair_geodesic(coords)
    assert result.distance_km == pytest.approx(brute_geodesic(coords), abs=1e-9)


def test_duplicates_and_antimeridian():
    assert closest_pair_geodesic([(10, 179.9), (10, -179.9), (40, 0), (40, 0)]).distance_km == 0
    result = closest_pair_geodesic([(10, 179.95), (10, -179.95), (12, 170), (-5, 0)])
    assert {result.i, result.j} == {0, 1}


@pytest.mark.parametrize("seed", range(8))
def test_pairs_within_matches_brute_force(seed):
    rng = random.Random(seed)
    coords = [(rng.uniform(-20, -10), rng.uniform(-50, -40)) for _ in range(150)]
    limit = 40.0
    pairs, candidates, truncated = pairs_within_km(coords, limit)
    expected = {(a, b) for a, b in itertools.combinations(range(len(coords)), 2)
                if haversine_km(*coords[a], *coords[b]) < limit}
    assert {(a, b) for a, b, _ in pairs} == expected
    assert candidates >= len(expected) and not truncated
    distances = [d for _, _, d in pairs]
    assert distances == sorted(distances)


def test_pairs_within_truncates():
    coords = [(0.0, i * 0.001) for i in range(40)]
    pairs, _, truncated = pairs_within_km(coords, 100, max_pairs=10)
    assert len(pairs) == 10 and truncated


EDGE_CASES = {
    "calota_norte": lambda rng: [(rng.uniform(89.5, 90), rng.uniform(-180, 180)) for _ in range(60)] + [(90.0, 0.0), (90.0, 123.0)],
    "calota_sul": lambda rng: [(rng.uniform(-90, -89), rng.uniform(-180, 180)) for _ in range(60)],
    "antimeridiano": lambda rng: [(rng.uniform(-5, 5), rng.choice((1, -1)) * rng.uniform(179, 180)) for _ in range(60)],
    "equador_greenwich": lambda rng: [(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(60)],
    "quase_antipodas": lambda rng: [(10, 20), (-10, -160), (10.001, 20), (-10, -159.999)],
    "empates": lambda rng: [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0), (0.0, 3.0)],
}


@pytest.mark.parametrize("case", EDGE_CASES)
def test_geographic_edge_cases_match_brute_force(case):
    coords = EDGE_CASES[case](random.Random(7))
    assert closest_pair_geodesic(coords).distance_km == pytest.approx(brute_geodesic(coords), abs=1e-9)


@pytest.mark.parametrize("seed", range(5))
def test_result_does_not_depend_on_input_order(seed):
    rng = random.Random(seed)
    coords = [(rng.uniform(-30, -10), rng.uniform(-60, -40)) for _ in range(150)]
    shuffled = coords[:]
    rng.shuffle(shuffled)
    first, second = closest_pair_geodesic(coords), closest_pair_geodesic(shuffled)
    assert first.distance_km == pytest.approx(second.distance_km, abs=1e-12)
    assert {coords[first.i], coords[first.j]} == {shuffled[second.i], shuffled[second.j]} or first.distance_km == 0


def test_global_spread_stays_exact():
    """No globo inteiro a projeção dobra um hemisfério sobre o outro: k cresce, mas o par continua exato."""
    rng = random.Random(1)
    coords = [(math.degrees(math.asin(rng.uniform(-1, 1))), rng.uniform(-180, 180)) for _ in range(3000)]
    result = closest_pair_geodesic(coords)
    assert result.distance_km == pytest.approx(min(
        haversine_km(*coords[a], *coords[b]) for a, b in pairs_from_grid(coords, result.distance_km * 1.01)), abs=1e-9)
    assert result.candidate_pairs < len(coords) * (len(coords) - 1) // 2 // 100


def test_certification_is_cheap_on_regional_traffic():
    rng = random.Random(1)
    coords = [(rng.uniform(-33, 5), rng.uniform(-74, -35)) for _ in range(3000)]  # recorte do tamanho do Brasil
    result = closest_pair_geodesic(coords)
    assert result.candidate_pairs < len(coords)


def pairs_from_grid(coords, radius_km):
    """Pares a menos de radius_km por força bruta em latitude (filtro barato e independente)."""
    order = sorted(range(len(coords)), key=lambda i: coords[i][0])
    band = radius_km / 111.0 + 1e-9
    for position, a in enumerate(order):
        for b in order[position + 1:]:
            if coords[b][0] - coords[a][0] > band:
                break
            yield a, b


def test_pairs_within_handles_empty_results():
    pairs, _, truncated = pairs_within_km([(0.0, 0.0), (10.0, 10.0)], 5)
    assert pairs == [] and truncated is False
    assert pairs_within_km([(0.0, 0.0)], 5) == ([], 0, False)
    assert pairs_within_km([(0.0, 0.0), (0.0, 0.0)], 0) == ([], 0, False)
