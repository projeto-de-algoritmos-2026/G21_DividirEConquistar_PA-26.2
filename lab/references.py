"""Referências independentes, escritas sem reaproveitar o código D&C.

Cada função devolve (resultado, comparações) na mesma unidade do algoritmo
D&C correspondente, para que as contagens sejam comparáveis.
"""


def insertion_sort(values):
    """Ordenação por inserção, O(n²) no pior caso; comparações entre elementos."""
    a = list(values)
    comparisons = 0
    for i in range(1, len(a)):
        current = a[i]
        j = i - 1
        while j >= 0:
            comparisons += 1
            if a[j] <= current:
                break
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = current
    return a, comparisons


def inversions_brute(values):
    """Conta pares i < j com a[i] > a[j] testando todos: n(n−1)/2 comparações."""
    count = comparisons = 0
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            comparisons += 1
            if values[i] > values[j]:
                count += 1
    return count, comparisons


def select_by_sorting(values, k):
    """k-ésimo menor ordenando por inserção e indexando (k começa em 1)."""
    ordered, comparisons = insertion_sort(values)
    return ordered[k - 1], comparisons


def max_subarray_brute(values):
    """Testa todos os n(n+1)/2 subarrays com somas acumuladas: O(n²)."""
    best = (values[0], 0, 1)
    comparisons = 0
    for i in range(len(values)):
        total = 0
        for j in range(i, len(values)):
            total += values[j]
            comparisons += 1
            if total > best[0]:
                best = (total, i, j + 1)
    return best, comparisons


def kadane(values):
    """Algoritmo de Kadane, O(n). Programação dinâmica, não é D&C."""
    best = (values[0], 0, 1)
    current, start = values[0], 0
    comparisons = 0
    for j in range(1, len(values)):
        comparisons += 1
        if current < 0:
            current, start = values[j], j
        else:
            current += values[j]
        comparisons += 1
        if current > best[0]:
            best = (current, start, j + 1)
    return best, comparisons
