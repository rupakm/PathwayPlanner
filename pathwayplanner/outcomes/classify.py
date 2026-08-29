"""Trajectory -> Outcome classification.

Classifiers turn a burst ensemble into the ActionResult an action
reports. ThresholdClassifier covers the common scalar-event case:
success when a progress coordinate advances by at least `delta`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

import numpy as np

from pathwayplanner.actions.base import ActionResult, Outcome
from pathwayplanner.backends.base import Trajectory
from pathwayplanner.states import State


@runtime_checkable
class OutcomeClassifier(Protocol):
    def classify(
        self, initial_state: State, trajectories: list[Trajectory]
    ) -> ActionResult:
        ...


@dataclass
class ThresholdClassifier(OutcomeClassifier):
    """Success when max progress along `cv` reaches delta; partial above
    `partial_fraction * delta`; failure otherwise.

    Successor states are the best frame of each qualifying trajectory,
    ranked by progress.
    """

    cv: Callable[[np.ndarray], float]
    delta: float
    partial_fraction: float = 0.5

    def classify(
        self, initial_state: State, trajectories: list[Trajectory]
    ) -> ActionResult:
        start_value = self.cv(np.asarray(initial_state.features, dtype=float))
        candidates: list[tuple[float, State]] = []
        total_cost = 0.0
        for trajectory in trajectories:
            total_cost += trajectory.cost
            values = np.array([self.cv(frame) for frame in trajectory.frames])
            best_idx = int(np.argmax(values))
            progress = float(values[best_idx] - start_value)
            frame = trajectory.frames[best_idx]
            configuration = (
                trajectory.configurations[best_idx]
                if trajectory.configurations is not None
                else frame
            )
            candidates.append(
                (progress, State(configuration=configuration, features=np.asarray(frame)))
            )
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        best_progress = candidates[0][0] if candidates else 0.0

        if best_progress >= self.delta:
            outcome = Outcome.SUCCESS
            keep = [s for p, s in candidates if p >= self.delta]
        elif best_progress >= self.partial_fraction * self.delta:
            outcome = Outcome.PARTIAL
            keep = [candidates[0][1]]
        else:
            outcome = Outcome.FAILURE
            keep = []

        return ActionResult(
            outcome=outcome,
            successor_states=keep,
            trajectories=trajectories,
            event_scores={"best_progress": best_progress, "target": self.delta},
            cost=total_cost,
        )
