"""Fontes de tráfego aéreo: simulação com seed e snapshot real da OpenSky."""
import json
import math
import random
from pathlib import Path

from radar.geo import KM_PER_NM, haversine_km

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "opensky_snapshot.json"

AIRPORTS = {
    "GRU": (-23.43, -46.47),
    "BSB": (-15.87, -47.92),
    "GIG": (-22.81, -43.25),
    "CNF": (-19.63, -43.97),
    "SSA": (-12.91, -38.33),
    "REC": (-8.13, -34.92),
    "FOR": (-3.78, -38.53),
    "POA": (-29.99, -51.17),
    "CWB": (-25.53, -49.18),
    "MAO": (-3.04, -60.05),
    "BEL": (-1.38, -48.48),
}
AIRLINES = ("GLO", "TAM", "AZU", "PTB")
MIN_FLIGHT_LEVEL = 280
MAX_FLIGHT_LEVEL = 410


def generate_traffic(n, seed=21, minutes=0):
    """Gera n voos em rotas entre aeroportos, avançados `minutes` no tempo."""
    rng = random.Random(seed)
    names = list(AIRPORTS)
    traffic = []
    for _ in range(n):
        origin, destination = rng.sample(names, 2)
        lat1, lon1 = AIRPORTS[origin]
        lat2, lon2 = AIRPORTS[destination]
        speed_kt = rng.randint(420, 480)
        route_km = haversine_km(lat1, lon1, lat2, lon2)
        progress = rng.random() + speed_kt * KM_PER_NM * minutes / 60 / route_km
        progress %= 1  # ao chegar, o voo recomeça a rota
        traffic.append({
            "callsign": f"{rng.choice(AIRLINES)}{rng.randint(1000, 9999)}",
            "lat": lat1 + (lat2 - lat1) * progress + rng.gauss(0, 0.06),
            "lon": lon1 + (lon2 - lon1) * progress + rng.gauss(0, 0.06),
            "altitude_ft": rng.randrange(MIN_FLIGHT_LEVEL, MAX_FLIGHT_LEVEL + 1, 10) * 100,
            "heading": round(math.degrees(math.atan2(lon2 - lon1, lat2 - lat1))) % 360,
            "speed_kt": speed_kt,
        })
    return traffic


def load_snapshot():
    """Carrega as aeronaves reais capturadas da API da OpenSky Network."""
    with SNAPSHOT_PATH.open(encoding="utf-8") as file:
        return json.load(file)["aircraft"]
