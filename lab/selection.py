"""Quickselect (k-ésimo menor) com partição em três vias, instrumentado."""
import random

from lab.metrics import Run

PIVOTS = ("ultimo", "mediana3", "aleatorio", "mediana_medianas")


def quickselect(values, k, pivot="aleatorio", seed=0, trace=False):
    """Retorna (k-ésimo menor valor, Run), com k começando em 1.

    A partição em três vias (menores, iguais, maiores) evita a degradação com
    valores repetidos. `comparisons` conta comparações entre elementos.
    """
    if pivot not in PIVOTS:
        raise ValueError(f"pivô desconhecido: {pivot}")
    if not 1 <= k <= len(values):
        raise ValueError(f"k deve estar entre 1 e {len(values)}")
    run = Run(trace=trace)
    rng = random.Random(seed)

    def less(x, y):
        run.comparisons += 1
        return x < y

    def small_median(group):
        """Mediana de até 5 elementos por inserção (comparações contadas)."""
        items = list(group)
        for i in range(1, len(items)):
            j = i
            while j > 0 and less(items[j], items[j - 1]):
                items[j], items[j - 1] = items[j - 1], items[j]
                j -= 1
        return items[(len(items) - 1) // 2]

    def choose(items, depth):
        if pivot == "ultimo":
            return items[-1]
        if pivot == "aleatorio":
            return items[rng.randrange(len(items))]
        if pivot == "mediana3":
            return small_median((items[0], items[len(items) // 2], items[-1]))
        if len(items) <= 5:
            return small_median(items)
        # Mediana das medianas: grupos de 5 e seleção recursiva da mediana.
        medians = [small_median(items[i:i + 5]) for i in range(0, len(items), 5)]
        return select(medians, (len(medians) + 1) // 2, depth + 1, nested=True)

    def select(items, rank, depth, nested=False):
        items = list(items)
        while True:
            run.enter(depth)
            if len(items) == 1:
                if trace and not nested:
                    run.step("base", 2, f"Resta um elemento: {items[0]} é o {rank}º menor.",
                             depth=depth, array=items, rank=rank, answer=items[0])
                return items[0]
            p = choose(items, depth)
            lows, equals, highs = [], [], []
            for item in items:
                if less(item, p):
                    lows.append(item)
                elif less(p, item):
                    highs.append(item)
                else:
                    equals.append(item)
            run.moves += len(items)
            if trace and not nested:
                run.step("partition", 4, f"Pivô {p}: {len(lows)} menores, {len(equals)} iguais, {len(highs)} maiores.",
                         depth=depth, array=items, rank=rank, pivot=p, lows=lows, equals=equals, highs=highs)
            if rank <= len(lows):
                items = lows
                where = "menores"
            elif rank <= len(lows) + len(equals):
                if trace and not nested:
                    run.step("combine", 6, f"O {rank}º menor está entre os iguais ao pivô: resposta {p}.",
                             depth=depth, array=items, rank=rank, answer=p)
                return p
            else:
                rank -= len(lows) + len(equals)
                items = highs
                where = "maiores"
            if trace and not nested:
                run.step("divide", 5 if where == "menores" else 7,
                         f"Continua só na parte dos {where}, procurando o {rank}º menor.",
                         depth=depth, array=items, rank=rank)
            depth += 1

    return select(values, k, 0), run
