"""Exercícios gerados por seed e corrigidos no servidor com os próprios algoritmos.

O enunciado não traz a resposta: a correção regenera o exercício pela seed e
calcula o gabarito com o algoritmo D&C, conferido com a referência.
"""
import math
import random

from lab import references
from lab.max_subarray import max_subarray
from lab.selection import quickselect
from lab.sorting import merge_sort

TYPES = {
    "inversoes": "Contagem de inversões",
    "soma_maxima": "Subarray de soma máxima",
    "k_esimo": "k-ésimo menor (Quickselect)",
    "teorema_mestre": "Teorema Mestre",
}


def build(kind, seed):
    """Retorna (enunciado público, gabarito, explicação)."""
    rng = random.Random(f"{kind}:{seed}")
    if kind == "inversoes":
        values = rng.sample(range(1, 20), 8)
        _, _, answer = merge_sort(values, count_inversions=True)
        assert answer == references.inversions_brute(values)[0]
        return ({"enunciado": "Quantas inversões (pares i < j com A[i] > A[j]) tem o vetor?", "values": values,
                 "answer_type": "integer"}, answer,
                "Conte, na intercalação, quantos elementos da esquerda ainda restam quando um da direita sai.")
    if kind == "soma_maxima":
        values = [rng.randint(-9, 9) for _ in range(10)]
        (answer, lo, hi), _ = max_subarray(values)
        assert answer == references.max_subarray_brute(values)[0][0]
        return ({"enunciado": "Qual é a maior soma de um trecho contíguo não vazio?", "values": values,
                 "answer_type": "integer"}, answer,
                f"O trecho A[{lo}..{hi - 1}] soma {answer}; compare o melhor da esquerda, da direita e o que cruza o meio.")
    if kind == "k_esimo":
        values = rng.sample(range(1, 60), 9)
        k = rng.randint(1, 9)
        answer, _ = quickselect(values, k, pivot="aleatorio", seed=seed)
        assert answer == sorted(values)[k - 1]
        return ({"enunciado": f"Qual é o {k}º menor elemento?", "values": values, "k": k,
                 "answer_type": "integer"}, answer,
                "Particione pelo pivô e continue só no lado que contém a posição k.")
    if kind == "teorema_mestre":
        a = rng.choice((1, 2, 3, 4, 7, 8))
        b = rng.choice((2, 4))
        d = rng.choice((0, 1, 2))
        critical = math.log(a, b)
        if math.isclose(d, critical):
            answer, why = 1, f"d = {d} = log_{b} {a}: caso 2."
        elif d > critical:
            answer, why = 0, f"d = {d} > log_{b} {a} ≈ {critical:.2f}: caso 3, f(n) domina."
        else:
            answer, why = 2, f"d = {d} < log_{b} {a} ≈ {critical:.2f}: caso 1, as folhas dominam."
        f = {0: "1", 1: "n", 2: "n²"}[d]
        options = [f"Θ({f})", "Θ(log n)" if d == 0 else f"Θ({f} log n)", f"Θ(n^(log_{b} {a}))"]
        return ({"enunciado": f"T(n) = {a if a > 1 else ''}T(n/{b}) + Θ({f}). Qual é a solução assintótica?", "a": a, "b": b,
                 "d": d, "options": options, "answer_type": "option"}, answer, why)
    raise ValueError(f"tipo desconhecido: {kind}")


def new_exercise(kind, seed):
    public, _, _ = build(kind, seed)
    return {"type": kind, "title": TYPES[kind], "seed": seed, **public}


def check(kind, seed, answer):
    _, expected, explanation = build(kind, seed)
    return {"correct": answer == expected, "expected": expected, "explanation": explanation}
