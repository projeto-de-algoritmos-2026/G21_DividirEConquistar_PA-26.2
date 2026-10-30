"""Radar de Conflitos Aéreos: servidor Flask."""
from flask import Flask, jsonify, render_template, request

from radar.bands import group_by_band, scan
from radar.generator import generate_traffic, load_snapshot
from radar.closest_pair import closest_pair
from radar.geo import project

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


def load_traffic():
    if request.args.get("source") == "opensky":
        return load_snapshot()
    return generate_traffic(
        request.args.get("n", 400, type=int),
        request.args.get("seed", 21, type=int),
        request.args.get("minutes", 0, type=int),
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
    points = [project(plane["lat"], plane["lon"]) for plane in planes]
    result = closest_pair(points, trace=True)
    return jsonify(flight_level=level, points=points, steps=result.steps)


if __name__ == "__main__":
    app.run(debug=True)
