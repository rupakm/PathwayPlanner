"""Hinge opening as a structural action.

`open_hinge(H, delta)` from the design document: the event is an advance
of the hinge's angular coordinate by at least `delta`, and the action is
a stochastic search for trajectories realizing it.

Progress is the *signed* advance of the angle from the state the action
was invoked on. That is obtained from the existing ThresholdClassifier
without a bespoke scoring rule, by placing its target at the angular
ceiling (180 degrees for a bond angle): with target C, progress reduces
to d(start, C) - d(x, C) = (C - start) - (C - x) = x - start for every
angle at or below the ceiling. A hinge that closes therefore scores
negative progress and can never be mistaken for a partial opening.

The action is protein-agnostic. The hinge coordinate arrives as a
CVSpace and the intervention as an opaque `bias` object, which the
backend interprets -- a trails_md BiasSpec for the biased-burst family,
or None for unbiased bursts. Nothing here imports a simulation package.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from pathwayplanner.actions.base import Action, ActionResult
from pathwayplanner.backends.base import Trajectory
from pathwayplanner.compiler.base import Implementation
from pathwayplanner.cv import CVSpace
from pathwayplanner.outcomes import ThresholdClassifier
from pathwayplanner.states import State

ANGULAR_CEILING_DEG = 180.0


class HingeOpeningAction(Action):
    """Search for trajectories that open a hinge by at least `delta` degrees.

    Attributes:
        name: Action name, e.g. "open_hinge_LID".
        space: One-dimensional CVSpace giving the hinge angle in degrees.
        delta: Required advance in degrees. It should exceed the angle's
            thermal fluctuation, or ordinary breathing will register as
            an opening.
        bias: Intervention passed through to the backend; None means the
            unbiased implementation family.
        open_above: Optional angle at or beyond which the hinge already
            counts as open, making the action inapplicable.
        ceiling: Angular ceiling used to turn distance-to-target into
            signed advance; 180 degrees for a bond angle.
    """

    def __init__(
        self,
        name: str,
        space: CVSpace,
        delta: float,
        bias: Any = None,
        n_steps: int = 5000,
        n_replicas: int = 4,
        open_above: float | None = None,
        partial_fraction: float = 0.5,
        ceiling: float = ANGULAR_CEILING_DEG,
    ):
        self.name = name
        self.space = space
        self.delta = delta
        self.bias = bias
        self.n_steps = n_steps
        self.n_replicas = n_replicas
        self.open_above = open_above
        self.ceiling = ceiling
        self.classifier = ThresholdClassifier(
            space=space,
            target_point=np.array([ceiling]),
            delta=delta,
            partial_fraction=partial_fraction,
        )

    def precondition(self, state: State) -> bool:
        """False once the hinge is already open, if a ceiling was given."""
        if self.open_above is None:
            return True
        return float(self.space.project(state.features)[0]) < self.open_above

    def propose(self, state: State) -> Sequence[Implementation]:
        return [
            Implementation(
                cv=self.space,
                bias=self.bias,
                n_steps=self.n_steps,
                n_replicas=self.n_replicas,
                policy="best_advance",
            )
        ]

    def evaluate(
        self, initial_state: State, trajectories: list[Trajectory]
    ) -> ActionResult:
        result = self.classifier.classify(initial_state, trajectories)
        result.metadata.setdefault("action", self.name)
        result.event_scores.setdefault("delta_required", self.delta)
        return result
