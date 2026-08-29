"""The relax action: first-class in the language.

Runs unbiased dynamics and reports whether the current state persists.
Distinguishes bias-induced displacement from entry into a physically
stable region: SUCCESS when the progress coordinate stays put for a
majority of replicas, UNSTABLE otherwise (with the drifted state
reported so recipes can recover).
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from pathwayplanner.actions.base import Action, ActionResult, Outcome
from pathwayplanner.actions.registry import register
from pathwayplanner.backends.base import Trajectory
from pathwayplanner.compiler.base import Implementation
from pathwayplanner.cv import CVSpace
from pathwayplanner.states import State


@register("relax")
class RelaxAction(Action):
    """Unbiased bursts; stable when the CV-space distance travelled stays
    within tolerance (periodicity handled by the CVSpace metric)."""

    name = "relax"

    def __init__(
        self,
        space: CVSpace,
        tolerance: float,
        n_steps: int = 500,
        n_replicas: int = 4,
    ):
        self.space = space
        self.tolerance = tolerance
        self.n_steps = n_steps
        self.n_replicas = n_replicas

    def precondition(self, state: State) -> bool:
        return True

    def propose(self, state: State) -> Sequence[Implementation]:
        return [
            Implementation(
                cv=self.space,
                bias=None,
                n_steps=self.n_steps,
                n_replicas=self.n_replicas,
            )
        ]

    def evaluate(
        self, initial_state: State, trajectories: list[Trajectory]
    ) -> ActionResult:
        cv_start = self.space.project(np.asarray(initial_state.features, dtype=float))
        drifts: list[tuple[float, State]] = []
        total_cost = 0.0
        for trajectory in trajectories:
            total_cost += trajectory.cost
            final = trajectory.frames[-1]
            configuration = (
                trajectory.configurations[-1]
                if trajectory.configurations is not None
                else final
            )
            drift = self.space.distance(cv_start, self.space.project(final))
            drifts.append((drift, State(configuration=configuration, features=np.asarray(final))))
        drifts.sort(key=lambda pair: pair[0])
        n_stable = sum(1 for drift, _ in drifts if drift <= self.tolerance)
        stable = n_stable > len(drifts) / 2

        if stable:
            outcome = Outcome.SUCCESS
            successors = [s for d, s in drifts if d <= self.tolerance]
        else:
            outcome = Outcome.UNSTABLE
            # Report the most-drifted state: where the system actually went.
            successors = [drifts[-1][1]]

        return ActionResult(
            outcome=outcome,
            successor_states=successors,
            trajectories=trajectories,
            event_scores={
                "median_drift": float(np.median([d for d, _ in drifts])),
                "stable_fraction": n_stable / max(len(drifts), 1),
            },
            cost=total_cost,
        )
