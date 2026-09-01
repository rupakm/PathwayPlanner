"""Relaxation direction: a signed measurement, not a pass/fail verdict.

Persistence was reported as a threshold on how far a coordinate drifted
after the restraint was removed. That measure has no defensible setting:
at 2.5 sigma of the coordinate's own fluctuation almost everything passes,
at 1 sigma almost everything fails, and neither says which way the system
went. It is also the wrong question for a configuration on a slope rather
than in a basin -- such a structure always relaxes; what matters is the
direction.

`relaxation_direction` reports the signed change in a progress coordinate
over an unbiased window, with its spread and the fraction advancing. No
threshold, and no claim about stability.
"""

import numpy as np
import pytest

from pathwayplanner import State
from pathwayplanner.backends.base import Trajectory
from pathwayplanner.cv import EuclideanCV
from pathwayplanner.evaluation import relaxation_direction

# Progress coordinate: larger means nearer the product state.
S = EuclideanCV(lambda f: np.asarray(f, dtype=float)[:1], dim=1)


def traj(*values):
    return Trajectory(frames=np.array([[v] for v in values], dtype=float), cost=1.0)


def test_retreat_is_negative():
    r = relaxation_direction(S, [traj(1.3, 0.4, -0.5)])
    assert r.mean_change == pytest.approx(-1.8)
    assert r.fraction_advancing == 0.0


def test_advance_is_positive():
    r = relaxation_direction(S, [traj(1.0, 2.0, 3.0)])
    assert r.mean_change == pytest.approx(2.0)
    assert r.fraction_advancing == 1.0


def test_change_is_measured_from_the_first_frame_of_each_trajectory():
    """Each trajectory supplies its own baseline, so successors released
    from different points are comparable."""
    r = relaxation_direction(S, [traj(5.0, 4.0), traj(1.0, 0.0)])
    assert r.mean_change == pytest.approx(-1.0)


def test_spread_is_reported_so_a_mean_is_never_read_alone():
    r = relaxation_direction(S, [traj(0.0, 2.0), traj(0.0, -2.0)])
    assert r.mean_change == pytest.approx(0.0)
    assert r.sd_change == pytest.approx(2.0)
    assert r.fraction_advancing == 0.5


def test_endpoints_are_reported_not_only_the_change():
    r = relaxation_direction(S, [traj(1.27, -0.48)])
    assert r.mean_start == pytest.approx(1.27)
    assert r.mean_end == pytest.approx(-0.48)


def test_no_trajectories_is_not_an_error():
    r = relaxation_direction(S, [])
    assert r.n == 0
    assert np.isnan(r.mean_change)
