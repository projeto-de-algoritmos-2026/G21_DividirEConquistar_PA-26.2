"""Merge Sort, contagem de inversões e Quick Sort, instrumentados."""
import random

from lab.metrics import Run

PIVOTS = ("ultimo", "mediana3", "aleatorio")


def merge_sort(values, trace=False, count_inversions=False):
    """Merge Sort estável. Retorna (vetor ordenado, Run, inversões).

    `comparisons` conta comparações entre elementos; `moves` conta escritas no
    vetor durante a intercalação. Inversões: pares i < j com a[i] > a[j].
    """
    a = list(values)
    run = Run(trace=trace)
    inversions = 0

    def sort(lo, hi, depth):
        nonlocal inversions
        run.enter(depth)
        if hi - lo <= 1:
            if trace:
                run.step("base", 2, f"Subvetor [{lo}, {hi}) tem {hi - lo} elemento: já está ordenado.",
                     lo=lo, hi=hi, depth=depth, array=list(a))
            return
        mid = (lo + hi) // 2
        if trace:
            run.step("divide", 3, f"Divide [{lo}, {hi}) em [{lo}, {mid}) e [{mid}, {hi}).",
                 lo=lo, hi=hi, mid=mid, depth=depth, array=list(a))
        sort(lo, mid, depth + 1)
        sort(mid, hi, depth + 1)

        left, right = a[lo:mid], a[mid:hi]
        i = j = 0
        k = lo
        counted = 0
        while i < len(left) and j < len(right):
            run.comparisons += 1
            # Empate sai da esquerda: é isso que torna o Merge Sort estável.
            if right[j] < left[i]:
                a[k] = right[j]
                counted += len(left) - i
                if trace:
                    note = f"{right[j]} < {left[i]}: sai da direita"
                    if count_inversions:
                        note += f" e forma {len(left) - i} inversão(ões) com o resto da esquerda"
                j += 1
                side = "right"
            else:
                a[k] = left[i]
                if trace:
                    note = f"{left[i]} ≤ {right[j]}: sai da esquerda (empate preserva a ordem)"
                i += 1
                side = "left"
            run.moves += 1
            if trace:
                run.step("merge", 7, note + ".", lo=lo, hi=hi, mid=mid, depth=depth, write=k, side=side, array=list(a),
                         inversions=inversions + counted)
            k += 1
        for value in left[i:] + right[j:]:
            a[k] = value
            run.moves += 1
            k += 1
        inversions += counted
        if trace:
            run.step("combine", 8, f"Intercalação de [{lo}, {hi}) concluída"
                 + (f"; {counted} inversão(ões) cruzando a divisão." if count_inversions else "."),
                 lo=lo, hi=hi, mid=mid, depth=depth, array=list(a), inversions=inversions)

    sort(0, len(a), 0)
    return a, run, inversions


def quick_sort(values, pivot="ultimo", seed=0, trace=False):
    """Quick Sort com partição de Lomuto. Retorna (vetor ordenado, Run).

    Recursão na parte menor e laço na maior: a pilha fica em O(log n) mesmo no
    pior caso, mas `max_depth` registra a profundidade lógica da árvore.
    """
    if pivot not in PIVOTS:
        raise ValueError(f"pivô desconhecido: {pivot}")
    a = list(values)
    run = Run(trace=trace)
    rng = random.Random(seed)

    def less(x, y):
        run.comparisons += 1
        return x < y

    def choose(lo, hi):
        if pivot == "ultimo":
            return hi - 1
        if pivot == "aleatorio":
            return rng.randrange(lo, hi)
        # Rede de 3 comparações: ao final, `mid` aponta para a mediana.
        first, mid, last = lo, (lo + hi) // 2, hi - 1
        if less(a[mid], a[first]):
            first, mid = mid, first
        if less(a[last], a[mid]):
            mid, last = last, mid
        if less(a[mid], a[first]):
            first, mid = mid, first
        return mid

    def swap(i, j):
        if i != j:
            a[i], a[j] = a[j], a[i]
            run.moves += 1

    def sort(lo, hi, depth):
        while True:
            run.enter(depth)
            if hi - lo <= 1:
                if trace:
                    run.step("base", 2, f"Subvetor [{lo}, {hi}) com {hi - lo} elemento: nada a fazer.",
                         lo=lo, hi=hi, depth=depth, array=list(a))
                return
            p = choose(lo, hi)
            swap(p, hi - 1)
            value = a[hi - 1]
            if trace:
                run.step("pivot", 3, f"Pivô {value} (estratégia {pivot}) vai para a posição {hi - 1}.",
                         lo=lo, hi=hi, depth=depth, pivot=hi - 1, array=list(a))
            i = lo
            for j in range(lo, hi - 1):
                if less(a[j], value):
                    swap(i, j)
                    if trace:
                        run.step("partition", 6, f"{a[i]} < {value}: vai para a parte menor (posição {i}).",
                                 lo=lo, hi=hi, depth=depth, pivot=hi - 1, i=i, j=j, array=list(a))
                    i += 1
                else:
                    if trace:
                        run.step("partition", 6, f"{a[j]} ≥ {value}: fica na parte maior.",
                                 lo=lo, hi=hi, depth=depth, pivot=hi - 1, i=i, j=j, array=list(a))
            swap(i, hi - 1)
            if trace:
                run.step("combine", 7, f"Pivô {value} na posição final {i}: [{lo}, {i}) < {value} ≤ ({i}, {hi}).",
                     lo=lo, hi=hi, depth=depth, pivot=i, array=list(a))
            if i - lo < hi - i - 1:
                sort(lo, i, depth + 1)
                lo = i + 1
            else:
                sort(i + 1, hi, depth + 1)
                hi = i
            depth += 1

    sort(0, len(a), 0)
    return a, run
