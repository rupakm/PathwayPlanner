"""Action compilation: (state, action) -> concrete implementation.

An Implementation is the I = (xi, V, T, N, rho) tuple from the design
doc: a CV or representation, an intervention, a duration, a replica
count, and a selection policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

import numpy as np


@dataclass
class Implementation:
    """One concrete physical realization of a structural action.

    Attributes:
        cv: Maps a configuration-space point to a progress coordinate.
        bias: Optional intervention; backend-specific meaning (e.g. a force
            callable for the toy backend, a bias spec for an MD backend).
        n_steps: Duration of each burst in backend steps.
        n_replicas: Number of independent bursts.
        policy: Named trajectory selection/resampling policy.
        params: Implementation-specific extras.
    """

    cv: Callable[[np.ndarray], float]
    bias: Any = None
    n_steps: int = 100
    n_replicas: int = 8
    policy: str = "all"
    params: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Compiler(Protocol):
    """Selects an implementation for an action in a given state."""

    def compile(self, state: "State", action: "Action") -> Implementation:  # noqa: F821
        ...
