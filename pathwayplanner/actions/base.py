"""The molecular action interface.

An action is a stochastic search procedure for realizing a structural
event. Executing an action does not guarantee the event occurs; failure
and alternative outcomes are part of the semantics, not exceptions.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Sequence

from pathwayplanner.backends.base import Backend, Budget, Trajectory
from pathwayplanner.compiler.base import Implementation
from pathwayplanner.states import State


class Outcome(enum.Enum):
    """Outcome categories of a molecular action.

    These are first-class language semantics: a recipe branches on them.
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    ALTERNATIVE = "alternative"
    UNSTABLE = "unstable"
    BUDGET_EXCEEDED = "budget_exceeded"

    @property
    def is_terminal_failure(self) -> bool:
        """True when no useful successor state was produced."""
        return self in (Outcome.FAILURE, Outcome.UNSTABLE, Outcome.BUDGET_EXCEEDED)


@dataclass
class ActionResult:
    """Everything an action execution reports back to the planner.

    Deliberately richer than a boolean: successor states, event scores,
    and cost drive recipe branching, learning, and compositionality
    measurements.
    """

    outcome: Outcome
    successor_states: list[State]
    trajectories: list[Trajectory] = field(default_factory=list)
    event_scores: dict[str, float] = field(default_factory=dict)
    cost: float = 0.0
    implementation: Implementation | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def best_state(self) -> State | None:
        """The first successor state, or None when execution produced none."""
        return self.successor_states[0] if self.successor_states else None


class Action(ABC):
    """A high-level structural action.

    The four-method contract mirrors the design doc:
    precondition -> propose -> execute -> evaluate. `run` ties them
    together with a compiler-free default (first proposed implementation).
    """

    name: str = "action"

    @abstractmethod
    def precondition(self, state: State) -> bool:
        """Whether this action is meaningful in `state`."""

    @abstractmethod
    def propose(self, state: State) -> Sequence[Implementation]:
        """Candidate physical implementations, most preferred first."""

    @abstractmethod
    def evaluate(
        self, initial_state: State, trajectories: list[Trajectory]
    ) -> ActionResult:
        """Classify the trajectory ensemble into an ActionResult."""

    def execute(
        self,
        state: State,
        implementation: Implementation,
        backend: Backend,
        budget: Budget,
    ) -> list[Trajectory]:
        """Run the search procedure for one implementation."""
        return backend.run_bursts([state], implementation, budget)

    def run(
        self,
        state: State,
        backend: Backend,
        budget: Budget,
        implementation: Implementation | None = None,
    ) -> ActionResult:
        """Precondition-check, execute, and evaluate in one call."""
        if not self.precondition(state):
            return ActionResult(
                outcome=Outcome.FAILURE,
                successor_states=[],
                metadata={"reason": "precondition_failed", "action": self.name},
            )
        impl = implementation or self.propose(state)[0]
        trajectories = self.execute(state, impl, backend, budget)
        result = self.evaluate(state, trajectories)
        result.implementation = impl
        return result
