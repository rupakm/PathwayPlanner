"""Toy potential/gradient consistency and landscape structure."""

import numpy as np
import pytest

from pathwayplanner.backends.toy import (
    double_well_gradient,
    double_well_potential,
    three_hole_gradient,
    three_hole_potential,
    wolfe_quapp_gradient,
    wolfe_quapp_potential,
)

PAIRS = [
    (double_well_potential, double_well_gradient),
    (wolfe_quapp_potential, wolfe_quapp_gradient),
    (three_hole_potential, three_hole_gradient),
]


@pytest.mark.parametrize("potential,gradient", PAIRS)
def test_gradient_matches_finite_difference(potential, gradient):
    rng = np.random.default_rng(0)
    h = 1e-6
    for _ in range(20):
        x = rng.uniform(-2.0, 2.0, size=2)
        grad = gradient(x)
        for i in range(2):
            e = np.zeros(2)
            e[i] = h
            fd = (potential(x + e) - potential(x - e)) / (2 * h)
            assert grad[i] == pytest.approx(fd, abs=1e-4)


@pytest.mark.parametrize(
    "gradient,start",
    [
        (double_well_gradient, np.array([-1.0, 0.0])),
        (double_well_gradient, np.array([1.0, 0.0])),
        (wolfe_quapp_gradient, np.array([-1.17, 1.48])),
        (wolfe_quapp_gradient, np.array([1.12, -1.49])),
        (three_hole_gradient, np.array([-1.0, 0.0])),
        (three_hole_gradient, np.array([1.0, 0.0])),
    ],
)
def test_gradient_descent_converges_near_known_minimum(gradient, start):
    x = start.copy()
    for _ in range(5000):
        x = x - 1e-3 * gradient(x)
    assert np.linalg.norm(gradient(x)) < 1e-3
    assert np.linalg.norm(x - start) < 0.5
