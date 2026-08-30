"""HingeOpeningAction: event semantics for a hinge-angle opening.

Exercised without any MD engine by handing the action synthetic
trajectories, so the outcome semantics are tested independently of the
backend that would produce them.
"""

import numpy as np
import pytest

from pathwayplanner import Budget, Outcome, State
from pathwayplanner.actions.hinge import HingeOpeningAction
from pathwayplanner.backends.base import Trajectory
from pathwayplanner.cv import PeriodicCV

# A synthetic "angle" CV: the first component of the frame, in degrees.
ANGLE = PeriodicCV(lambda f: np.asarray(f, dtype=float)[:1], periods=[360.0])


def state_at(angle: float) -> State:
    frame = np.array([angle, 0.0])
    return State(configuration=frame, features=frame)


def trajectory_through(*angles: float) -> Trajectory:
    return Trajectory(
        frames=np.array([[a, 0.0] for a in angles], dtype=float),
        cost=float(len(angles)),
    )


def action(delta: float = 25.0, **kwargs) -> HingeOpeningAction:
    return HingeOpeningAction(
        name="open_hinge_test", space=ANGLE, delta=delta, bias="BIAS", **kwargs
    )


def test_success_when_the_angle_advances_by_delta():
    result = action().evaluate(state_at(110.0), [trajectory_through(110.0, 128.0, 137.0)])
    assert result.outcome is Outcome.SUCCESS
    assert result.event_scores["best_progress"] == pytest.approx(27.0)
    # The successor is the frame that achieved the opening, not the last one.
    assert result.best_state.features[0] == pytest.approx(137.0)


def test_partial_when_the_angle_advances_but_not_enough():
    result = action().evaluate(state_at(110.0), [trajectory_through(110.0, 124.0)])
    assert result.outcome is Outcome.PARTIAL
    assert result.event_scores["best_progress"] == pytest.approx(14.0)


def test_failure_when_the_hinge_does_not_open():
    result = action().evaluate(state_at(110.0), [trajectory_through(110.0, 108.0, 111.0)])
    assert result.outcome is Outcome.FAILURE
    assert result.successor_states == []


def test_closing_scores_negative_progress_and_never_succeeds():
    """A hinge that only closes must score below zero, not merely below delta.

    The trajectory starts one stride into the dynamics, as real bursts do
    (the burst API's first saved frame is at step `stride`), so no frame
    sits at the starting angle to floor the score at zero.
    """
    result = action().evaluate(state_at(110.0), [trajectory_through(108.0, 80.0)])
    assert result.outcome is Outcome.FAILURE
    assert result.event_scores["best_progress"] == pytest.approx(-2.0)


def test_best_replica_decides_the_ensemble_outcome():
    trajectories = [
        trajectory_through(110.0, 112.0),  # stalls
        trajectory_through(110.0, 140.0),  # opens
    ]
    result = action().evaluate(state_at(110.0), trajectories)
    assert result.outcome is Outcome.SUCCESS
    assert len(result.successor_states) == 1


def test_precondition_rejects_an_already_open_hinge():
    act = action(open_above=145.0)
    assert act.precondition(state_at(110.0))
    assert not act.precondition(state_at(150.0))


def test_precondition_admits_everything_when_no_ceiling_is_given():
    assert action().precondition(state_at(179.0))


def test_proposed_implementation_carries_the_bias_and_budget():
    act = action(n_steps=5000, n_replicas=6)
    [implementation] = act.propose(state_at(110.0))
    assert implementation.bias == "BIAS"
    assert implementation.n_steps == 5000
    assert implementation.n_replicas == 6
    assert implementation.cv is ANGLE


def test_unbiased_variant_proposes_no_bias():
    act = HingeOpeningAction(
        name="open_hinge_null", space=ANGLE, delta=25.0, bias=None
    )
    [implementation] = act.propose(state_at(110.0))
    assert implementation.bias is None


def test_run_is_semantic_on_a_failed_precondition():
    act = action(open_above=100.0)
    result = act.run(state_at(150.0), backend=None, budget=Budget())
    assert result.outcome is Outcome.FAILURE
    assert result.metadata["reason"] == "precondition_failed"


def test_progress_is_measured_from_the_start_state_not_the_first_frame():
    """Bursts restart from a saved frame, so the first trajectory frame is
    already one stride into the dynamics; progress must be relative to the
    state the action was invoked on."""
    result = action(delta=10.0).evaluate(
        state_at(110.0), [trajectory_through(118.0, 121.0)]
    )
    assert result.event_scores["best_progress"] == pytest.approx(11.0)
