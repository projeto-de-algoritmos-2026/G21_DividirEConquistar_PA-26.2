"""Radar de Conflitos Aéreos — Laboratório de Dividir e Conquistar: servidor Flask."""
import math
import os

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from lab import exercises
from lab.catalog import CATALOG, public_catalog
from lab.runner import (ALGORITHMS, ARRAY_ALGORITHMS, BENCH_MAX_N, BENCH_MAX_REPEATS, BENCH_MAX_SIZES,
                        COMPARE_MAX_N, LAB_MAX_N, REFERENCE_MAX_N, TRACE_MAX_N, BusyError, LabError,
                        compare_all, run_benchmark, run_lab)
from lab.scenarios import (ARRAY_SCENARIOS, POINT_SCENARIOS, VISUAL_CASES, make_array, make_visual_case)
from lab.selection import PIVOTS as SELECT_PIVOTS
from lab.sorting import PIVOTS as SORT_PIVOTS
from radar.bands import BAND_CHOICES, MAX_SEPARATION_NM, MIN_SEPARATION_NM, flight_level, group_by_band, scan
from radar.brute_force import closest_pair_brute
from radar.closest_pair import closest_pair
from radar.generator import SnapshotError, generate_traffic, read_snapshot
from radar.geo import TangentPlane

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024
app.json.ensure_ascii = False

MAX_AIRCRAFT = 3000
MAX_MINUTES = 240
MAX_SEED = 2**31 - 1
STEPS_MAX_AIRCRAFT = 64
COORD_LIMIT = 1e6


HTTP_MESSAGES = {404: "recurso não encontrado", 405: "método não permitido",
                 413: "requisição grande demais (limite de 256 KB)"}


class ApiError(ValueError):
    """Parâmetro inválido: responde 400 com a mensagem."""


@app.errorhandler(ApiError)
@app.errorhandler(LabError)
def bad_request(error):
    return jsonify(error=str(error)), 400


@app.errorhandler(BusyError)
def busy(error):
    return jsonify(error=str(error)), 429


@app.errorhandler(SnapshotError)
def snapshot_unavailable(error):
    return jsonify(error=str(error)), 503


@app.errorhandler(HTTPException)
def http_error(error):
    if request.path.startswith("/api/"):
        return jsonify(error=HTTP_MESSAGES.get(error.code, error.description)), error.code
    return error


@app.errorhandler(Exception)
def internal_error(error):
    # Nunca expõe o stack trace ao cliente.
    app.logger.exception("erro não tratado")
    return jsonify(error="erro interno do servidor"), 500


def int_arg(name, default, low, high):
    """Inteiro da query string; fora do intervalo ou malformado vira HTTP 400."""
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ApiError(f"'{name}' deve ser um número inteiro") from None
    if not low <= value <= high:
        raise ApiError(f"'{name}' deve estar entre {low} e {high}")
    return value


def float_arg(name, default, low, high):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ApiError(f"'{name}' deve ser um número") from None
    if not math.isfinite(value) or not low <= value <= high:
        raise ApiError(f"'{name}' deve estar entre {low} e {high}")
    return value


def choice_arg(name, default, choices):
    value = request.args.get(name) or default
    if value not in choices:
        raise ApiError(f"'{name}' deve ser um de: {', '.join(map(str, choices))}")
    return value


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError("corpo JSON (objeto) obrigatório")
    return body


def body_int(body, name, default, low, high):
    value = body.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ApiError(f"'{name}' deve ser inteiro entre {low} e {high}")
    return value


def load_traffic():
    """Tráfego da fonte pedida e metadados da fonte."""
    source = choice_arg("source", "sim", ("sim", "opensky"))
    if source == "opensky":
        return read_snapshot()
    n = int_arg("n", 400, 2, MAX_AIRCRAFT)
    seed = int_arg("seed", 21, 0, MAX_SEED)
    minutes = int_arg("minutes", 0, 0, MAX_MINUTES)
    meta = {"kind": "sim", "label": "Simulação determinística", "seed": seed, "minutes": minutes, "records": n}
    return generate_traffic(n, seed, minutes), meta


