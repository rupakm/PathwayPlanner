"""RelaxAction stability semantics and channel-based outcome classification."""

import numpy as np
import pytest

from pathwayplanner import Budget, Outcome, State
from pathwayplanner.actions.relax import RelaxAction
from pathwayplanner.backends import ToyBackend
from pathwayplanner.backends.base import Trajectory
from pathwayplanner.cv import EuclideanCV, PeriodicCV
from pathwayplanner.outcomes import ChannelClassifier, ThresholdClassifier

X_SPACE = EuclideanCV(lambda f: np.asarray(f, dtype=float)[:1], dim=1)


def test_relax_in_well_is_success():
    backend = ToyBackend(seed=1, kT=0.1)
    start = backend.make_state(np.array([-1.0, 0.0]))
    action = RelaxAction(space=X_SPACE, tolerance=0.3, n_steps=500, n_replicas=4)
    result = action.run(start, backend, Budget())
    assert result.outcome is Outcome.SUCCESS
    assert result.best_state is not None
    assert abs(result.best_state.features[0] + 1.0) < 0.5


def test_relax_from_saddle_is_unstable():
    backend = ToyBackend(seed=2, kT=0.1)
    start = backend.make_state(np.array([0.0, 0.0]))
    action = RelaxAction(space=X_SPACE, tolerance=0.3, n_steps=2000, n_replicas=4)
    result = action.run(start, backend, Budget())
    assert result.outcome is Outcome.UNSTABLE
    # The state still moved somewhere: successor reported for recovery.
    assert result.best_state is not None
    assert abs(result.best_state.features[0]) > 0.3


def make_traj(points):
    frames = np.array(points, dtype=float)
    return Trajectory(frames=frames, cost=float(len(frames)))


def make_state(x=0.0, y=0.0):
    p = np.array([x, y])
    return State(configuration=p, features=p)


TARGET = lambda cv: cv[0] > 0.9  # noqa: E731
UPPER = lambda cv: cv[1] > 1.0  # noqa: E731

XY_SPACE = EuclideanCV(lambda f: np.asarray(f, dtype=float)[:2], dim=2)


def classifier():
    return ChannelClassifier(
        target=TARGET,
        alternatives={"upper_channel": UPPER},
        space=XY_SPACE,
        target_point=np.array([1.0, 0.0]),
        delta=1.5,
    )


def test_channel_target_hit_is_success():
    trajs = [make_traj([[-1, 0], [0, 0.2], [1.0, 0.1]])]
    result = classifier().classify(make_state(-1.0), trajs)
    assert result.outcome is Outcome.SUCCESS
    assert result.best_state.features[0] > 0.9


def test_channel_alternative_hit_is_alternative():
    trajs = [make_traj([[-1, 0], [-0.5, 1.2], [-0.4, 1.3]])]
    result = classifier().classify(make_state(-1.0), trajs)
    assert result.outcome is Outcome.ALTERNATIVE
    assert result.metadata["channel"] == "upper_channel"


def test_channel_alternative_before_target_counts_alternative_frame_first():
    # Trajectory passes through the upper channel region before the target:
    # the first region hit decides that trajectory's classification.
    trajs = [make_traj([[-1, 0], [-0.5, 1.2], [1.0, 0.0]])]
    result = classifier().classify(make_state(-1.0), trajs)
    assert result.outcome is Outcome.ALTERNATIVE


def test_target_hit_in_any_trajectory_wins_over_alternatives():
    trajs = [
        make_traj([[-1, 0], [-0.5, 1.2]]),  # alternative
        make_traj([[-1, 0], [1.0, 0.0]]),  # target
    ]
    result = classifier().classify(make_state(-1.0), trajs)
    assert result.outcome is Outcome.SUCCESS


def test_no_region_hit_falls_back_to_progress():
    partial = [make_traj([[-1, 0], [0.0, 0.0]])]  # progress 1.0 >= 0.5 * delta
    result = classifier().classify(make_state(-1.0), partial)
    assert result.outcome is Outcome.PARTIAL

    stuck = [make_traj([[-1, 0], [-0.9, 0.0]])]
    result = classifier().classify(make_state(-1.0), stuck)
    assert result.outcome is Outcome.FAILURE


def test_periodic_progress_crosses_branch_cut():
    # Dihedral-like CV in degrees. Start at 170, target at -150: the true
    # gap is 40 degrees through the +-180 cut. A frame at -170 has made 20
    # degrees of progress; Euclidean treatment would score it as regress
    # (|-170 - (-150)| = 20 but |170 - (-150)| computed flat = 320).
    space = PeriodicCV(lambda f: np.asarray(f, dtype=float)[:1], periods=[360.0])
    clf = ThresholdClassifier(
        space=space, target_point=np.array([-150.0]), delta=20.0
    )
    start = State(configuration=np.array([170.0]), features=np.array([170.0]))
    traj = Trajectory(frames=np.array([[170.0], [-170.0]]))
    result = clf.classify(start, [traj])
    assert result.outcome is Outcome.SUCCESS
    assert result.event_scores["best_progress"] == pytest.approx(20.0)
