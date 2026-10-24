"""Resultado comum às soluções do par mais próximo."""
from dataclasses import dataclass


@dataclass
class PairResult:
    distance: float
    i: int
    j: int
    comparisons: int = 0
