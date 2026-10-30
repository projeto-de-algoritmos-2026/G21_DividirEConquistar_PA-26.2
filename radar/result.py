"""Resultado comum às soluções do par mais próximo."""
from dataclasses import dataclass, field


@dataclass
class PairResult:
    distance: float
    i: int
    j: int
    comparisons: int = 0
    steps: list = field(default_factory=list)
