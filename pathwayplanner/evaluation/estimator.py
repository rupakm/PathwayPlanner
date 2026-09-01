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

    def js_pvalue(
        self, other: "OutcomeModel", n_resamples: int = 5000, seed: int = 0
    ) -> float:
        """How surprising this pair's divergence is if both came from one
        distribution.

        An absolute threshold on JS divergence is not interpretable: with
        30 executions per batch, two batches drawn from the *same*
        distribution already have a median divergence near 0.02 and a 90th
        percentile near 0.06, so a gate of 0.1 passes almost anything. This
        pools the two batches, resamples pairs of the same sizes from the
        pooled distribution, and returns the fraction whose divergence
        equals or exceeds the observed one. Large means reproducible;
        small means the two batches disagree more than sampling explains.
        """
        rng = np.random.default_rng(seed)
        outcomes = list(self.counts.elements()) + list(other.counts.elements())
        n_a, n_b = self.n, other.n
        if not outcomes or n_a == 0 or n_b == 0:
            return 1.0
        observed = self.js_divergence(other)
        indices = np.arange(len(outcomes))
        exceed = 0
        for _ in range(n_resamples):
            draw = rng.choice(indices, size=n_a + n_b, replace=True)
            a = OutcomeModel(counts=Counter(outcomes[i] for i in draw[:n_a]))
            b = OutcomeModel(counts=Counter(outcomes[i] for i in draw[n_a:]))
            exceed += a.js_divergence(b) >= observed - 1e-12
        return exceed / n_resamples

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
