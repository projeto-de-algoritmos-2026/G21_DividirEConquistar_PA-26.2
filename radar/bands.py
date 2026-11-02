"""Agrupamento por faixa de altitude e varredura do radar.

Parâmetros do modelo (não são regras operacionais): largura da faixa vertical
(padrão 1.000 ft) e limiar horizontal (padrão 5 NM). Aeronaves em faixas
diferentes são tratadas como separadas verticalmente, mesmo que estejam perto
do limite entre duas faixas.
"""
import math
import time
from collections import defaultdict

from radar.geo import KM_PER_NM
from radar.geodesic import closest_pair_geodesic, pairs_within_km

SEPARATION_NM = 5.0
BAND_FT = 1000
BAND_CHOICES = (500, 1000, 2000)
MIN_SEPARATION_NM = 0.5
MAX_SEPARATION_NM = 20.0


def flight_level(altitude_ft, band_ft=BAND_FT):
    """Arredonda a altitude para a faixa mais próxima (meio para cima), em FL.

    Usa floor(x + 0,5) em vez de round(): o round do Python arredonda empates
    para o par, o que mandava 36.500 ft para FL360 e 37.500 ft para FL380.
    """
    return math.floor(altitude_ft / band_ft + 0.5) * band_ft // 100


def group_by_band(aircraft, band_ft=BAND_FT):
    """Agrupa aeronaves por FL, preservando a ordem de entrada em cada faixa."""
    bands = defaultdict(list)
    for plane in aircraft:
        bands[flight_level(plane["altitude_ft"], band_ft)].append(plane)
    return bands


def scan(aircraft, separation_nm=SEPARATION_NM, band_ft=BAND_FT, all_pairs=False):
    """Roda o par geodésico mais próximo em cada faixa com 2+ aeronaves.

    Devolve (faixas, resumo). Cada faixa traz um único par: o mínimo da faixa.
    Com `all_pairs=True`, lista também todos os pares abaixo do limiar
    (busca por grade, não D&C).
    """
    started = time.perf_counter()
    report = []
    single = 0
    limit_km = separation_nm * KM_PER_NM
    for level, planes in sorted(group_by_band(aircraft, band_ft).items()):
        if len(planes) < 2:
            single += 1
            continue
        coords = [(plane["lat"], plane["lon"]) for plane in planes]
        result = closest_pair_geodesic(coords)
        first, second = planes[result.i], planes[result.j]
        band = {
            "flight_level": level,
            "aircraft_count": len(planes),
            "pair": [first, second],
            "distance_km": result.distance_km,
            "distance_nm": result.distance_km / KM_PER_NM,
            "comparisons": result.planar_comparisons,
            "candidate_pairs": result.candidate_pairs,
            "projection_corrected": result.corrected,
            "alert": result.distance_km < limit_km,
        }
        if all_pairs:
            pairs, candidates, truncated = pairs_within_km(coords, limit_km)
            band["close_pairs"] = [
                {"ids": [planes[a].get("id"), planes[b].get("id")], "distance_nm": d / KM_PER_NM} for a, b, d in pairs
            ]
            band["close_pairs_candidates"] = candidates
            band["close_pairs_truncated"] = truncated
        report.append(band)

    closest = min(report, key=lambda band: band["distance_km"], default=None)
    summary = {
        "aircraft": len(aircraft),
        "bands_total": len(report) + single,
        "bands_analyzed": len(report),
        "bands_single": single,
        "bands_below_threshold": sum(band["alert"] for band in report),
        "min_distance_nm": closest["distance_nm"] if closest else None,
        "min_flight_level": closest["flight_level"] if closest else None,
        "comparisons": sum(band["comparisons"] for band in report),
        "candidate_pairs": sum(band["candidate_pairs"] for band in report),
        "projection_corrections": sum(band["projection_corrected"] for band in report),
        "separation_nm": separation_nm,
        "band_ft": band_ft,
        "elapsed_ms": (time.perf_counter() - started) * 1000,
    }
    if all_pairs:
        summary["close_pairs"] = sum(len(band["close_pairs"]) for band in report)
        summary["close_pairs_truncated"] = any(band["close_pairs_truncated"] for band in report)
    return report, summary
