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
class ChannelClassifier(OutcomeClassifier):
    """Region-based classification with alternative-transition detection.

    Walks each trajectory frame by frame; the first region hit (target or
    a named alternative) classifies that trajectory. Ensemble verdict:
    SUCCESS when any trajectory reached the target, else ALTERNATIVE when
    any reached an alternative region (channel name in metadata), else
    the ThresholdClassifier progress fallback (PARTIAL / FAILURE).
    """

    target: Callable[[np.ndarray], bool]
    alternatives: dict[str, Callable[[np.ndarray], bool]]
    cv: Callable[[np.ndarray], float]
    delta: float
    partial_fraction: float = 0.5

    def classify(
        self, initial_state: State, trajectories: list[Trajectory]
    ) -> ActionResult:
        target_hits: list[State] = []
        channel_counts: dict[str, int] = {}
        alternative_hits: list[State] = []
        total_cost = 0.0
        for trajectory in trajectories:
            total_cost += trajectory.cost
            hit = self._first_hit(trajectory)
            if hit is None:
                continue
            channel, index = hit
            frame = trajectory.frames[index]
            configuration = (
                trajectory.configurations[index]
                if trajectory.configurations is not None
                else frame
            )
            state = State(configuration=configuration, features=np.asarray(frame))
            if channel == "target":
                target_hits.append(state)
            else:
                channel_counts[channel] = channel_counts.get(channel, 0) + 1
                alternative_hits.append(state)

        if target_hits:
            return ActionResult(
                outcome=Outcome.SUCCESS,
                successor_states=target_hits,
                trajectories=trajectories,
                event_scores={"n_target_hits": float(len(target_hits))},
                cost=total_cost,
                metadata={"alternative_channels": channel_counts},
            )
        if alternative_hits:
            dominant = max(channel_counts, key=channel_counts.get)
            return ActionResult(
                outcome=Outcome.ALTERNATIVE,
                successor_states=alternative_hits,
                trajectories=trajectories,
                event_scores={"n_alternative_hits": float(len(alternative_hits))},
                cost=total_cost,
                metadata={"channel": dominant, "alternative_channels": channel_counts},
            )
        fallback = ThresholdClassifier(
            cv=self.cv, delta=self.delta, partial_fraction=self.partial_fraction
        ).classify(initial_state, trajectories)
        # Region semantics own SUCCESS; progress alone can at most be PARTIAL.
        if fallback.outcome is Outcome.SUCCESS:
            fallback.outcome = Outcome.PARTIAL
        return fallback

    def _first_hit(self, trajectory: Trajectory) -> tuple[str, int] | None:
        for index, frame in enumerate(trajectory.frames):
            if self.target(frame):
                return ("target", index)
            for name, predicate in self.alternatives.items():
                if predicate(frame):
                    return (name, index)
        return None


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
