"""CVSpace: projection plus metric structure, in one abstraction."""

import numpy as np
import pytest

from pathwayplanner.cv import CVSpace, EuclideanCV, PeriodicCV


def take_xy(frame):
    return np.asarray(frame, dtype=float)[:2]


def test_euclidean_project_and_distance():
    space = EuclideanCV(take_xy, dim=2)
    assert isinstance(space, CVSpace)
    a = space.project(np.array([0.0, 0.0, 9.0]))
    b = space.project(np.array([3.0, 4.0, 9.0]))
    assert a.shape == (2,)
    assert space.distance(a, b) == pytest.approx(5.0)
    np.testing.assert_allclose(space.displacement(a, b), [3.0, 4.0])


def test_periodic_distance_uses_minimum_image():
    # Dihedral-like CV in degrees: 170 and -170 are 20 degrees apart.
    space = PeriodicCV(take_xy, periods=[360.0, 360.0])
    d = space.distance(np.array([170.0, 0.0]), np.array([-170.0, 0.0]))
    assert d == pytest.approx(20.0)
    np.testing.assert_allclose(
        space.displacement(np.array([170.0, 0.0]), np.array([-170.0, 0.0])),
        [20.0, 0.0],
    )


def test_periodic_mixed_components():
    # First component periodic, second not (None).
    space = PeriodicCV(take_xy, periods=[360.0, None])
    d = space.distance(np.array([179.0, 1.0]), np.array([-179.0, -1.0]))
    assert d == pytest.approx(np.hypot(2.0, 2.0))


def test_distance_is_norm_of_displacement():
    space = PeriodicCV(take_xy, periods=[360.0, None])
    a, b = np.array([100.0, 3.0]), np.array([-150.0, -1.0])
    assert space.distance(a, b) == pytest.approx(
        float(np.linalg.norm(space.displacement(a, b)))
    )


def test_periods_attribute_exposed_for_adapters():
    space = PeriodicCV(take_xy, periods=[360.0, None])
    assert space.periods == [360.0, None]
    assert getattr(EuclideanCV(take_xy, dim=2), "periods", None) is None
