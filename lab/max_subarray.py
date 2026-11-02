"""Subarray contíguo de soma máxima por dividir e conquistar, O(n log n)."""
from lab.metrics import Run


def max_subarray(values, trace=False):
    """Retorna ((soma, início, fim exclusivo), Run) para um vetor não vazio.

    `comparisons` conta comparações entre somas, a mesma unidade da força bruta.
    """
    if not values:
        raise ValueError("o vetor não pode ser vazio")
    a = list(values)
    run = Run(trace=trace)

    def better(x, y):
        run.comparisons += 1
        return x[0] > y[0]

    def solve(lo, hi, depth):
        run.enter(depth)
        if hi - lo == 1:
            if trace:
                run.step("base", 2, f"Um elemento: a melhor soma de [{lo}, {hi}) é {a[lo]}.",
                     lo=lo, hi=hi, depth=depth, best=[a[lo], lo, hi])
            return (a[lo], lo, hi)
        mid = (lo + hi) // 2
        if trace:
            run.step("divide", 3, f"Divide [{lo}, {hi}) em [{lo}, {mid}) e [{mid}, {hi}).",
                 lo=lo, hi=hi, mid=mid, depth=depth)
        left = solve(lo, mid, depth + 1)
        right = solve(mid, hi, depth + 1)

        # Melhor sufixo da esquerda + melhor prefixo da direita.
        total, best_left = 0, (a[mid - 1], mid - 1)
        for i in range(mid - 1, lo - 1, -1):
            total += a[i]
            if better((total, i), best_left):
                best_left = (total, i)
        total, best_right = 0, (a[mid], mid + 1)
        for j in range(mid, hi):
            total += a[j]
            if better((total, j + 1), best_right):
                best_right = (total, j + 1)
        cross = (best_left[0] + best_right[0], best_left[1], best_right[1])

        best = left
        if better(right, best):
            best = right
        if better(cross, best):
            best = cross
        if trace:
            run.step("combine", 7, f"Esquerda {left[0]}, direita {right[0]}, cruzando a divisão {cross[0]}: "
                     f"fica {best[0]} em [{best[1]}, {best[2]}).",
                 lo=lo, hi=hi, mid=mid, depth=depth, left=list(left), right=list(right),
                 cross=list(cross), best=list(best))
        return best

    return solve(0, len(a), 0), run
