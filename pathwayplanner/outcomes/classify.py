"""Trajectory -> Outcome classification.

Classifiers turn a burst ensemble into the ActionResult an action
reports. All CV geometry (projection, periodicity, distances) comes
from the CVSpace on the classifier; classifiers never compute
differences of CV components themselves.

Progress is defined relative to a target point in CV space:
progress(x) = d(cv_start, target) - d(cv_x, target), which is
well-defined in any dimension and under periodicity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol, runtime_checkable

import numpy as np

from pathwayplanner.actions.base import ActionResult, Outcome
from pathwayplanner.backends.base import Trajectory
from pathwayplanner.cv import CVSpace
from pathwayplanner.states import State


@runtime_checkable
class OutcomeClassifier(Protocol):
    def classify(
        self, initial_state: State, trajectories: list[Trajectory]
    ) -> ActionResult:
        ...


@dataclass
class ThresholdClassifier(OutcomeClassifier):
    """Success when progress toward `target_point` reaches delta; partial
    above `partial_fraction * delta`; failure otherwise.

    Successor states are the best frame of each qualifying trajectory,
    ranked by progress.
    """

    space: CVSpace
    target_point: np.ndarray
    delta: float
    partial_fraction: float = 0.5

    def _progress(self, cv_start: np.ndarray, cv: np.ndarray) -> float:
        target = np.asarray(self.target_point, dtype=float)
        return self.space.distance(cv_start, target) - self.space.distance(cv, target)

    def classify(
        self, initial_state: State, trajectories: list[Trajectory]
    ) -> ActionResult:
        cv_start = self.space.project(np.asarray(initial_state.features, dtype=float))
        candidates: list[tuple[float, State]] = []
        total_cost = 0.0
        for trajectory in trajectories:
            total_cost += trajectory.cost
            progresses = np.array(
                [self._progress(cv_start, self.space.project(f)) for f in trajectory.frames]
            )
            best_idx = int(np.argmax(progresses))
            frame = trajectory.frames[best_idx]
            configuration = (
                trajectory.configurations[best_idx]
                if trajectory.configurations is not None
                else frame
            )
            candidates.append(
                (
                    float(progresses[best_idx]),
                    State(configuration=configuration, features=np.asarray(frame)),
                )
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


@dataclass
class ChannelClassifier(OutcomeClassifier):
    """Region-based classification with alternative-transition detection.

    Region predicates operate on CV vectors (`space.project` of each
    frame). Walks each trajectory frame by frame; the first region hit
    (target or a named alternative) classifies that trajectory. Ensemble
    verdict: SUCCESS when any trajectory reached the target, else
    ALTERNATIVE when any reached an alternative region (channel name in
    metadata), else the ThresholdClassifier progress fallback toward
    `target_point` (PARTIAL / FAILURE).
    """

    target: Callable[[np.ndarray], bool]
    alternatives: dict[str, Callable[[np.ndarray], bool]]
    space: CVSpace
    target_point: np.ndarray = field(default=None)  # type: ignore[assignment]
    delta: float = 0.0
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
            space=self.space,
            target_point=self.target_point,
            delta=self.delta,
            partial_fraction=self.partial_fraction,
        ).classify(initial_state, trajectories)
        # Region semantics own SUCCESS; progress alone can at most be PARTIAL.
        if fallback.outcome is Outcome.SUCCESS:
            fallback.outcome = Outcome.PARTIAL
        return fallback

    def _first_hit(self, trajectory: Trajectory) -> tuple[str, int] | None:
        for index, frame in enumerate(trajectory.frames):
            cv = self.space.project(frame)
            if self.target(cv):
                return ("target", index)
            for name, predicate in self.alternatives.items():
                if predicate(cv):
                    return (name, index)
        return None


@dataclass
class Criterion:
    """One coordinate an event requires progress in.

    Progress is signed movement of `space` toward `target_point`, the same
    construction ThresholdClassifier uses: with target L, progress is
    d(start, L) - d(x, L), so it is positive only for motion in the
    intended direction.
    """

    space: CVSpace
    target_point: np.ndarray
    delta: float


@dataclass
class ConjunctiveClassifier(OutcomeClassifier):
    """An event that several coordinates must satisfy at once.

    A single-coordinate event can be met by configurations that are not the
    intended state: pulling adenylate kinase's LID-CORE distance drove
    theta_LID past the closed crystal value while the structure remained
    about 5 A from the closed conformation, so the angle reported an event
    the structure had not reached.

    The score of a frame is the *worst* component's relative progress,
    min_i(progress_i / delta_i), so one lagging coordinate governs the
    verdict and no amount of overshoot elsewhere compensates. The event is
    met when a single frame scores 1.0 or more -- criteria must be
    satisfied together, not accumulated across different frames, which is
    what makes this a conjunction rather than a checklist.

    With one criterion it reduces exactly to ThresholdClassifier.
    """

    criteria: list[Criterion]
    partial_fraction: float = 0.5

    def _frame_score(self, starts: list[np.ndarray], frame: np.ndarray) -> float:
        scores = []
        for criterion, start_cv in zip(self.criteria, starts):
            target = np.asarray(criterion.target_point, dtype=float)
            cv = criterion.space.project(frame)
            progress = criterion.space.distance(
                start_cv, target
            ) - criterion.space.distance(cv, target)
            scores.append(progress / criterion.delta)
        return min(scores)

    def classify(
        self, initial_state: State, trajectories: list[Trajectory]
    ) -> ActionResult:
        features = np.asarray(initial_state.features, dtype=float)
        starts = [c.space.project(features) for c in self.criteria]

        candidates: list[tuple[float, State]] = []
        total_cost = 0.0
        for trajectory in trajectories:
            total_cost += trajectory.cost
            scores = np.array(
                [self._frame_score(starts, frame) for frame in trajectory.frames]
            )
            best_idx = int(np.argmax(scores))
            frame = trajectory.frames[best_idx]
            configuration = (
                trajectory.configurations[best_idx]
                if trajectory.configurations is not None
                else frame
            )
            candidates.append(
                (
                    float(scores[best_idx]),
                    State(configuration=configuration, features=np.asarray(frame)),
                )
            )
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        best = candidates[0][0] if candidates else 0.0

        if best >= 1.0:
            outcome = Outcome.SUCCESS
            keep = [s for score, s in candidates if score >= 1.0]
        elif best >= self.partial_fraction:
            outcome = Outcome.PARTIAL
            keep = [candidates[0][1]]
        else:
            outcome = Outcome.FAILURE
            keep = []

        return ActionResult(
            outcome=outcome,
            successor_states=keep,
            trajectories=trajectories,
            event_scores={
                "worst_component": best,
                "n_criteria": float(len(self.criteria)),
            },
            cost=total_cost,
        )
