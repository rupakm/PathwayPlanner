"""Hinge motion as a structural action.

`open_hinge(H, delta)` and `close_hinge(H, delta)` from the design
document: the event is a movement of the hinge's angular coordinate by
at least `delta` in the named direction, and the action is a stochastic
search for trajectories realizing it.

Progress is the *signed* movement of the angle from the state the action
was invoked on, in the action's own direction. That is obtained from the
existing ThresholdClassifier without a bespoke scoring rule, by placing
its target at the angular limit the motion heads toward: with target L,
progress reduces to d(start, L) - d(x, L), which is x - start when
L = 180 (opening) and start - x when L = 0 (closing). Motion the wrong
way therefore scores negative and can never be mistaken for partial
progress, in either direction.

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
from pathwayplanner.outcomes import (
    ConjunctiveClassifier,
    Criterion,
    ThresholdClassifier,
)
from pathwayplanner.states import State

ANGULAR_CEILING_DEG = 180.0


class _HingeAction(Action):
    """Shared machinery for hinge motion in one direction.

    Subclasses fix `limit`, the angular extreme the motion heads toward,
    and `sense`, +1 when the angle should increase and -1 when it should
    decrease.

    Attributes:
        name: Action name, e.g. "open_hinge_LID".
        space: One-dimensional CVSpace giving the hinge angle in degrees.
        delta: Required movement in degrees. It should exceed the angle's
            thermal fluctuation, or ordinary breathing will register as
            the event.
        bias: Intervention passed through to the backend; None means the
            unbiased implementation family.
        stop_at: Optional angle beyond which the motion is already
            complete, making the action inapplicable.
        also: Further coordinates the event requires progress in. An angle
            alone can be satisfied by a configuration that is not the
            intended state -- pulling adenylate kinase's LID-CORE distance
            drove theta_LID past the closed crystal value while the
            structure stayed about 5 A from the closed conformation -- so a
            structural criterion such as RMSD to the target endpoint can be
            conjoined here. With none given the action behaves exactly as
            the single-coordinate version.
    """

    limit: float = ANGULAR_CEILING_DEG
    sense: int = 1

    def __init__(
        self,
        name: str,
        space: CVSpace,
        delta: float,
        bias: Any = None,
        n_steps: int = 5000,
        n_replicas: int = 4,
        stop_at: float | None = None,
        partial_fraction: float = 0.5,
        also: list[Criterion] | None = None,
    ):
        self.name = name
        self.space = space
        self.delta = delta
        self.bias = bias
        self.n_steps = n_steps
        self.n_replicas = n_replicas
        self.stop_at = stop_at
        self.also = list(also or [])
        angle_criterion = Criterion(
            space=space, target_point=np.array([self.limit]), delta=delta
        )
        self.classifier = (
            ConjunctiveClassifier(
                criteria=[angle_criterion, *self.also],
                partial_fraction=partial_fraction,
            )
            if self.also
            else ThresholdClassifier(
                space=space,
                target_point=np.array([self.limit]),
                delta=delta,
                partial_fraction=partial_fraction,
            )
        )

    def precondition(self, state: State) -> bool:
        """False once the hinge has already passed `stop_at`, if given."""
        if self.stop_at is None:
            return True
        angle = float(self.space.project(state.features)[0])
        return self.sense * (angle - self.stop_at) < 0

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


class HingeOpeningAction(_HingeAction):
    """Search for trajectories that open a hinge by at least `delta` degrees."""

    limit = ANGULAR_CEILING_DEG
    sense = 1


class HingeClosingAction(_HingeAction):
    """Search for trajectories that close a hinge by at least `delta` degrees.

    The uphill direction for an apo enzyme whose equilibrium is open, and
    therefore a sharper test of an implementation than opening: a closing
    that succeeds cannot be spontaneous relaxation.
    """

    limit = 0.0
    sense = -1
