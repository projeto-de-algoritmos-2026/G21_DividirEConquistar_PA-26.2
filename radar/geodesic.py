"""Par geodésico exato: D&C no plano tangente + certificação por grade.

1. Projeta os pontos no plano tangente (radar.geo.TangentPlane), onde
   d_plano <= corda 3D para qualquer par.
2. Roda o par mais próximo D&C no plano: O(n log n). O par (i, j) achado dá
   um limite superior r = corda(i, j) para a menor corda verdadeira.
3. Todo par com corda < r tem d_plano < r. Uma grade de lado r encontra todos
   os k pares com d_plano < r em O(n + k), e a corda real decide entre eles.

Como o arco de círculo máximo cresce com a corda, o par de menor corda é o par
geodésico mais próximo. O resultado é exato sobre a esfera; o custo extra é
O(n + k), onde k depende da distorção da projeção (pequeno para pontos de uma
mesma região, até O(n²) em entradas patológicas espalhadas pelo globo).

A busca por grade não é dividir e conquistar: é hashing espacial, usado só
para certificar o resultado e para listar pares abaixo de um raio.
"""
import math
from collections import defaultdict
from dataclasses import dataclass, field

from radar.closest_pair import closest_pair
from radar.geo import TangentPlane, arc_to_chord_km, chord_to_arc_km, haversine_km, to_ecef

# Folga relativa contra erro de arredondamento na desigualdade d_plano <= corda.
EPSILON = 1e-9


@dataclass
class GeoPairResult:
    i: int
    j: int
    distance_km: float
    planar_comparisons: int
    candidate_pairs: int
    corrected: bool
    center: tuple
    planar_steps: list = field(default_factory=list)


def _chord(a, b):
    return math.dist(a, b)


def planar_pairs_within(points, radius):
    """Pares (a, b), a < b, com distância no plano <= radius, via grade."""
    if radius <= 0:
        return []
    cells = defaultdict(list)
    for index, (x, y) in enumerate(points):
        cells[(math.floor(x / radius), math.floor(y / radius))].append(index)
    pairs = []
    for (cx, cy), members in cells.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                others = cells.get((cx + dx, cy + dy))
                if not others:
                    continue
                for a in members:
                    for b in others:
                        if a < b and math.dist(points[a], points[b]) <= radius:
                            pairs.append((a, b))
    return pairs


def closest_pair_geodesic(coords, trace=False):
    """Par de menor distância de círculo máximo entre coordenadas (lat, lon)."""
    plane = TangentPlane(coords)
    planar = [plane.project(lat, lon) for lat, lon in coords]
    xyz = [to_ecef(lat, lon) for lat, lon in coords]
    fast = closest_pair(planar, trace=trace)
    best_i, best_j = fast.i, fast.j
    best_chord = _chord(xyz[best_i], xyz[best_j])
    candidates = []
    if best_chord > 0:
        candidates = planar_pairs_within(planar, best_chord * (1 + EPSILON) + EPSILON)
        for a, b in candidates:
            chord = _chord(xyz[a], xyz[b])
            if chord < best_chord:
                best_i, best_j, best_chord = a, b, chord
    i, j = sorted((best_i, best_j))
    return GeoPairResult(
        i=i,
        j=j,
        distance_km=haversine_km(*coords[i], *coords[j]),
        planar_comparisons=fast.comparisons,
        candidate_pairs=len(candidates),
        corrected={i, j} != {fast.i, fast.j},
        center=(plane.center_lat, plane.center_lon),
        planar_steps=fast.steps,
    )


def pairs_within_km(coords, limit_km, max_pairs=500):
    """Todos os pares com distância de círculo máximo < limit_km.

    Retorna (pares ordenados por distância, candidatos examinados, truncado).
    Custo O(n + k) com k candidatos da grade.
    """
    if len(coords) < 2 or limit_km <= 0:
        return [], 0, False
    plane = TangentPlane(coords)
    planar = [plane.project(lat, lon) for lat, lon in coords]
    xyz = [to_ecef(lat, lon) for lat, lon in coords]
    limit_chord = arc_to_chord_km(limit_km)
    candidates = planar_pairs_within(planar, limit_chord * (1 + EPSILON) + EPSILON)
    found = []
    for a, b in candidates:
        chord = _chord(xyz[a], xyz[b])
        if chord < limit_chord:
            found.append((chord_to_arc_km(chord), a, b))
    found.sort()
    truncated = len(found) > max_pairs
    pairs = [(a, b, haversine_km(*coords[a], *coords[b])) for _, a, b in found[:max_pairs]]
    return pairs, len(candidates), truncated
