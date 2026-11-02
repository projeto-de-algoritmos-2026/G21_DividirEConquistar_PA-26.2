import itertools
import math
import random

import pytest

from lab import references
from lab.catalog import CATALOG
from lab.exercises import TYPES, check, new_exercise
from lab.max_subarray import max_subarray
from lab.metrics import MAX_STEPS
from lab.runner import ARRAY_ALGORITHMS, LabError, run_lab
from lab.scenarios import ARRAY_SCENARIOS, POINT_SCENARIOS, VISUAL_CASES, make_array, make_points, make_visual_case
from lab.selection import PIVOTS as SELECT_PIVOTS
from lab.selection import quickselect
from lab.sorting import PIVOTS as SORT_PIVOTS
from lab.sorting import merge_sort, quick_sort
from radar.brute_force import closest_pair_brute
from radar.closest_pair import closest_pair

SCENARIOS = list(ARRAY_SCENARIOS)


def random_arrays(count=40):
    rng = random.Random(99)
    for _ in range(count):
        yield [rng.randint(-20, 20) for _ in range(rng.randint(1, 120))]


# ---------- Merge Sort ----------

@pytest.mark.parametrize("scenario", SCENARIOS)
def test_merge_sort_matches_sorted(scenario):
    for seed in range(5):
        values = make_array(scenario, 97, seed)
        assert merge_sort(values)[0] == sorted(values)


def test_merge_sort_is_stable():
    records = [(random.Random(i).randint(0, 3), i) for i in range(60)]

    class Key:
        def __init__(self, record):
            self.record = record

        def __lt__(self, other):
            return self.record[0] < other.record[0]

    output = [key.record for key in merge_sort([Key(r) for r in records])[0]]
    assert output == sorted(records, key=lambda r: r[0])  # sorted() também é estável


def test_merge_sort_comparison_bounds():
    for n in (1, 2, 16, 100, 1000):
        values = make_array("aleatorio", n, n)
        _, run, _ = merge_sort(values)
        assert run.comparisons <= max(0, n * math.ceil(math.log2(max(n, 1))) - n + 1)
    assert merge_sort([])[0] == []


# ---------- Contagem de inversões ----------

def test_inversions_exhaustive_permutations():
    for n in range(0, 7):
        for perm in itertools.permutations(range(n)):
            assert merge_sort(list(perm), count_inversions=True)[2] == references.inversions_brute(list(perm))[0]


@pytest.mark.parametrize("values", list(random_arrays()))
def test_inversions_with_duplicates(values):
    assert merge_sort(values, count_inversions=True)[2] == references.inversions_brute(values)[0]


def test_inversions_extremes():
    n = 200
    assert merge_sort(list(range(n)), count_inversions=True)[2] == 0
    assert merge_sort(list(range(n, 0, -1)), count_inversions=True)[2] == n * (n - 1) // 2
    assert merge_sort([5] * n, count_inversions=True)[2] == 0


# ---------- Quick Sort ----------

@pytest.mark.parametrize("pivot", SORT_PIVOTS)
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_quick_sort_matches_sorted(pivot, scenario):
    values = make_array(scenario, 150, 4)
    assert quick_sort(values, pivot=pivot, seed=1)[0] == sorted(values)


def test_quick_sort_worst_case_is_quadratic():
    n = 300
    _, run = quick_sort(list(range(n)), pivot="ultimo")
    assert run.comparisons == n * (n - 1) // 2
    assert run.max_depth == n - 1
    _, run = quick_sort([7] * n, pivot="aleatorio", seed=3)  # Lomuto com iguais
    assert run.comparisons == n * (n - 1) // 2


def test_quick_sort_median_of_three_avoids_sorted_worst_case():
    n = 1024
    _, run = quick_sort(list(range(n)), pivot="mediana3")
    assert run.comparisons < 4 * n * math.log2(n)
    assert run.max_depth < 3 * math.log2(n)


def test_quick_sort_rejects_unknown_pivot():
    with pytest.raises(ValueError):
        quick_sort([1, 2], pivot="primeiro")


def test_quick_sort_deep_recursion_does_not_overflow():
    # Recursão na parte menor: profundidade lógica n − 1, pilha real O(log n).
    output, run = quick_sort(list(range(3000)), pivot="ultimo")
    assert output == list(range(3000)) and run.max_depth == 2999


# ---------- Quickselect ----------

