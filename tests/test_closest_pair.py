import math
import random

import pytest

from radar.brute_force import closest_pair_brute
from radar.closest_pair import closest_pair


def random_points(rng, n, span):
    return [(rng.uniform(0, span), rng.uniform(0, span)) for _ in range(n)]


def test_finds_known_pair():
    points = [(0, 0), (10, 10), (3, 4), (10.5, 10), (20, 1)]
    result = closest_pair(points)
    assert result.distance == pytest.approx(0.5)
    assert {result.i, result.j} == {1, 3}


def test_two_points():
    assert closest_pair([(0, 0), (3, 4)]).distance == pytest.approx(5)


def test_requires_two_points():
    with pytest.raises(ValueError):
        closest_pair([(1, 1)])


def test_duplicate_points_have_zero_distance():
    assert closest_pair([(1, 1), (5, 5), (1, 1), (9, 2)]).distance == 0


def test_same_x_coordinate():
    points = [(7, y * y) for y in range(40)]
    assert closest_pair(points).distance == pytest.approx(1)


def test_pair_crossing_the_division():
    points = [(0, 0), (1, 50), (49.9, 10), (50.1, 10), (99, 0), (100, 50)]
    result = closest_pair(points)
    assert result.distance == pytest.approx(0.2)


@pytest.mark.parametrize("seed", range(30))
def test_matches_brute_force(seed):
    rng = random.Random(seed)
    # Spans pequenos forçam empates e coordenadas repetidas.
    span = rng.choice((5, 100, 10000))
    points = random_points(rng, rng.randint(2, 300), span)
    if seed % 3 == 0:
        points = [(round(x), round(y)) for x, y in points]
    assert closest_pair(points).distance == pytest.approx(closest_pair_brute(points).distance)


def test_uses_far_fewer_comparisons_than_brute_force():
    n = 4000
    points = random_points(random.Random(1), n, 1000)
    assert closest_pair(points).comparisons < 8 * n * math.log2(n) / 2
    assert closest_pair_brute(points).comparisons == n * (n - 1) // 2
