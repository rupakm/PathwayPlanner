"""Recipe contracts: (Pre, Post, K, B).

A contract makes a recipe composable: which abstract labels it accepts,
which it may produce, its empirical outcome statistics, and its budget.
The outcome model K starts as observed frequencies and is refined as
executions accumulate.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from pathwayplanner.actions.base import ActionResult, Outcome
from pathwayplanner.backends.base import Budget


@dataclass
class RecipeContract:
    """Behavioral contract for a recipe.

    Attributes:
        pre: Abstract labels the recipe accepts as input states.
        post: Abstract labels the recipe may produce.
        outcome_counts: Observed outcome frequencies across executions.
        budget: Resource cap per execution.
    """

    pre: set[str] = field(default_factory=set)
    post: set[str] = field(default_factory=set)
    outcome_counts: Counter = field(default_factory=Counter)
    budget: Budget = field(default_factory=Budget)

    def record(self, result: ActionResult) -> None:
        """Fold one execution into the empirical outcome model."""
        self.outcome_counts[result.outcome] += 1

    def success_rate(self) -> float | None:
        """Empirical P(success), or None before any execution."""
        total = sum(self.outcome_counts.values())
        if total == 0:
            return None
        return self.outcome_counts[Outcome.SUCCESS] / total

    def accepts(self, labels: set[str]) -> bool:
        """Whether a state with `labels` satisfies the precondition."""
        return self.pre <= labels if self.pre else True
