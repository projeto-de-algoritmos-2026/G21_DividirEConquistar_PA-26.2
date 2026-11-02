"""Solução de referência do par mais próximo, em O(n²)."""
import math

from radar.closest_pair import validate_points
from radar.result import PairResult


def closest_pair_brute(points):
    """Compara todos os pares de pontos (x, y)."""
    validate_points(points)
    best = PairResult(math.inf, -1, -1)
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            best.comparisons += 1
            distance = math.dist(points[i], points[j])
            if distance < best.distance:
                best.distance, best.i, best.j = distance, i, j
    return best