def model_args():
    return {
        "separation_nm": float_arg("threshold_nm", 5.0, MIN_SEPARATION_NM, MAX_SEPARATION_NM),
        "band_ft": int(choice_arg("band_ft", "1000", tuple(map(str, BAND_CHOICES)))),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def api_health():
    try:
        _, meta = read_snapshot()
        snapshot = {"available": True, "records": meta["records"], "captured_at_local": meta.get("captured_at_local")}
    except SnapshotError as error:
        snapshot = {"available": False, "error": str(error)}
    return jsonify(status="ok", snapshot=snapshot)


@app.route("/api/scan")
def api_scan():
    aircraft, meta = load_traffic()
    model = model_args()
    all_pairs = choice_arg("all_pairs", "0", ("0", "1")) == "1"
    bands, summary = scan(aircraft, all_pairs=all_pairs, **model)
    for plane in aircraft:
        plane["flight_level"] = flight_level(plane["altitude_ft"], model["band_ft"])
    return jsonify(source=meta, model=model, aircraft=aircraft, bands=bands, summary=summary)


def trace_payload(points, labels=None):
    """Executa o par mais próximo com trilha e confere com a força bruta."""
    result = closest_pair(points, trace=True)
    brute = closest_pair_brute(points)
    return {
        "points": [list(point) for point in points],
        "labels": labels,
        "steps": result.steps,
        "tree": result.tree,
        "result": {"distance": result.distance, "pair": [result.i, result.j], "comparisons": result.comparisons,
                   "calls": result.calls, "max_depth": result.max_depth},
        "verification": {"ok": math.isclose(result.distance, brute.distance, rel_tol=1e-12, abs_tol=1e-12),
                         "brute_distance": brute.distance, "brute_comparisons": brute.comparisons},
        "pseudocode": CATALOG["closest_pair"]["pseudocode"],
    }


@app.route("/api/steps")
def api_steps():
    """Trilha da recursão numa faixa de altitude (padrão: a mais movimentada)."""
    aircraft, meta = load_traffic()
    band_ft = model_args()["band_ft"]
    bands = {level: planes for level, planes in group_by_band(aircraft, band_ft).items() if len(planes) >= 2}
    if not bands:
        raise ApiError("nenhuma faixa tem duas aeronaves")
    raw_band = request.args.get("band")
    if raw_band:
        level = int_arg("band", 0, 0, 1000)
        if level not in bands:
            raise ApiError(f"a faixa FL{level:03d} não tem duas aeronaves")
    else:
        level = max(bands, key=lambda key: len(bands[key]))
    planes = bands[level][:STEPS_MAX_AIRCRAFT]
    plane = TangentPlane([(p["lat"], p["lon"]) for p in planes])
    points = [plane.project(p["lat"], p["lon"]) for p in planes]
    payload = trace_payload(points, [p["callsign"] for p in planes])
    return jsonify(flight_level=level, band_size=len(bands[level]), sampled=len(planes) < len(bands[level]),
                   bands=sorted((key, len(value)) for key, value in bands.items()), source=meta, **payload)


@app.route("/api/visualizer/cases")
def api_visual_cases():
    return jsonify(cases=[{"id": key, "name": name, "description": text} for key, (name, text) in VISUAL_CASES.items()],
                   max_points=TRACE_MAX_N)


@app.route("/api/visualizer", methods=["POST"])
def api_visualizer():
    body = json_body()
    if "points" in body:
        points = body["points"]
        if not isinstance(points, list) or not 2 <= len(points) <= TRACE_MAX_N:
            raise ApiError(f"informe de 2 a {TRACE_MAX_N} pontos")
        clean = []
        for point in points:
            if (not isinstance(point, list) or len(point) != 2
                    or not all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in point)
                    or not all(math.isfinite(c) and abs(c) <= COORD_LIMIT for c in point)):
                raise ApiError(f"cada ponto deve ser [x, y] com números finitos de até {COORD_LIMIT:g} em módulo")
            clean.append((float(point[0]), float(point[1])))
        return jsonify(case=None, **trace_payload(clean))
    case = body.get("case", "nuvem")
    if case not in VISUAL_CASES:
        raise ApiError(f"caso deve ser um de: {', '.join(VISUAL_CASES)}")
    n = body_int(body, "n", 16, 2, TRACE_MAX_N)
    seed = body_int(body, "seed", 21, 0, MAX_SEED)
    return jsonify(case=case, **trace_payload(make_visual_case(case, n, seed)))


