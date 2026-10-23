"""Conversões geográficas usadas pelo radar."""
import math

EARTH_RADIUS_KM = 6371.0
KM_PER_NM = 1.852

# Centro da projeção: aproximadamente o centro do Brasil.
ORIGIN_LAT = -15.0
ORIGIN_LON = -52.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Distância real entre dois pontos sobre a esfera terrestre."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def project(lat, lon):
    """Projeção equirretangular: converte (lat, lon) em (x, y) no plano, em km."""
    x = EARTH_RADIUS_KM * math.radians(lon - ORIGIN_LON) * math.cos(math.radians(ORIGIN_LAT))
    y = EARTH_RADIUS_KM * math.radians(lat - ORIGIN_LAT)
    return x, y
