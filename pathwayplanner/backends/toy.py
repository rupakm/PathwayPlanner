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


def double_well_gradient(x: np.ndarray) -> np.ndarray:
    """Gradient of V(x, y) = (x^2 - 1)^2 + y^2: wells at (-1, 0), (1, 0)."""
    return np.array([4.0 * x[0] * (x[0] ** 2 - 1.0), 2.0 * x[1]])


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