@app.route("/api/lab/catalog")
def api_catalog():
    return jsonify(
        algorithms=public_catalog(),
        lab_algorithms=list(ARRAY_ALGORITHMS),
        array_scenarios=ARRAY_SCENARIOS,
        point_scenarios=POINT_SCENARIOS,
        pivots={"quick_sort": list(SORT_PIVOTS), "quickselect": list(SELECT_PIVOTS)},
        limits={"trace_max_n": TRACE_MAX_N, "lab_max_n": LAB_MAX_N, "compare_max_n": COMPARE_MAX_N,
                "bench_max_n": BENCH_MAX_N, "bench_max_sizes": BENCH_MAX_SIZES,
                "bench_max_repeats": BENCH_MAX_REPEATS, "reference_max_n": REFERENCE_MAX_N},
    )


@app.route("/api/lab/run", methods=["POST"])
def api_lab_run():
    body = json_body()
    algorithm = body.get("algorithm")
    if algorithm not in ARRAY_ALGORITHMS:
        raise ApiError(f"'algorithm' deve ser um de: {', '.join(ARRAY_ALGORITHMS)}")
    seed = body_int(body, "seed", 21, 0, MAX_SEED)
    if "values" in body:
        values = body["values"]
    else:
        scenario = body.get("scenario", "aleatorio")
        if scenario not in ARRAY_SCENARIOS:
            raise ApiError(f"cenário deve ser um de: {', '.join(ARRAY_SCENARIOS)}")
        values = make_array(scenario, body_int(body, "n", 16, 1, LAB_MAX_N), seed)
    params = body.get("params") or {}
    if not isinstance(params, dict):
        raise ApiError("'params' deve ser um objeto")
    return jsonify(run_lab(algorithm, values, {**params, "seed": seed}))


@app.route("/api/compare")
def api_compare():
    return jsonify(compare_all(
        scenario=choice_arg("scenario", "aleatorio", tuple(ARRAY_SCENARIOS)),
        n=int_arg("n", 500, 2, COMPARE_MAX_N),
        seed=int_arg("seed", 21, 0, MAX_SEED),
        repeats=int_arg("repeats", 3, 1, BENCH_MAX_REPEATS),
    ))


@app.route("/api/benchmark")
def api_benchmark():
    algorithm = choice_arg("algorithm", "closest_pair", ALGORITHMS)
    raw_sizes = request.args.get("sizes", "250,500,1000,2000")
    try:
        sizes = [int(size) for size in raw_sizes.split(",") if size.strip()]
    except ValueError:
        raise ApiError("'sizes' deve ser uma lista de inteiros separados por vírgula") from None
    scenarios = POINT_SCENARIOS if algorithm == "closest_pair" else ARRAY_SCENARIOS
    seed = int_arg("seed", 21, 0, MAX_SEED)
    params = {"seed": seed}
    if algorithm in ("quick_sort", "quickselect"):
        pivots = SORT_PIVOTS if algorithm == "quick_sort" else SELECT_PIVOTS
        params["pivot"] = choice_arg("pivot", pivots[0] if algorithm == "quick_sort" else "aleatorio", pivots)
    return jsonify(run_benchmark(
        algorithm=algorithm,
        sizes=sizes,
        repeats=int_arg("repeats", 3, 1, BENCH_MAX_REPEATS),
        seed=seed,
        scenario=choice_arg("scenario", "aleatorio", tuple(scenarios)),
        params=params,
        warmup=choice_arg("warmup", "1", ("0", "1")) == "1",
    ))


@app.route("/api/exercises/new")
def api_exercise_new():
    kind = choice_arg("type", "inversoes", tuple(exercises.TYPES))
    return jsonify(exercises.new_exercise(kind, int_arg("seed", 1, 0, MAX_SEED)))


@app.route("/api/exercises/check", methods=["POST"])
def api_exercise_check():
    body = json_body()
    kind = body.get("type")
    if kind not in exercises.TYPES:
        raise ApiError(f"'type' deve ser um de: {', '.join(exercises.TYPES)}")
    seed = body_int(body, "seed", 1, 0, MAX_SEED)
    answer = body.get("answer")
    if isinstance(answer, bool) or not isinstance(answer, int):
        raise ApiError("'answer' deve ser um número inteiro")
    return jsonify(exercises.check(kind, seed, answer))


if __name__ == "__main__":
    # Debug só quando pedido explicitamente: FLASK_DEBUG=1 python app.py
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", threaded=True)
