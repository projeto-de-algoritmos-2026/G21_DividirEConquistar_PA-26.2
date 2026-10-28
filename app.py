"""Radar de Conflitos Aéreos: servidor Flask."""
from flask import Flask, jsonify, render_template, request

from radar.bands import scan
from radar.generator import generate_traffic, load_snapshot

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


if __name__ == "__main__":
    app.run(debug=True)
