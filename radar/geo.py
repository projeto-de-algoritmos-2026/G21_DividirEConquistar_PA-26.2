"""Conversões geográficas usadas pelo radar.

O modelo é a Terra como esfera de raio 6.371 km. A distância "real" exibida é
a de círculo máximo (haversine). Elipsoide e altitude não entram no cálculo.
"""
import math

EARTH_RADIUS_KM = 6371.0
KM_PER_NM = 1.852

# Origem da projeção equirretangular antiga (aproximadamente o centro do Brasil).
ORIGIN_LAT = -15.0
ORIGIN_LON = -52.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Distância de círculo máximo entre dois pontos da esfera, em km."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def project(lat, lon):
    """Projeção equirretangular de origem fixa, em km.

    Mantida só para demonstrar a limitação da versão anterior: longe da latitude
    de origem ela distorce distâncias leste-oeste e pode escolher o par errado.
    """
    x = EARTH_RADIUS_KM * math.radians(lon - ORIGIN_LON) * math.cos(math.radians(ORIGIN_LAT))
    y = EARTH_RADIUS_KM * math.radians(lat - ORIGIN_LAT)
    return x, y


def to_ecef(lat, lon):
    """Ponto da esfera em coordenadas cartesianas 3D, em km."""
    phi, lam = math.radians(lat), math.radians(lon)
    return (
        EARTH_RADIUS_KM * math.cos(phi) * math.cos(lam),
        EARTH_RADIUS_KM * math.cos(phi) * math.sin(lam),
        EARTH_RADIUS_KM * math.sin(phi),
    )


def chord_to_arc_km(chord_km):
    """Converte a corda 3D em distância de círculo máximo (função crescente)."""
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, chord_km / (2 * EARTH_RADIUS_KM)))


def arc_to_chord_km(arc_km):
    """Inversa de `chord_to_arc_km`, para arcos de até meia circunferência."""
    return 2 * EARTH_RADIUS_KM * math.sin(min(math.pi / 2, arc_km / (2 * EARTH_RADIUS_KM)))


class TangentPlane:
    """Projeção ortográfica no plano tangente ao centro de um grupo de pontos.

    É a projeção ortogonal do vetor 3D sobre o plano gerado pelos eixos leste e
    norte do centro. Por ser ortogonal, a distância no plano nunca passa da
    corda 3D: d_plano(a, b) <= corda(a, b). Essa desigualdade vale para
    quaisquer pontos e é o que permite certificar o par geodésico exato.
    """

    def __init__(self, coords):
        sx = sy = sz = 0.0
        for lat, lon in coords:
            x, y, z = to_ecef(lat, lon)
            sx, sy, sz = sx + x, sy + y, sz + z
        norm = math.sqrt(sx * sx + sy * sy + sz * sz)
        if norm < 1e-9 * EARTH_RADIUS_KM * max(1, len(coords)):
            # Pontos espalhados simetricamente: usa o primeiro como centro.
            sx, sy, sz = to_ecef(*coords[0])
            norm = EARTH_RADIUS_KM
        self.center_lat = math.degrees(math.asin(max(-1.0, min(1.0, sz / norm))))
        self.center_lon = math.degrees(math.atan2(sy, sx))
        phi, lam = math.radians(self.center_lat), math.radians(self.center_lon)
        self.east = (-math.sin(lam), math.cos(lam), 0.0)
        self.north = (-math.sin(phi) * math.cos(lam), -math.sin(phi) * math.sin(lam), math.cos(phi))

    def project(self, lat, lon):
        x, y, z = to_ecef(lat, lon)
        return (
            x * self.east[0] + y * self.east[1] + z * self.east[2],
            x * self.north[0] + y * self.north[1] + z * self.north[2],
        )
