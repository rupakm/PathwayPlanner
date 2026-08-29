"""Backend protocol: the only seam between the language and MD engines.

Nothing outside `pathwayplanner.backends` may import trails_md or
pathgennie. A backend turns (start states, implementation, budget) into
trajectories; everything above this line is simulator-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence, runtime_checkable

import numpy as np

from pathwayplanner.states import State

# Frame convention: Trajectory.frames and State.features hold configuration
# features in the backend's native form (a 2D point for the toy backend,
# an (n_atoms, 3) Angstrom array for MD backends). CV vectors exist only
# transiently, produced by a CVSpace.project at the point of use.


@dataclass
class Trajectory:
    """One burst: per-frame configuration features plus opaque
    configuration handles for restarting."""

    frames: np.ndarray
    configurations: Sequence[Any] | None = None
    cost: float = 0.0

    def __len__(self) -> int:
        return len(self.frames)


@dataclass
class Budget:
    """Resource cap for one action execution."""

    max_steps: int = 100_000
    wall_seconds: float | None = None


@runtime_checkable
class Backend(Protocol):
    """Runs an implementation's burst ensemble from given start states."""

    def run_bursts(
        self,
        start_states: Sequence[State],
        implementation: "Implementation",  # noqa: F821
        budget: Budget,
    ) -> list[Trajectory]:
        ...

    def make_state(self, configuration: Any) -> State:
        """Wrap a backend configuration into a planner State."""
        ...
