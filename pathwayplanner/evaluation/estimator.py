"""Empirical outcome models: P(o, s' | s, step) from repeated execution."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from pathwayplanner.actions.base import Outcome
from pathwayplanner.recipes.contracts import RecipeContract
from pathwayplanner.recipes.lang import Step
from pathwayplanner.states import State


@dataclass
class OutcomeModel:
    """Outcome frequencies plus the successor states that produced them."""

    counts: Counter = field(default_factory=Counter)
    successors: list[State] = field(default_factory=list)
    total_cost: float = 0.0

    @classmethod
    def from_outcomes(cls, outcomes: list[Outcome]) -> "OutcomeModel":
        return cls(counts=Counter(outcomes))

    @property
    def n(self) -> int:
        return sum(self.counts.values())

    def probs(self) -> dict[Outcome, float]:
        n = self.n
        return {o: c / n for o, c in self.counts.items()} if n else {}

    def js_divergence(self, other: "OutcomeModel") -> float:
        """Jensen-Shannon divergence (base 2, in [0, 1]) between outcome
        distributions."""
        p, q = self.probs(), other.probs()
        support = set(p) | set(q)

        def kl(d1, d2):
            total = 0.0
            for o in support:
                a = d1.get(o, 0.0)
                if a > 0.0:
                    total += a * np.log2(a / d2[o])
            return total

        m = {o: 0.5 * (p.get(o, 0.0) + q.get(o, 0.0)) for o in support}
        return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def estimate_outcomes(
    step: Step,
    state: State,
    n: int,
    contract: RecipeContract | None = None,
) -> OutcomeModel:
    """Execute `step` from `state` n times and tabulate the results.

    Optionally folds each execution into a RecipeContract's outcome model.
    """
    model = OutcomeModel()
    for _ in range(n):
        result = step(state)
        model.counts[result.outcome] += 1
        model.total_cost += result.cost
        if result.best_state is not None:
            model.successors.append(result.best_state)
        if contract is not None:
            contract.record(result)
    return model
