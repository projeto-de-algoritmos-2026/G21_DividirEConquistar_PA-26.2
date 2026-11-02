import itertools
import math
import random

import pytest

from radar.brute_force import closest_pair_brute
from radar.closest_pair import MAX_TRACE_POINTS, closest_pair


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
    with pytest.raises(ValueError):
        closest_pair([])


@pytest.mark.parametrize("bad", [(math.nan, 0), (math.inf, 1), (0, -math.inf), (1, 2, 3), ("1", 2)])
def test_rejects_invalid_points(bad):
    with pytest.raises(ValueError):
        closest_pair([(0, 0), bad])
    with pytest.raises(ValueError):
        closest_pair_brute([(0, 0), bad])


def test_duplicate_points_have_zero_distance():
    result = closest_pair([(1, 1), (5, 5), (1, 1), (9, 2)])
    assert result.distance == 0
    assert {result.i, result.j} == {0, 2}


def test_same_x_coordinate():
    points = [(7, y * y) for y in range(40)]
    assert closest_pair(points).distance == pytest.approx(1)


def test_pair_crossing_the_division():
    points = [(0, 0), (1, 50), (49.9, 10), (50.1, 10), (99, 0), (100, 50)]
    result = closest_pair(points)
    assert result.distance == pytest.approx(0.2)


def test_returned_indices_match_distance():
    rng = random.Random(5)
    points = random_points(rng, 500, 100)
    result = closest_pair(points)
    assert result.i != result.j
    assert math.dist(points[result.i], points[result.j]) == result.distance


@pytest.mark.parametrize("seed", range(30))
def test_matches_brute_force(seed):
    rng = random.Random(seed)
    # Spans pequenos forçam empates e coordenadas repetidas.
    span = rng.choice((5, 100, 10000))
    points = random_points(rng, rng.randint(2, 300), span)
    if seed % 3 == 0:
        points = [(round(x), round(y)) for x, y in points]
    assert closest_pair(points).distance == pytest.approx(closest_pair_brute(points).distance)


def test_exhaustive_small_grids():
    """Todos os subconjuntos de 2 a 5 pontos de uma grade 3×3 (muitos empates)."""
    grid = [(x, y) for x in range(3) for y in range(3)]
    for size in range(2, 6):
        for subset in itertools.combinations(grid, size):
            assert closest_pair(list(subset)).distance == closest_pair_brute(list(subset)).distance


def test_uses_far_fewer_comparisons_than_brute_force():
    n = 4000
    points = random_points(random.Random(1), n, 1000)
    assert closest_pair(points).comparisons < 8 * n * math.log2(n) / 2
    assert closest_pair_brute(points).comparisons == n * (n - 1) // 2


def test_strip_comparisons_stay_linear_for_collinear_points():
    # Todos no mesmo x: a faixa contém todos os pontos, mas o corte por Δy limita o trabalho.
    n = 2048
    points = [(0.0, float(i)) for i in range(n)]
    assert closest_pair(points).comparisons < 4 * n * math.log2(n)


class TestTrace:
    @pytest.fixture
    def run(self):
        points = random_points(random.Random(11), 40, 100)
        return points, closest_pair(points, trace=True)

    def test_trace_limit(self):
        with pytest.raises(ValueError):
            closest_pair(random_points(random.Random(1), MAX_TRACE_POINTS + 1, 10), trace=True)

    def test_last_step_is_root_combine(self, run):
        points, result = run
        last = result.steps[-1]
        assert last["kind"] == "combine" and last["depth"] == 0 and last["size"] == len(points)
        assert last["best"]["distance"] == result.distance

    def test_each_step_reports_its_local_best(self, run):
        """O melhor par de cada etapa é o mínimo do subconjunto, não o global."""
        points, result = run
        for step in result.steps:
            if step["kind"] == "divide":
                assert step["best"] is None
                continue
            subset = [points[i] for i in step["members"]]
            expected = closest_pair_brute(subset).distance if len(subset) >= 2 else None
            if expected is None:
                assert step["best"] is None
            else:
                assert step["best"]["distance"] == pytest.approx(expected)
                assert set(step["best"]["pair"]) <= set(step["members"])

    def test_combine_delta_is_min_of_halves(self, run):
        _, result = run
        for step in result.steps:
            if step["kind"] == "combine":
                halves = [h["distance"] for h in (step["left"], step["right"]) if h]
                assert step["delta"] == pytest.approx(min(halves))
                assert step["best"]["distance"] <= step["delta"]

    def test_strip_members_are_within_delta(self, run):
        points, result = run
        for step in result.steps:
            if step["kind"] == "combine":
                assert all(abs(points[p][0] - step["middle_x"]) < step["delta"] for p in step["strip"])
                ys = [points[p][1] for p in step["strip"]]
                assert ys == sorted(ys)

    def test_comparisons_are_fully_reported(self, run):
        points, result = run
        reported = sum(len(step["compared"]) for step in result.steps)
        assert reported == result.comparisons
        assert result.steps[-1]["comparisons_total"] == result.comparisons
        for step in result.steps:
            for a, b in step["compared"]:
                assert 0 <= a < len(points) and 0 <= b < len(points) and a != b

    def test_tree_is_consistent(self, run):
        points, result = run
        tree = result.tree
        assert len(tree) == result.calls
        assert tree[0]["parent"] is None and tree[0]["size"] == len(points)
        for node in tree[1:]:
            parent = tree[node["parent"]]
            assert node["depth"] == parent["depth"] + 1
            assert set(node["members"]) <= set(parent["members"])
        assert max(node["depth"] for node in tree) == result.max_depth