@pytest.mark.parametrize("pivot", SELECT_PIVOTS)
def test_quickselect_every_k(pivot):
    for values in itertools.islice(random_arrays(), 15):
        ordered = sorted(values)
        for k in range(1, len(values) + 1):
            assert quickselect(values, k, pivot=pivot, seed=k)[0] == ordered[k - 1]


@pytest.mark.parametrize("pivot", SELECT_PIVOTS)
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_quickselect_scenarios(pivot, scenario):
    values = make_array(scenario, 301, 8)
    for k in (1, 150, 301):
        assert quickselect(values, k, pivot=pivot)[0] == sorted(values)[k - 1]


def test_quickselect_median_of_medians_is_linear_on_adversarial_input():
    for n in (500, 2000):
        _, run = quickselect(list(range(n)), 1, pivot="mediana_medianas")
        assert run.comparisons < 40 * n
    _, slow = quickselect(list(range(2000)), 1, pivot="ultimo")
    assert slow.comparisons > 2000 * 1999 // 2  # pior caso quadrático do pivô fixo


def test_quickselect_validates_k():
    with pytest.raises(ValueError):
        quickselect([1, 2, 3], 0)
    with pytest.raises(ValueError):
        quickselect([1, 2, 3], 4)


# ---------- Subarray de soma máxima ----------

@pytest.mark.parametrize("values", list(random_arrays()) + [[-5], [-3, -1, -2], [0, 0, 0], [4, -1, 2, 1]])
def test_max_subarray_matches_brute_force_and_kadane(values):
    (total, lo, hi), _ = max_subarray(values)
    assert 0 <= lo < hi <= len(values) and sum(values[lo:hi]) == total
    assert total == references.max_subarray_brute(values)[0][0] == references.kadane(values)[0][0]


def test_max_subarray_all_negative_returns_single_largest():
    (total, lo, hi), _ = max_subarray([-8, -3, -6, -2, -5])
    assert (total, lo, hi) == (-2, 3, 4)


def test_max_subarray_rejects_empty():
    with pytest.raises(ValueError):
        max_subarray([])


# ---------- Referências ----------

def test_references_are_correct():
    rng = random.Random(3)
    for _ in range(30):
        values = [rng.randint(-9, 9) for _ in range(rng.randint(1, 40))]
        assert references.insertion_sort(values)[0] == sorted(values)
        k = rng.randint(1, len(values))
        assert references.select_by_sorting(values, k)[0] == sorted(values)[k - 1]
    assert references.inversions_brute([3, 2, 1]) == (3, 3)


# ---------- Trilhas, catálogo e runner ----------

@pytest.mark.parametrize("algorithm", ARRAY_ALGORITHMS)
def test_trace_lines_exist_in_pseudocode(algorithm):
    lines = len(CATALOG[algorithm]["pseudocode"])
    for scenario in ("aleatorio", "iguais", "ordenado"):
        response = run_lab(algorithm, make_array(scenario, 33, 2))
        assert response["trace"] and response["steps"]
        assert response["verification"]["ok"]
        for step in response["steps"]:
            assert 1 <= step["line"] <= lines
            assert step["text"]


def test_closest_pair_trace_lines_exist_in_pseudocode():
    lines = len(CATALOG["closest_pair"]["pseudocode"])
    for step in closest_pair(make_points("aleatorio", 50, 1), trace=True).steps:
        assert 1 <= step["line"] <= lines


def test_merge_sort_trace_final_array_is_sorted():
    values = make_array("aleatorio", 40, 1)
    steps = run_lab("merge_sort", values)["steps"]
    assert steps[-1]["array"] == sorted(values)
    merges = [s for s in steps if s["kind"] == "merge"]
    assert len(merges) == run_lab("merge_sort", values)["metrics"]["comparisons"]


def test_inversions_trace_running_total_matches_answer():
    values = make_array("aleatorio", 30, 6)
    response = run_lab("inversions", values)
    assert response["steps"][-1]["inversions"] == response["output"] == references.inversions_brute(values)[0]


def test_large_inputs_skip_trace():
    response = run_lab("merge_sort", make_array("aleatorio", 500, 1))
    assert response["trace"] is False and response["steps"] == []


def test_trace_is_truncated_honestly():
    response = run_lab("quick_sort", list(range(64)) * 1, {"pivot": "ultimo"})
    assert len(response["steps"]) <= MAX_STEPS
    assert response["verification"]["ok"]


@pytest.mark.parametrize("bad", [[], [1.5], [True], ["1"], [10**10], list(range(2001))])
def test_run_lab_rejects_bad_values(bad):
    with pytest.raises(LabError):
        run_lab("merge_sort", bad)


