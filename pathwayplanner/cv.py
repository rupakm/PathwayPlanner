"""Collective-variable spaces: a projection together with its metric.

Distance is a property of the CV space, not of its consumers. A CVSpace
bundles the projection from configuration features to CV vectors with
the metric structure of that space, so periodic coordinates (dihedrals)
are handled once here rather than in every classifier and action. The
invariant distance(a, b) == norm(displacement(a, b)) holds for all
implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence, runtime_checkable

import numpy as np

ProjectFn = Callable[[np.ndarray], np.ndarray]


@runtime_checkable
class CVSpace(Protocol):
    """A collective-variable space: projection plus metric structure."""

    dim: int

    def project(self, frame: np.ndarray) -> np.ndarray:
        """Configuration features -> CV vector of shape (dim,)."""
        ...

    def displacement(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Minimum-image difference b - a in CV space."""
        ...

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Metric on CV vectors; equals the norm of the displacement."""
        ...


@dataclass
class EuclideanCV:
    """Flat CV space with the Euclidean metric."""

    project_fn: ProjectFn
    dim: int

    def project(self, frame: np.ndarray) -> np.ndarray:
        return np.atleast_1d(np.asarray(self.project_fn(frame), dtype=float))

    def displacement(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.asarray(b, dtype=float) - np.asarray(a, dtype=float)

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.linalg.norm(self.displacement(a, b)))


@dataclass
class PeriodicCV:
    """CV space with per-component periodicity (e.g. dihedral angles).

    `periods[i]` is the period of component i (360.0 for degrees, 2*pi
    for radians) or None/0 for a non-periodic component. Same convention
    as PathGennie's `periodic_delta`, so adapters can pass `periods`
    through directly.
    """

    project_fn: ProjectFn
    periods: Sequence[float | None]

    def __post_init__(self) -> None:
        self.dim = len(self.periods)

    def project(self, frame: np.ndarray) -> np.ndarray:
        return np.atleast_1d(np.asarray(self.project_fn(frame), dtype=float))

    def displacement(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        delta = np.asarray(b, dtype=float) - np.asarray(a, dtype=float)
        if delta.size != len(self.periods):
            raise ValueError(
                f"CV has {delta.size} components but {len(self.periods)} periods given"
            )
        out = delta.copy()
        for i, period in enumerate(self.periods):
            if period:
                p = float(period)
                out[i] = (out[i] + 0.5 * p) % p - 0.5 * p
        return out

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.linalg.norm(self.displacement(a, b)))
