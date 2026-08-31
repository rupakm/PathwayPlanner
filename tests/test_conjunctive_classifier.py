"""ConjunctiveClassifier: an event that several coordinates must all satisfy.

The close_hinge probe showed why this is needed. A restraint pulling the
LID-CORE centroid distance drove theta_LID past the closed crystal value
while the structure stayed ~5 A from the closed conformation: the
one-coordinate event was satisfied by a configuration that was not the
intended state.
"""

import numpy as np
import pytest

from pathwayplanner import Outcome, State
from pathwayplanner.backends.base import Trajectory
from pathwayplanner.cv import EuclideanCV
from pathwayplanner.outcomes import ConjunctiveClassifier, Criterion

# Frame layout: [angle_deg, rmsd_A].
ANGLE = EuclideanCV(lambda f: np.asarray(f, dtype=float)[:1], dim=1)
RMSD = EuclideanCV(lambda f: np.asarray(f, dtype=float)[1:2], dim=1)


def state_at(angle, rmsd):
    frame = np.array([angle, rmsd])
    return State(configuration=frame, features=frame)


def traj(*frames):
    return Trajectory(frames=np.array(frames, dtype=float), cost=1.0)


def closing_both(angle_delta=25.0, rmsd_delta=2.0):
    """Both coordinates must fall: the angle by 25 deg, the RMSD by 2 A."""
    return ConjunctiveClassifier(
        criteria=[
            Criterion(space=ANGLE, target_point=np.array([0.0]), delta=angle_delta),
            Criterion(space=RMSD, target_point=np.array([0.0]), delta=rmsd_delta),
        ]
    )


def test_success_needs_every_criterion_in_one_frame():
    result = closing_both().classify(
        state_at(146.0, 6.2), [traj([118.0, 4.0])]
    )
    assert result.outcome is Outcome.SUCCESS
    assert result.best_state.features[0] == pytest.approx(118.0)


def test_angle_alone_is_not_success():
    """The failure mode the probe found: the hinge angle closes past target
    while the structure has barely moved toward the closed conformation."""
    result = closing_both().classify(
        state_at(146.0, 6.2), [traj([99.0, 5.9])]
    )
    assert result.outcome is not Outcome.SUCCESS
    assert result.event_scores["worst_component"] < 1.0


def test_rmsd_alone_is_not_success():
    result = closing_both().classify(
        state_at(146.0, 6.2), [traj([144.0, 3.0])]
    )
    assert result.outcome is not Outcome.SUCCESS


def test_criteria_must_be_met_by_the_same_frame_not_different_ones():
    """Two frames each satisfying one criterion do not make an event."""
    result = closing_both().classify(
        state_at(146.0, 6.2), [traj([118.0, 6.1], [145.0, 3.9])]
    )
    assert result.outcome is not Outcome.SUCCESS


def test_partial_when_every_component_is_halfway():
    result = closing_both().classify(
        state_at(146.0, 6.2), [traj([133.0, 5.1])]
    )
    assert result.outcome is Outcome.PARTIAL


def test_score_is_the_worst_component_so_one_lagging_axis_governs():
    result = closing_both().classify(
        state_at(146.0, 6.2), [traj([96.0, 5.2])]
    )
    # Angle is 200% of its target, RMSD only 50%: the score is the RMSD's.
    assert result.event_scores["worst_component"] == pytest.approx(0.5)


def test_single_criterion_reduces_to_a_threshold():
    single = ConjunctiveClassifier(
        criteria=[Criterion(space=ANGLE, target_point=np.array([0.0]), delta=25.0)]
    )
    assert single.classify(
        state_at(146.0, 6.2), [traj([118.0, 6.2])]
    ).outcome is Outcome.SUCCESS


def test_motion_the_wrong_way_scores_negative():
    result = closing_both().classify(
        state_at(146.0, 6.2), [traj([152.0, 6.9])]
    )
    assert result.outcome is Outcome.FAILURE
    assert result.event_scores["worst_component"] < 0.0
