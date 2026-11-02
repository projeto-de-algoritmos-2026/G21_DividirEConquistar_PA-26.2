"""Par de pontos mais próximos por dividir e conquistar, em O(n log n).

Cada subproblema devolve o próprio melhor par (resultado local). Assim, δ na
combinação é min(δ_esquerda, δ_direita) do subproblema, como no livro-texto, e
a trilha registrada descreve exatamente o que cada chamada sabe.
"""
import math

from radar.result import PairResult

BASE_CASE_SIZE = 3
MAX_TRACE_POINTS = 128

# Linhas do pseudocódigo (ver lab/catalog.py) citadas em cada etapa da trilha.
LINE_BASE, LINE_DIVIDE, LINE_COMBINE = 2, 3, 8


def validate_points(points):
    """Exige ao menos 2 pontos (x, y) com coordenadas finitas."""
    if len(points) < 2:
        raise ValueError("são necessários ao menos 2 pontos")
    for point in points:
        if len(point) != 2 or not all(isinstance(c, (int, float)) and math.isfinite(c) for c in point):
            raise ValueError(f"ponto inválido: {point!r}")


def closest_pair(points, trace=False):
    """Retorna o par mais próximo de `points`, uma sequência de pontos (x, y).

    `comparisons` conta cálculos de distância. Com `trace=True` (até
    MAX_TRACE_POINTS pontos), `steps` recebe as etapas e `tree` os nós da recursão.
    """
    validate_points(points)
    if trace and len(points) > MAX_TRACE_POINTS:
        raise ValueError(f"a trilha aceita no máximo {MAX_TRACE_POINTS} pontos")

    by_x = sorted(range(len(points)), key=lambda p: (points[p][0], points[p][1], p))
    by_y = sorted(range(len(points)), key=lambda p: (points[p][1], points[p][0], p))
    # A posição em by_x separa as metades mesmo com x repetido.
    rank = [0] * len(points)
    for position, point in enumerate(by_x):
        rank[point] = position
    result = PairResult(math.inf, -1, -1)

    def distance(a, b, compared):
        result.comparisons += 1
        if trace:
            compared.append([a, b])
        return math.dist(points[a], points[b])

    def solve(low, high, ys, depth, parent):
        """Resolve by_x[low:high]; `ys` são os mesmos pontos ordenados por y."""
        result.calls += 1
        result.max_depth = max(result.max_depth, depth)
        node = len(result.tree)
        if trace:
            result.tree.append({"id": node, "parent": parent, "depth": depth, "size": high - low,
                                "members": by_x[low:high], "distance": None, "pair": None})

        if high - low <= BASE_CASE_SIZE:
            best, compared = (math.inf, -1, -1), []
            for a in range(low, high):
                for b in range(a + 1, high):
                    d = distance(by_x[a], by_x[b], compared)
                    if d < best[0]:
                        best = (d, by_x[a], by_x[b])
            if trace:
                record("base", LINE_BASE, node, low, high, depth, best, compared=compared)
            return best

        middle = (low + high) // 2
        middle_x = points[by_x[middle]][0]
        if trace:
            record("divide", LINE_DIVIDE, node, low, high, depth, None, middle_x=middle_x)
        left_ys = [p for p in ys if rank[p] < middle]
        right_ys = [p for p in ys if rank[p] >= middle]
        left = solve(low, middle, left_ys, depth + 1, node)
        right = solve(middle, high, right_ys, depth + 1, node)
        best = left if left[0] <= right[0] else right
        delta = best[0]

        # Só pontos a menos de δ da divisão podem formar um par melhor.
        strip = [p for p in ys if abs(points[p][0] - middle_x) < delta]
        compared = []
        for position in range(len(strip)):
            a = strip[position]
            for other in range(position + 1, len(strip)):
                b = strip[other]
                # Com a faixa em ordem de y, no máximo 7 vizinhos passam daqui.
                if points[b][1] - points[a][1] >= best[0]:
                    break
                d = distance(a, b, compared)
                if d < best[0]:
                    best = (d, a, b)
        if trace:
            record("combine", LINE_COMBINE, node, low, high, depth, best, middle_x=middle_x, strip=strip,
                   compared=compared, delta=delta, left=left, right=right)
        return best

    def record(kind, line, node, low, high, depth, best, middle_x=None, strip=(), compared=(),
               delta=None, left=None, right=None):
        if best is not None and best[1] >= 0:
            result.tree[node]["distance"] = best[0]
            result.tree[node]["pair"] = [best[1], best[2]]
        result.steps.append({
            "kind": kind,
            "line": line,
            "node": node,
            "depth": depth,
            "size": high - low,
            "members": by_x[low:high],
            "low_x": points[by_x[low]][0],
            "high_x": points[by_x[high - 1]][0],
            "middle_x": middle_x,
            "strip": list(strip),
            "compared": list(compared),
            "delta": None if delta is None or math.isinf(delta) else delta,
            "left": pair_json(left),
            "right": pair_json(right),
            # Melhor par do subproblema (local), não o melhor global até agora.
            "best": pair_json(best),
            "comparisons_total": result.comparisons,
        })

    def pair_json(best):
        if best is None or best[1] < 0:
            return None
        return {"pair": [best[1], best[2]], "distance": best[0]}

    result.distance, result.i, result.j = solve(0, len(points), by_y, 0, None)
    return result
