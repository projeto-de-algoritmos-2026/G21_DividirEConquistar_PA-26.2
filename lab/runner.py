"""Execução, verificação, comparação e benchmark dos algoritmos do laboratório.

Cada algoritmo D&C é executado e conferido com uma referência independente
(lab/references.py ou a biblioteca padrão). Tempos e contagens vêm sempre de
uma execução real; nada é pré-calculado.
"""
import math
import os
import platform
import statistics
import threading
import time
from datetime import datetime

from lab import references
from lab.catalog import CATALOG
from lab.max_subarray import max_subarray
from lab.scenarios import ARRAY_SCENARIOS, POINT_SCENARIOS, make_array, make_points
from lab.selection import PIVOTS as SELECT_PIVOTS
from lab.selection import quickselect
from lab.sorting import PIVOTS as SORT_PIVOTS
from lab.sorting import merge_sort, quick_sort
from radar.brute_force import closest_pair_brute
from radar.closest_pair import closest_pair

TRACE_MAX_N = 64
LAB_MAX_N = 2000
COMPARE_MAX_N = 1000
REFERENCE_MAX_N = 2000    # referências Θ(n²) param aqui no benchmark
BENCH_MAX_N = 20000
BENCH_QUADRATIC_MAX_N = 3000  # quando o próprio D&C pode cair em Θ(n²)
BENCH_MAX_SIZES = 8
BENCH_MAX_REPEATS = 7
BENCH_BUDGET_S = 20.0
VALUE_LIMIT = 10**9

ARRAY_ALGORITHMS = ("merge_sort", "quick_sort", "quickselect", "inversions", "max_subarray")
ALGORITHMS = ("closest_pair",) + ARRAY_ALGORITHMS
_bench_lock = threading.Lock()


class LabError(ValueError):
    """Entrada inválida para o laboratório (vira HTTP 400)."""


class BusyError(RuntimeError):
    """Já existe um benchmark em execução (vira HTTP 429)."""


def validate_values(values, max_n):
    if not isinstance(values, list) or not 1 <= len(values) <= max_n:
        raise LabError(f"informe de 1 a {max_n} valores")
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or abs(value) > VALUE_LIMIT:
            raise LabError(f"valores devem ser inteiros entre −{VALUE_LIMIT} e {VALUE_LIMIT}")
    return values


