"""Toy backend: overdamped Langevin dynamics on 2D analytic potentials.

Runs with no MD engine installed; drives the test suite and fast
semantics experiments. The "configuration" of a state is simply its 2D
point, so features and configuration coincide.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from pathwayplanner.backends.base import Backend, Budget, Trajectory
from pathwayplanner.compiler.base import Implementation
from pathwayplanner.states import State

PotentialGradient = Callable[[np.ndarray], np.ndarray]


def double_well_potential(x: np.ndarray) -> float:
    """V(x, y) = (x^2 - 1)^2 + y^2: wells at (-1, 0), (1, 0)."""
    return float((x[0] ** 2 - 1.0) ** 2 + x[1] ** 2)


def double_well_gradient(x: np.ndarray) -> np.ndarray:
    """Gradient of `double_well_potential`."""
    return np.array([4.0 * x[0] * (x[0] ** 2 - 1.0), 2.0 * x[1]])


def wolfe_quapp_potential(x: np.ndarray) -> float:
    """Wolfe-Quapp surface: two minima connected by two saddle channels.

    Same parameterization as the Trails-MD / PathGennie toy benchmarks.
    """
    return float(
        x[0] ** 4 + x[1] ** 4 - 2.0 * x[0] ** 2 - 4.0 * x[1] ** 2
        + x[0] * x[1] + 0.3 * x[0] + 0.1 * x[1]
    )


def wolfe_quapp_gradient(x: np.ndarray) -> np.ndarray:
    """Gradient of `wolfe_quapp_potential`."""
    return np.array(
        [
            4.0 * x[0] ** 3 - 4.0 * x[0] + x[1] + 0.3,
            4.0 * x[1] ** 3 - 8.0 * x[1] + x[0] + 0.1,
        ]
    )


def three_hole_potential(x: np.ndarray) -> float:
    """Metzner-style three-hole surface: wells at (+-1, 0), an upper channel
    through the shallow hole near (0, 1.5), and a direct lower channel.
    """
    g = np.exp
    return float(
        3.0 * g(-x[0] ** 2 - (x[1] - 1.0 / 3.0) ** 2)
        - 3.0 * g(-x[0] ** 2 - (x[1] - 5.0 / 3.0) ** 2)
        - 5.0 * g(-((x[0] - 1.0) ** 2) - x[1] ** 2)
        - 5.0 * g(-((x[0] + 1.0) ** 2) - x[1] ** 2)
        + 0.2 * x[0] ** 4
        + 0.2 * (x[1] - 1.0 / 3.0) ** 4
    )


def three_hole_gradient(x: np.ndarray) -> np.ndarray:
    """Gradient of `three_hole_potential`."""
    g = np.exp
    a = 3.0 * g(-x[0] ** 2 - (x[1] - 1.0 / 3.0) ** 2)
    b = -3.0 * g(-x[0] ** 2 - (x[1] - 5.0 / 3.0) ** 2)
    c = -5.0 * g(-((x[0] - 1.0) ** 2) - x[1] ** 2)
    d = -5.0 * g(-((x[0] + 1.0) ** 2) - x[1] ** 2)
    dx = (
        a * (-2.0 * x[0])
        + b * (-2.0 * x[0])
        + c * (-2.0 * (x[0] - 1.0))
        + d * (-2.0 * (x[0] + 1.0))
        + 0.8 * x[0] ** 3
    )
    dy = (
        a * (-2.0 * (x[1] - 1.0 / 3.0))
        + b * (-2.0 * (x[1] - 5.0 / 3.0))
        + c * (-2.0 * x[1])
        + d * (-2.0 * x[1])
        + 0.8 * (x[1] - 1.0 / 3.0) ** 3
    )
    return np.array([dx, dy])


@dataclass
class ToyBackend(Backend):
    """Euler–Maruyama integrator: dx = -grad V dt + bias dt + noise."""

    gradient: PotentialGradient = double_well_gradient
    dt: float = 1e-3
    kT: float = 0.3
    seed: int = 0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)

    def make_state(self, configuration: np.ndarray) -> State:
        point = np.asarray(configuration, dtype=float)
        return State(configuration=point, features=point.copy())

    def run_bursts(
        self,
        start_states: Sequence[State],
        implementation: Implementation,
        budget: Budget,
    ) -> list[Trajectory]:
        n_steps = min(implementation.n_steps, budget.max_steps)
        noise_scale = np.sqrt(2.0 * self.kT * self.dt)
        bias = implementation.bias
        trajectories: list[Trajectory] = []
        for replica in range(implementation.n_replicas):
            start = start_states[replica % len(start_states)]
            x = np.asarray(start.configuration, dtype=float).copy()
            frames = np.empty((n_steps + 1, x.size))
            frames[0] = x
            for step in range(1, n_steps + 1):
                drift = -self.gradient(x)
                if bias is not None:
                    drift = drift + bias(x)
                x = x + drift * self.dt + noise_scale * self._rng.standard_normal(x.size)
                frames[step] = x
            trajectories.append(
                Trajectory(frames=frames, configurations=list(frames), cost=float(n_steps))
            )
        return trajectories
