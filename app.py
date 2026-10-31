"""Radar de Conflitos Aéreos: servidor Flask."""
from flask import Flask, jsonify, render_template, request

from radar.bands import group_by_band, scan
from radar.generator import generate_traffic, load_snapshot
from radar.benchmark import run_benchmark
from radar.closest_pair import closest_pair
from radar.geo import project

app = Flask(__name__)
MAX_AIRCRAFT = 3000
MAX_MINUTES = 240


@app.route("/")
def index():
    return render_template("index.html")


def int_arg(name, default, low, high):
    """Lê um inteiro da query string, limitado ao intervalo aceito."""
    value = request.args.get(name, default, type=int)
    return max(low, min(high, value))


def load_traffic():
    if request.args.get("source") == "opensky":
        return load_snapshot()
    return generate_traffic(
        int_arg("n", 400, 2, MAX_AIRCRAFT),
        request.args.get("seed", 21, type=int),
        int_arg("minutes", 0, 0, MAX_MINUTES),
    )


@app.route("/api/scan")
def api_scan():
    aircraft = load_traffic()
    return jsonify(aircraft=aircraft, bands=scan(aircraft))


@app.route("/api/steps")
def api_steps():
    """Etapas da recursão na faixa com mais aeronaves."""
    bands = group_by_band(load_traffic())
    level, planes = max(bands.items(), key=lambda band: len(band[1]))
    planes = planes[:64]
    if len(planes) < 2:
        return jsonify(error="nenhuma faixa tem duas aeronaves"), 400
    points = [project(plane["lat"], plane["lon"]) for plane in planes]
    result = closest_pair(points, trace=True)
    return jsonify(flight_level=level, points=points, steps=result.steps)


@app.route("/api/benchmark")
def api_benchmark():
    return jsonify(rows=run_benchmark())


if __name__ == "__main__":
    app.run(debug=True)
