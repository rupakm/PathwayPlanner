"""Record every segment of a PathGennie search, to see where it stalls.

The anchor trace shows *that* a selection-driven search plateaus; it does
not show *why*. The mechanism lives inside each cycle: a swarm of tau1
trials explores, the best is selected, and the tau2 commit either banks
that gain or gives it back. Only the last of those is visible in the
anchor.

This wraps the engine and logs the hinge angle at the end of every
segment, tagged by kind -- `randomize_velocities=True` marks a tau1
trial, False marks the tau2 commit -- so a cycle can be reconstructed as
a run of trials followed by one commit. Comparing the best trial angle
against the following commit angle measures directly how much of each
selected excursion survives.

Usage:
  PYTHONPATH=<burst-api>:<pathgennie>:<pathwayplanner>:<here> \
      python instrument_pathgennie.py
Writes pathgennie_segments.json next to this file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from pathwayplanner import Budget
from pathwayplanner.backends.pathgennie import DriverSearchSpec, run_driver_search

import domains
from run_open_hinge_pathgennie import (
    DELTA_DEG,
    OPEN_THETA_DEG,
    STEPS_PER_EXECUTION,
    TEMPERATURE_K,
    build_simulation,
    start_positions,
)

HERE = Path(__file__).resolve().parent
CLOSED_TOPOLOGY = HERE / "structures" / "adk_closed_topology.pdb"
MAX_TRIAL, TAU1, TAU2 = 4, 1250, 1250
N_REPEATS = 2


class SegmentRecorder:
    """Engine wrapper logging the hinge angle at the end of every segment."""

    def __init__(self, inner, theta):
        self._inner = inner
        self._theta = theta
        self.log: list[dict] = []

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def _angle(self, handle) -> float:
        return float(self._theta.project(self._inner.get_coords(handle))[0])

    def run_segment(self, handle, n_steps, *, randomize_velocities, **kwargs):
        before = self._angle(handle)
        result = self._inner.run_segment(
            handle, n_steps, randomize_velocities=randomize_velocities, **kwargs
        )
        out = result[0] if isinstance(result, tuple) else result
        self.log.append(
            {
                "kind": "trial" if randomize_velocities else "commit",
                "start": before,
                "end": self._angle(out),
                "n_steps": int(n_steps),
            }
        )
        return result


def cycles_from(log: list[dict], max_trial: int) -> list[dict]:
    """Group a segment log into cycles: a run of trials, then one commit."""
    cycles, trials = [], []
    for entry in log:
        if entry["kind"] == "trial":
            trials.append(entry["end"])
        else:
            cycles.append(
                {
                    "trials": trials,
                    "best_trial": max(trials) if trials else None,
                    "commit_start": entry["start"],
                    "commit_end": entry["end"],
                }
            )
            trials = []
    return cycles


def main() -> int:
    from pathgennie.backends.openmm.engine import OpenMMEngine

    theta = domains.lid_core_angle(CLOSED_TOPOLOGY)
    simulation, dt_ps = build_simulation("OpenCL")
    inner = OpenMMEngine(simulation, temperature=TEMPERATURE_K, n_workers=1)

    start = start_positions(3, seed=17)[1]
    start_angle = float(theta.project(start)[0])
    threshold = start_angle + DELTA_DEG

    def opened(coords) -> bool:
        return float(theta.project(coords)[0]) >= threshold

    conditions = {
        "no_ratchet": dict(reject_worse_anchor=False, reject_worse_tau2=False),
        "ratchet": dict(reject_worse_anchor=True, reject_worse_tau2=True),
    }
    out: dict[str, list] = {}
    for label, flags in conditions.items():
        runs = []
        for repeat in range(N_REPEATS):
            engine = SegmentRecorder(inner, theta)
            spec = DriverSearchSpec(
                space=theta,
                event=opened,
                target_cv=np.array([OPEN_THETA_DEG]),
                tau1=TAU1,
                tau2=TAU2,
                max_trial=MAX_TRIAL,
                max_cycle=STEPS_PER_EXECUTION // (MAX_TRIAL * TAU1 + TAU2),
                **flags,
            )
            result = run_driver_search(
                engine, start, spec, seed=4242 + repeat,
                budget=Budget(max_steps=STEPS_PER_EXECUTION),
            )
            runs.append(
                {
                    "cycles": cycles_from(engine.log, MAX_TRIAL),
                    "anchor": [
                        float(theta.project(f)[0]) for f in result.trajectory.frames
                    ],
                }
            )
        out[label] = runs

    payload = {
        "start_angle": start_angle,
        "threshold": threshold,
        "delta_deg": DELTA_DEG,
        "tau1_ps": TAU1 * dt_ps,
        "tau2_ps": TAU2 * dt_ps,
        "max_trial": MAX_TRIAL,
        "conditions": out,
    }
    (HERE / "pathgennie_segments.json").write_text(json.dumps(payload, indent=2) + "\n")

    for label, runs in out.items():
        print(f"\n== {label}")
        for index, run in enumerate(runs):
            print(f"  run {index}: anchor "
                  f"{', '.join(f'{a:.1f}' for a in run['anchor'])}")
            for c, cycle in enumerate(run["cycles"]):
                spread = ", ".join(f"{t:.1f}" for t in cycle["trials"])
                give_back = cycle["best_trial"] - cycle["commit_end"]
                print(f"    cycle {c}: trials [{spread}] best "
                      f"{cycle['best_trial']:.1f} -> commit "
                      f"{cycle['commit_end']:.1f} (gave back {give_back:+.1f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
