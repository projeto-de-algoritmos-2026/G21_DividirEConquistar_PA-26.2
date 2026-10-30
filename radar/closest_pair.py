"""Par de pontos mais próximos por dividir e conquistar, em O(n log n)."""
import math

from radar.result import PairResult

BASE_CASE_SIZE = 3


def closest_pair(points, trace=False):
    """Retorna o par mais próximo de `points`, uma sequência de pontos (x, y).

    Com `trace=True`, registra em `steps` as etapas da recursão.
    """
    if len(points) < 2:
        raise ValueError("são necessários ao menos 2 pontos")

    by_x = sorted(range(len(points)), key=lambda p: (points[p][0], points[p][1], p))
    by_y = sorted(range(len(points)), key=lambda p: (points[p][1], points[p][0], p))
    # A posição em by_x separa as metades mesmo com pontos repetidos.
    rank = {point: position for position, point in enumerate(by_x)}
    result = PairResult(math.inf, -1, -1)

    def compare(a, b):
        result.comparisons += 1
        distance = math.dist(points[a], points[b])
        if distance < result.distance:
            result.distance, result.i, result.j = distance, a, b

    def solve(low, high, ys, depth):
        """Resolve by_x[low:high]; `ys` são os mesmos pontos ordenados por y."""
        if high - low <= BASE_CASE_SIZE:
            for a in range(low, high):
                for b in range(a + 1, high):
                    compare(by_x[a], by_x[b])
            if trace:
                record("base", low, high, depth)
            return

        middle = (low + high) // 2
        middle_x = points[by_x[middle]][0]
        if trace:
            record("divide", low, high, depth, middle_x=middle_x)
        left_ys = [p for p in ys if rank[p] < middle]
        right_ys = [p for p in ys if rank[p] >= middle]
        solve(low, middle, left_ys, depth + 1)
        solve(middle, high, right_ys, depth + 1)

        # Só pontos a menos de delta da divisão podem formar um par melhor.
        strip = [p for p in ys if abs(points[p][0] - middle_x) < result.distance]
        for position, a in enumerate(strip):
            for b in strip[position + 1:]:
                # Com a faixa ordenada por y, no máximo 7 vizinhos passam daqui.
                if points[b][1] - points[a][1] >= result.distance:
                    break
                compare(a, b)
        if trace:
            record("combine", low, high, depth, middle_x=middle_x, strip=strip)

    def record(kind, low, high, depth, middle_x=None, strip=()):
        result.steps.append({
            "kind": kind,
            "low_x": points[by_x[low]][0],
            "high_x": points[by_x[high - 1]][0],
            "size": high - low,
            "depth": depth,
            "middle_x": middle_x,
            "strip": list(strip),
            "best": [result.i, result.j],
            "distance": result.distance if result.i >= 0 else None,
        })

    solve(0, len(points), by_y, 0)
    return result
