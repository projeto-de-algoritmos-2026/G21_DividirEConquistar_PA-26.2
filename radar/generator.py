"""Fontes de tráfego aéreo: simulação com seed e snapshot histórico da OpenSky."""
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar.geo import KM_PER_NM, haversine_km

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "opensky_snapshot.json"
BRASILIA = timezone(timedelta(hours=-3), "UTC-03:00")

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


class SnapshotError(RuntimeError):
    """O arquivo do snapshot está ausente ou inválido."""


def generate_traffic(n, seed=21, minutes=0):
    """Gera n voos em rotas entre aeroportos, avançados `minutes` no tempo.

    Determinístico: a mesma (n, seed, minutes) produz sempre o mesmo tráfego, e
    um voo mantém rota e callsign quando só `minutes` muda.
    """
    rng = random.Random(seed)
    names = list(AIRPORTS)
    traffic = []
    for index in range(n):
        origin, destination = rng.sample(names, 2)
        lat1, lon1 = AIRPORTS[origin]
        lat2, lon2 = AIRPORTS[destination]
        speed_kt = rng.randint(420, 480)
        route_km = haversine_km(lat1, lon1, lat2, lon2)
        progress = rng.random() + speed_kt * KM_PER_NM * minutes / 60 / route_km
        progress %= 1  # ao chegar, o voo recomeça a rota
        traffic.append({
            "id": index,
            "callsign": f"{rng.choice(AIRLINES)}{rng.randint(1000, 9999)}",
            "lat": lat1 + (lat2 - lat1) * progress + rng.gauss(0, 0.06),
            "lon": lon1 + (lon2 - lon1) * progress + rng.gauss(0, 0.06),
            "altitude_ft": rng.randrange(MIN_FLIGHT_LEVEL, MAX_FLIGHT_LEVEL + 1, 10) * 100,
            "heading": round(math.degrees(math.atan2(lon2 - lon1, lat2 - lat1))) % 360,
            "speed_kt": speed_kt,
            "route": f"{origin}→{destination}",
        })
    return traffic


def _valid(plane):
    try:
        lat, lon, alt = float(plane["lat"]), float(plane["lon"]), float(plane["altitude_ft"])
    except (KeyError, TypeError, ValueError):
        return False
    return all(map(math.isfinite, (lat, lon, alt))) and -90 <= lat <= 90 and -180 <= lon <= 180


def read_snapshot(path=SNAPSHOT_PATH):
    """Lê o snapshot e devolve (aeronaves válidas, metadados)."""
    try:
        with Path(path).open(encoding="utf-8") as file:
            data = json.load(file)
        raw = data["aircraft"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SnapshotError(f"snapshot indisponível: {type(error).__name__}") from error

    aircraft = []
    for plane in raw:
        if isinstance(plane, dict) and _valid(plane):
            aircraft.append({**plane, "id": len(aircraft), "callsign": str(plane.get("callsign") or "?").strip()})
    meta = {"kind": "opensky", "label": "Snapshot histórico OpenSky Network", "origin": data.get("source"),
            "records": len(raw), "discarded": len(raw) - len(aircraft)}
    captured = data.get("captured_at")
    if isinstance(captured, (int, float)):
        moment = datetime.fromtimestamp(captured, timezone.utc)
        meta["captured_at_utc"] = moment.isoformat()
        meta["captured_at_local"] = moment.astimezone(BRASILIA).isoformat()
    return aircraft, meta


def load_snapshot():
    """Aeronaves válidas do snapshot histórico (não é dado em tempo real)."""
    return read_snapshot()[0]