def test_run_lab_rejects_bad_params():
    with pytest.raises(LabError):
        run_lab("quickselect", [1, 2, 3], {"k": 9})
    with pytest.raises(LabError):
        run_lab("quick_sort", [1, 2, 3], {"pivot": "x"})
    with pytest.raises(LabError):
        run_lab("bogo_sort", [1, 2, 3])


def test_kadane_reported_as_extra_reference():
    response = run_lab("max_subarray", [2, -5, 3, 4, -1])
    assert response["kadane"]["sum"] == response["output"]["sum"] == 7


# ---------- Cenários ----------

def test_scenarios_are_deterministic():
    for scenario in ARRAY_SCENARIOS:
        assert make_array(scenario, 50, 3) == make_array(scenario, 50, 3)
        assert len(make_array(scenario, 50, 3)) == 50
    for scenario in POINT_SCENARIOS:
        assert make_points(scenario, 50, 3) == make_points(scenario, 50, 3)
        assert len(make_points(scenario, 50, 3)) == 50


def test_scenario_shapes():
    assert make_array("ordenado", 30, 1) == sorted(make_array("ordenado", 30, 1))
    assert make_array("invertido", 30, 1) == sorted(make_array("invertido", 30, 1), reverse=True)
    assert set(make_array("iguais", 10, 1)) == {7}
    assert max(make_array("todos_negativos", 50, 1)) < 0
    assert len({p[0] for p in make_points("mesmo_eixo", 20, 1)}) == 1


@pytest.mark.parametrize("case", VISUAL_CASES)
def test_visual_cases_are_valid(case):
    points = make_visual_case(case, 16, 21)
    result = closest_pair(points, trace=True)
    assert result.distance == closest_pair_brute(points).distance


def test_visual_case_semantics():
    for case in ("faixa_central", "cruzamento_mediana"):
        points = make_visual_case(case, 16, 21)
        result = closest_pair(points, trace=True)
        root = result.steps[-1]
        # Nenhuma metade sozinha contém o par: ele só aparece na faixa da raiz.
        assert root["best"]["distance"] < root["delta"]
        assert set(root["best"]["pair"]) <= set(root["strip"])
    assert closest_pair(make_visual_case("duplicados", 16, 21)).distance == 0
    empates = make_visual_case("empates", 16, 21)
    assert closest_pair(empates).distance == 20


# ---------- Exercícios ----------

@pytest.mark.parametrize("kind", TYPES)
def test_exercises_are_reproducible_and_checked(kind):
    for seed in range(20):
        public = new_exercise(kind, seed)
        assert public == new_exercise(kind, seed)
        expected = check(kind, seed, -12345)["expected"]
        assert check(kind, seed, expected)["correct"] is True
        assert "answer" not in public and "expected" not in public


def test_master_theorem_exercise_answers():
    seen = set()
    for seed in range(200):
        public = new_exercise("teorema_mestre", seed)
        a, b, d = public["a"], public["b"], public["d"]
        expected = check("teorema_mestre", seed, 0)["expected"]
        critical = math.log(a, b)
        if math.isclose(d, critical):
            assert expected == 1
        elif d > critical:
            assert expected == 0
        else:
            assert expected == 2
        seen.add(expected)
    assert seen == {0, 1, 2}


def test_trace_truncation_is_real_and_bounded():
    _, run = quick_sort(list(range(200)), pivot="ultimo", trace=True)
    assert run.truncated is True and len(run.steps) == MAX_STEPS
    assert run.comparisons == 200 * 199 // 2  # a execução continua completa


@pytest.mark.parametrize("algorithm", ARRAY_ALGORITHMS)
def test_tracing_does_not_change_the_algorithm(algorithm):
    from lab.runner import execute, validate_params
    values = make_array("aleatorio", 60, 3)
    params = validate_params(algorithm, values, {"seed": 3})
    plain_output, plain = execute(algorithm, values, params, trace=False)
    traced_output, traced = execute(algorithm, values, params, trace=True)
    assert plain_output == traced_output
    assert plain.metrics() == traced.metrics()
    assert plain.steps == [] and traced.steps


def test_quickselect_with_and_without_median_of_medians_agree_on_adversarial_inputs():
    for values in (list(range(500)), list(range(500, 0, -1)), [3] * 500, [i % 7 for i in range(500)]):
        for k in (1, 250, 500):
            expected = sorted(values)[k - 1]
            for pivot in SELECT_PIVOTS:
                assert quickselect(values, k, pivot=pivot, seed=k)[0] == expected
