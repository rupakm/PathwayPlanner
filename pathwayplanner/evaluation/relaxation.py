"""Direction of relaxation after an intervention is removed.

Whether a produced structure "persists" was reported as a threshold on
coordinate drift. No setting of that threshold is defensible: the
coordinate's own thermal fluctuation is comparable to any drift worth
detecting, so a permissive threshold passes everything and a strict one
fails everything, and neither reports which way the system moved.

The question is also ill-posed for the configurations an action typically
returns. These lie on a gradient rather than in a basin, and such a
structure always relaxes; what carries information is the direction and
size of that relaxation, not whether it stayed within an arbitrary
window.

This module therefore reports a signed measurement and makes no claim
about stability. Establishing that a structure has committed to a basin
requires the committor, estimated from trajectories long enough to reach
one, which is a separate and far more expensive measurement.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pathwayplanner.backends.base import Trajectory
from pathwayplanner.cv import CVSpace


@dataclass
class RelaxationDirection:
    """Signed change of a progress coordinate over an unbiased window.

    Attributes:
        mean_change: Mean of (final - initial) across trajectories, in the
            coordinate's units. Positive means the ensemble moved toward
            the product state.
        sd_change: Spread of that change, so the mean is never read alone.
        fraction_advancing: Fraction of trajectories whose change is
            positive.
        mean_start, mean_end: Ensemble means at release and at the end of
            the window.
        n: Number of trajectories.
    """

    mean_change: float
    sd_change: float
    fraction_advancing: float
    mean_start: float
    mean_end: float
    n: int

    def summary(self, units: str = "") -> str:
        """One line suitable for a results table."""
        if self.n == 0:
            return "no trajectories"
        suffix = f" {units}" if units else ""
        return (
            f"{self.mean_start:+.2f} -> {self.mean_end:+.2f}{suffix}, "
            f"change {self.mean_change:+.2f} (sd {self.sd_change:.2f}), "
            f"{int(round(self.fraction_advancing * self.n))}/{self.n} advancing"
        )


def relaxation_direction(
    space: CVSpace, trajectories: list[Trajectory]
) -> RelaxationDirection:
    """Measure how a progress coordinate moves once the bias is removed.

    `space` should project a frame onto a coordinate that increases toward
    the product state; the difference of RMSD values to the two reference
    structures is a natural choice, being signed and threshold-free.

    Each trajectory supplies its own baseline from its first frame, so
    successors released from different configurations are comparable.
    """
    starts, ends = [], []
    for trajectory in trajectories:
        if len(trajectory.frames) < 2:
            continue
        starts.append(float(space.project(trajectory.frames[0])[0]))
        ends.append(float(space.project(trajectory.frames[-1])[0]))
    if not starts:
        return RelaxationDirection(
            float("nan"), float("nan"), float("nan"), float("nan"), float("nan"), 0
        )
    starts_a, ends_a = np.array(starts), np.array(ends)
    change = ends_a - starts_a
    return RelaxationDirection(
        mean_change=float(change.mean()),
        sd_change=float(change.std()),
        fraction_advancing=float((change > 0).mean()),
        mean_start=float(starts_a.mean()),
        mean_end=float(ends_a.mean()),
        n=len(change),
    )
