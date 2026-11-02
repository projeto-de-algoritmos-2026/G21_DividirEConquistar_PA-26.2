"""Contadores e trilha de etapas compartilhados pelos algoritmos do laboratório."""
from dataclasses import dataclass, field

MAX_STEPS = 5000


@dataclass
class Run:
    """Métricas de uma execução. `comparisons` segue a unidade de cada algoritmo."""

    trace: bool = False
    comparisons: int = 0
    moves: int = 0
    calls: int = 0
    max_depth: int = 0
    steps: list = field(default_factory=list)
    truncated: bool = False

    def enter(self, depth):
        self.calls += 1
        self.max_depth = max(self.max_depth, depth)

    def step(self, kind, line, text, **data):
        """Registra uma etapa; acima de MAX_STEPS marca a trilha como truncada."""
        if not self.trace:
            return
        if len(self.steps) >= MAX_STEPS:
            self.truncated = True
            return
        self.steps.append({"kind": kind, "line": line, "text": text, **data})

    def metrics(self):
        return {"comparisons": self.comparisons, "moves": self.moves, "calls": self.calls,
                "max_depth": self.max_depth}