def validate_params(algorithm, values, params):
    params = dict(params or {})
    if algorithm == "quick_sort":
        params.setdefault("pivot", "ultimo")
        if params["pivot"] not in SORT_PIVOTS:
            raise LabError(f"pivô deve ser um de {', '.join(SORT_PIVOTS)}")
    if algorithm == "quickselect":
        params.setdefault("pivot", "aleatorio")
        if params["pivot"] not in SELECT_PIVOTS:
            raise LabError(f"pivô deve ser um de {', '.join(SELECT_PIVOTS)}")
        k = params.get("k", (len(values) + 1) // 2)
        if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(values):
            raise LabError(f"k deve ser inteiro entre 1 e {len(values)}")
        params["k"] = k
    seed = params.get("seed", 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise LabError("seed deve ser inteira")
    params["seed"] = seed
    return params


def execute(algorithm, values, params, trace=False):
    """Roda a versão D&C. Retorna (saída, Run ou métricas, trilha)."""
    if algorithm == "merge_sort":
        output, run, _ = merge_sort(values, trace=trace)
        return output, run
    if algorithm == "inversions":
        output, run, count = merge_sort(values, trace=trace, count_inversions=True)
        for step in run.steps:
            if step["kind"] == "merge":
                step["line"] = 7 if step["side"] == "right" else 6
        return count, run
    if algorithm == "quick_sort":
        return quick_sort(values, pivot=params["pivot"], seed=params["seed"], trace=trace)
    if algorithm == "quickselect":
        return quickselect(values, params["k"], pivot=params["pivot"], seed=params["seed"], trace=trace)
    if algorithm == "max_subarray":
        (total, lo, hi), run = max_subarray(values, trace=trace)
        return {"sum": total, "start": lo, "end": hi}, run
    if algorithm == "closest_pair":
        result = closest_pair(values)
        return {"distance": result.distance, "pair": [result.i, result.j]}, result
    raise LabError(f"algoritmo desconhecido: {algorithm}")


def reference(algorithm, values, params):
    """Roda a referência usada no benchmark. Retorna (saída, comparações, nome)."""
    if algorithm in ("merge_sort", "quick_sort"):
        output, comparisons = references.insertion_sort(values)
        return output, comparisons, "Inserção Θ(n²)"
    if algorithm == "quickselect":
        output, comparisons = references.select_by_sorting(values, params["k"])
        return output, comparisons, "Ordenar por inserção e indexar"
    if algorithm == "inversions":
        output, comparisons = references.inversions_brute(values)
        return output, comparisons, "Força bruta Θ(n²)"
    if algorithm == "max_subarray":
        (total, lo, hi), comparisons = references.max_subarray_brute(values)
        return {"sum": total, "start": lo, "end": hi}, comparisons, "Força bruta Θ(n²)"
    if algorithm == "closest_pair":
        result = closest_pair_brute(values)
        return {"distance": result.distance, "pair": [result.i, result.j]}, result.comparisons, "Força bruta Θ(n²)"
    raise LabError(f"algoritmo desconhecido: {algorithm}")


def verify(algorithm, values, params, output):
    """Confere a saída D&C com uma fonte independente. Retorna (ok, esperado, fonte)."""
    if algorithm in ("merge_sort", "quick_sort"):
        expected = sorted(values)
        return output == expected, expected, "sorted() do Python"
    if algorithm == "quickselect":
        expected = sorted(values)[params["k"] - 1]
        return output == expected, expected, "sorted(A)[k − 1]"
    if algorithm == "inversions":
        expected, _ = references.inversions_brute(values)
        return output == expected, expected, "força bruta"
    if algorithm == "max_subarray":
        (total, lo, hi), _ = references.max_subarray_brute(values)
        ok = output["sum"] == total and sum(values[output["start"]:output["end"]]) == output["sum"]
        return ok, {"sum": total, "start": lo, "end": hi}, "força bruta (soma conferida no trecho)"
    if algorithm == "closest_pair":
        brute = closest_pair_brute(values)
        ok = math.isclose(output["distance"], brute.distance, rel_tol=1e-12, abs_tol=1e-12)
        return ok, {"distance": brute.distance, "pair": [brute.i, brute.j]}, "força bruta"
    raise LabError(f"algoritmo desconhecido: {algorithm}")


def agree(algorithm, output, other):
    """Compara a saída D&C com a saída da referência do benchmark."""
    if algorithm == "closest_pair":
        return math.isclose(output["distance"], other["distance"], rel_tol=1e-12, abs_tol=1e-12)
    if algorithm == "max_subarray":
        return output["sum"] == other["sum"]
    return output == other


def run_lab(algorithm, values, params=None):
    """Execução do laboratório: saída, métricas, trilha (n ≤ 64) e verificação."""
    if algorithm not in ARRAY_ALGORITHMS:
        raise LabError(f"algoritmo desconhecido: {algorithm}")
    values = validate_values(values, LAB_MAX_N)
    params = validate_params(algorithm, values, params)
    trace = len(values) <= TRACE_MAX_N
    started = time.perf_counter()
    output, run = execute(algorithm, values, params, trace=trace)
    elapsed = (time.perf_counter() - started) * 1000
    ok, expected, source = verify(algorithm, values, params, output)
    response = {
        "algorithm": algorithm,
        "input": values,
        "params": params,
        "output": output,
        "metrics": {**run.metrics(), "elapsed_ms": elapsed, "unit": CATALOG[algorithm]["unit"]},
        "steps": run.steps,
        "trace": trace,
        "truncated": run.truncated,
        "verification": {"ok": ok, "expected": expected, "source": source},
    }
    if algorithm == "max_subarray":
        (total, lo, hi), comparisons = references.kadane(values)
        response["kadane"] = {"sum": total, "start": lo, "end": hi, "comparisons": comparisons}
    return response


def make_input(algorithm, scenario, n, seed):
    if algorithm == "closest_pair":
        if scenario not in POINT_SCENARIOS:
            raise LabError(f"cenário de pontos desconhecido: {scenario}")
        if n < 2:
            raise LabError("o par mais próximo precisa de ao menos 2 pontos")
        return make_points(scenario, n, seed)
    if scenario not in ARRAY_SCENARIOS:
        raise LabError(f"cenário de vetor desconhecido: {scenario}")
    return make_array(scenario, n, seed)


def max_bench_n(algorithm, scenario, params):
    """Teto de n que mantém cada execução em poucos segundos.

    Quick Sort com Lomuto degrada para Θ(n²) com pivô determinístico em entradas
    ordenadas e, com qualquer pivô, quando há muitos valores iguais.
    """
    deterministic = params.get("pivot") in ("ultimo", "mediana3")
    if algorithm == "quick_sort" and (deterministic or scenario in ("duplicados", "iguais")):
        return BENCH_QUADRATIC_MAX_N
    if algorithm == "quickselect" and deterministic:
        return BENCH_QUADRATIC_MAX_N
    return BENCH_MAX_N


def _timed(function):
    started = time.perf_counter()
    output = function()
    return (time.perf_counter() - started) * 1000, output


def _stats(samples):
    return {
        "median_ms": statistics.median(samples),
        "min_ms": min(samples),
        "max_ms": max(samples),
        "stdev_ms": statistics.stdev(samples) if len(samples) > 1 else 0.0,
        "samples_ms": samples,
    }


def environment():
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "não informado",
        "cpus": os.cpu_count(),
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def run_benchmark(algorithm="closest_pair", sizes=(250, 500, 1000, 2000), repeats=3, seed=21,
                  scenario="aleatorio", params=None, warmup=True, budget_s=BENCH_BUDGET_S):
    """Mede D&C e referência sobre a mesma entrada para cada n.

    A ordem D&C/referência alterna a cada repetição para reduzir viés; uma
    rodada de aquecimento é descartada. Referências Θ(n²) acima de
    REFERENCE_MAX_N e tamanhos além do orçamento de tempo não são executados e
    vêm marcados como tal, sem valor inventado.
    """
    if algorithm not in ALGORITHMS:
        raise LabError(f"algoritmo desconhecido: {algorithm}")
    sizes = sorted(set(sizes))
    if not 1 <= len(sizes) <= BENCH_MAX_SIZES:
        raise LabError(f"informe de 1 a {BENCH_MAX_SIZES} tamanhos")
    if not 1 <= repeats <= BENCH_MAX_REPEATS:
        raise LabError(f"repetições devem estar entre 1 e {BENCH_MAX_REPEATS}")
    params = validate_params(algorithm, [0] * max(sizes), params)
    limit = max_bench_n(algorithm, scenario, params)
    minimum = 2 if algorithm == "closest_pair" else 1
    if sizes[0] < minimum or sizes[-1] > limit:
        raise LabError(f"tamanhos devem estar entre {minimum} e {limit} para este algoritmo e cenário")
    if not _bench_lock.acquire(blocking=False):
        raise BusyError("já existe um benchmark em execução; aguarde")
    try:
        return _benchmark(algorithm, sizes, repeats, seed, scenario, params, warmup, budget_s)
    finally:
        _bench_lock.release()


def _benchmark(algorithm, sizes, repeats, seed, scenario, params, warmup, budget_s):
    deadline = time.perf_counter() + budget_s
    rows = []
    for n in sizes:
        row = {"n": n, "dc": None, "reference": None, "skipped": None, "reference_skipped": None}
        if rows and time.perf_counter() > deadline:
            row["skipped"] = "orçamento de tempo esgotado"
            rows.append(row)
            continue
        values = make_input(algorithm, scenario, n, seed)
        local = dict(params)
        if algorithm == "quickselect":
            local["k"] = (n + 1) // 2
        run_ref = n <= REFERENCE_MAX_N
        if not run_ref:
            row["reference_skipped"] = f"referência Θ(n²) só até n = {REFERENCE_MAX_N}"
        dc_samples, ref_samples = [], []
        dc_output = ref_output = None
        if warmup:
            execute(algorithm, values, local)
        for repeat in range(repeats):
            order = ("dc", "ref") if repeat % 2 == 0 else ("ref", "dc")
            for which in order:
                if which == "dc":
                    elapsed, dc_output = _timed(lambda: execute(algorithm, values, local))
                    dc_samples.append(elapsed)
                elif run_ref:
                    elapsed, ref_output = _timed(lambda: reference(algorithm, values, local))
                    ref_samples.append(elapsed)
        output, run = dc_output
        # Sem referência executada, não há como afirmar que o resultado confere.
        ok = agree(algorithm, output, ref_output[0]) if run_ref else None
        row["dc"] = {**_stats(dc_samples), "comparisons": run.comparisons, "verified": ok}
        if run_ref:
            _, comparisons, name = ref_output
            row["reference"] = {**_stats(ref_samples), "comparisons": comparisons, "name": name}
        rows.append(row)
    return {
        "algorithm": algorithm,
        "name": CATALOG[algorithm]["name"],
        "unit": CATALOG[algorithm]["unit"],
        "scenario": scenario,
        "seed": seed,
        "repeats": repeats,
        "warmup": warmup,
        "params": params,
        "rows": rows,
        "environment": environment(),
    }


def compare_all(scenario="aleatorio", n=500, seed=21, repeats=3):
    """D&C × referência para todos os algoritmos, sobre entradas da mesma seed."""
    if not 2 <= n <= COMPARE_MAX_N:
        raise LabError(f"n deve estar entre 2 e {COMPARE_MAX_N}")
    if scenario not in ARRAY_SCENARIOS:
        raise LabError(f"cenário desconhecido: {scenario}")
    if not 1 <= repeats <= BENCH_MAX_REPEATS:
        raise LabError(f"repetições devem estar entre 1 e {BENCH_MAX_REPEATS}")
    if not _bench_lock.acquire(blocking=False):
        raise BusyError("já existe uma medição em execução; aguarde")
    try:
        return _compare(scenario, n, seed, repeats)
    finally:
        _bench_lock.release()


def _compare(scenario, n, seed, repeats):
    rows = []
    for algorithm in ALGORITHMS:
        # O par mais próximo usa pontos; os demais usam o vetor do cenário.
        point_scenario = scenario if scenario in POINT_SCENARIOS else "aleatorio"
        values = make_input(algorithm, point_scenario if algorithm == "closest_pair" else scenario, n, seed)
        params = validate_params(algorithm, values, {"seed": seed})
        dc_times, ref_times = [], []
        for repeat in range(repeats):
            elapsed, dc_output = _timed(lambda: execute(algorithm, values, params))
            dc_times.append(elapsed)
            elapsed, ref_output = _timed(lambda: reference(algorithm, values, params))
            ref_times.append(elapsed)
        output, run = dc_output
        ok, _, source = verify(algorithm, values, params, output)
        rows.append({
            "algorithm": algorithm,
            "name": CATALOG[algorithm]["name"],
            "unit": CATALOG[algorithm]["unit"],
            "input": "pontos: " + POINT_SCENARIOS[point_scenario] if algorithm == "closest_pair" else ARRAY_SCENARIOS[scenario],
            "params": {key: value for key, value in params.items() if key != "seed"},
            "dc_ms": statistics.median(dc_times),
            "dc_comparisons": run.comparisons,
            "reference_name": ref_output[2],
            "reference_ms": statistics.median(ref_times),
            "reference_comparisons": ref_output[1],
            "verified": ok,
            "verified_by": source,
        })
    return {"scenario": scenario, "n": n, "seed": seed, "repeats": repeats, "rows": rows,
            "environment": environment()}

