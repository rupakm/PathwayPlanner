"""Recipe combinators: sequencing, outcome-branching, retry, repetition.

A Step maps a State to an ActionResult. Combinators compose Steps into
Steps, so recipes nest arbitrarily. Composition is outcome-aware by
construction: Cond branches on the Outcome of its guard step, and Seq
threads the best successor state (stopping early on terminal failure).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol, runtime_checkable

from pathwayplanner.actions.base import ActionResult, Outcome
from pathwayplanner.states import State


@runtime_checkable
class Step(Protocol):
    def __call__(self, state: State) -> ActionResult:
        ...


@dataclass
class Seq:
    """Run steps in order, threading each best successor state forward.

    Stops at the first terminal failure; the composite result carries the
    last step's outcome and the accumulated cost.
    """

    steps: list[Step]

    def __call__(self, state: State) -> ActionResult:
        current = state
        total_cost = 0.0
        result = ActionResult(outcome=Outcome.SUCCESS, successor_states=[state])
        for step in self.steps:
            result = step(current)
            total_cost += result.cost
            if result.outcome.is_terminal_failure or result.best_state is None:
                break
            current = result.best_state
        result.cost = total_cost
        return result


@dataclass
class Cond:
    """Branch on the outcome of a guard step.

    `branches` maps Outcome to a continuation Step run from the guard's
    best successor (or the original state when the guard produced none).
    Unmapped outcomes return the guard result unchanged.
    """

    guard: Step
    branches: Mapping[Outcome, Step]

    def __call__(self, state: State) -> ActionResult:
        guard_result = self.guard(state)
        branch = self.branches.get(guard_result.outcome)
        if branch is None:
            return guard_result
        continue_from = guard_result.best_state or state
        result = branch(continue_from)
        result.cost += guard_result.cost
        return result


@dataclass
class Retry:
    """Re-run a step until success or `max_attempts` is exhausted."""

    step: Step
    max_attempts: int = 3

    def __call__(self, state: State) -> ActionResult:
        result = ActionResult(outcome=Outcome.FAILURE, successor_states=[])
        total_cost = 0.0
        for _ in range(self.max_attempts):
            result = self.step(state)
            total_cost += result.cost
            if result.outcome is Outcome.SUCCESS:
                break
        result.cost = total_cost
        return result


@dataclass
class Repeat:
    """Run a step `n` times, threading successor states, keeping the last result."""

    step: Step
    n: int

    def __call__(self, state: State) -> ActionResult:
        return Seq([self.step] * self.n)(state)


@dataclass
class Lift:
    """Wrap a plain function (e.g. a bound Action.run) as a named Step."""

    fn: Callable[[State], ActionResult]
    name: str = "step"
    metadata: dict = field(default_factory=dict)

    def __call__(self, state: State) -> ActionResult:
        return self.fn(state)
