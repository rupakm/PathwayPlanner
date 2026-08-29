"""Molecular state abstraction.

Planning operates over an abstract state s = phi(x), while the full
configuration x is always retained so that any action can be executed
from any state we have visited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class State:
    """An abstract molecular state paired with its full configuration.

    Attributes:
        configuration: Backend-specific handle to the full configuration
            (coordinates, velocities, box, ...). Opaque to the planner.
        features: Feature vector phi(x) used for planning and outcome
            classification.
        labels: Abstract state labels (e.g. "gate_open", "interface_intact")
            assigned by classifiers.
        metadata: Free-form provenance (source action, iteration, cost, ...).
    """

    configuration: Any
    features: np.ndarray
    labels: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_labels(self, *labels: str) -> "State":
        """Return a copy of this state with additional labels."""
        return State(
            configuration=self.configuration,
            features=self.features,
            labels=self.labels | set(labels),
            metadata=dict(self.metadata),
        )
