"""Physical compositionality measurement: delta_comp.

Compares the empirical success of a composed recipe P1;P2 against the
prediction obtained by abstracting P1's successors into classes and
integrating per-class P2 success rates. Small delta means the
abstraction preserves the information P2 needs — the central quantity
of the compositionality research question.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable, Hashable

from pathwayplanner.actions.base import Outcome
from pathwayplanner.recipes.lang import Seq, Step
from pathwayplanner.states import State

Abstraction = Callable[[State], Hashable]


@dataclass
class DeltaCompResult:
    actual: float
    predicted: float
    class_rates: dict[Hashable, float]
    class_weights: dict[Hashable, float]

    @property
    def delta(self) -> float:
        return abs(self.actual - self.predicted)


def delta_comp(
    p1: Step,
    p2: Step,
    state: State,
    n_runs: int,
    n_per_class: int,
    abstraction: Abstraction,
) -> DeltaCompResult:
    """Measure |P(C | A, P1;P2) - sum_k w_k * P(C | class k, P2)|.

    Empirical side: run the composed Seq([p1, p2]) n_runs times.
    Predicted side: run p1 n_runs times, group successors by
    `abstraction`, estimate P2's success rate from one representative per
    class (n_per_class runs), and integrate over the class weights. P1
    executions with no successor carry weight as guaranteed failures.
    """
    composed = Seq([p1, p2])
    actual_successes = sum(
        1 for _ in range(n_runs) if composed(state).outcome is Outcome.SUCCESS
    )
    actual = actual_successes / n_runs

    class_counts: Counter = Counter()
    representatives: dict[Hashable, State] = {}
    failures = 0
    for _ in range(n_runs):
        result = p1(state)
        successor = result.best_state
        if result.outcome.is_terminal_failure or successor is None:
            failures += 1
            continue
        key = abstraction(successor)
        class_counts[key] += 1
        representatives.setdefault(key, successor)

    class_rates: dict[Hashable, float] = {}
    for key, representative in representatives.items():
        successes = sum(
            1
            for _ in range(n_per_class)
            if p2(representative).outcome is Outcome.SUCCESS
        )
        class_rates[key] = successes / n_per_class

    class_weights = {key: count / n_runs for key, count in class_counts.items()}
    predicted = sum(class_weights[key] * class_rates[key] for key in class_rates)

    return DeltaCompResult(
        actual=actual,
        predicted=predicted,
        class_rates=class_rates,
        class_weights=class_weights,
    )
