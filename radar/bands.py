"""Detecção de conflitos por faixa de altitude."""
from collections import defaultdict

from radar.closest_pair import closest_pair
from radar.geo import KM_PER_NM, haversine_km, project

SEPARATION_NM = 5.0


def flight_level(altitude_ft):
    """Arredonda a altitude para o nível de voo (FL) a cada 1.000 pés."""
    return round(altitude_ft / 1000) * 10


def group_by_band(aircraft):
    """Agrupa aeronaves por FL: voos em níveis diferentes já estão separados."""
    bands = defaultdict(list)
    for plane in aircraft:
        bands[flight_level(plane["altitude_ft"])].append(plane)
    return bands


def scan(aircraft, solver=closest_pair, separation_nm=SEPARATION_NM):
    """Roda o par mais próximo em cada faixa e marca as abaixo da separação."""
    report = []
    for level, planes in sorted(group_by_band(aircraft).items()):
        if len(planes) < 2:
            continue
        points = [project(plane["lat"], plane["lon"]) for plane in planes]
        result = solver(points)
        first, second = planes[result.i], planes[result.j]
        # A projeção escolhe o par; a distância exibida vem da esfera.
        distance_km = haversine_km(first["lat"], first["lon"], second["lat"], second["lon"])
        distance_nm = distance_km / KM_PER_NM
        report.append({
            "flight_level": level,
            "aircraft_count": len(planes),
            "pair": [first, second],
            "distance_km": distance_km,
            "distance_nm": distance_nm,
            "comparisons": result.comparisons,
            "alert": distance_nm < separation_nm,
        })
    return report
