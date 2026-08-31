"""Reconnaissance: does the missing ratchet explain the 0/90 result?

The selection-driven run of open_hinge(LID) returned 0 successes in 90
executions with a median theta_LID advance of 5.7 deg -- less than one
thermal fluctuation width (8-11 deg) after eight rounds of best-of-four
selection. A search that retained its selections should have accumulated
roughly 1 sigma per cycle, on the order of 60-90 deg over eight cycles,
which is far more than the 25 deg the event requires.

That discrepancy has a candidate explanation: PathGennieDriver defaults
`reject_worse_anchor` to False, so the anchor advances to the committed
candidate even when the candidate is worse. There is then no ratchet at
all and the anchor random-walks. The earlier run used that default,
because the adapter did not expose the flag.

This probe is small (2 conditions x 3 repeats x 50,000 steps, matching
one execution of the earlier run) and logs the per-cycle anchor angle,
which distinguishes three outcomes:

* monotone climb reaching 25 deg -> the missing ratchet was the whole
  story, and the earlier conclusion about the method was wrong;
* climb that stalls partway -> the barrier is genuine; selection helps
  but not enough at this budget;
* flat trace despite rejection being on -> selected excursions decay
  within the tau2 commit before they can be banked, which argues for
  longer commits or a time-averaged progress coordinate.

Usage:
  PYTHONPATH=<burst-api>:<pathgennie>:<pathwayplanner>:<here> \
      python recon_ratchet.py
Writes recon_ratchet_results.md next to this file.
"""

from __future__ import annotations

import json
import sys
import time
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
N_REPEATS = 3


def main() -> int:
    from pathgennie.backends.openmm.engine import OpenMMEngine

    theta = domains.lid_core_angle(CLOSED_TOPOLOGY)
    simulation, dt_ps = build_simulation("OpenCL")
    engine = OpenMMEngine(simulation, temperature=TEMPERATURE_K, n_workers=1)

    # One start state: the probe asks whether the anchor climbs, which does
    # not need the start-state replication a success-rate estimate would.
    start = start_positions(3, seed=17)[1]
    start_angle = float(theta.project(start)[0])
    threshold = start_angle + DELTA_DEG

    def opened(coords) -> bool:
        return float(theta.project(coords)[0]) >= threshold

    conditions = {
        "no ratchet (earlier run's defaults)": dict(
            reject_worse_anchor=False, reject_worse_tau2=False
        ),
        "ratchet (reject worse anchor and tau2)": dict(
            reject_worse_anchor=True, reject_worse_tau2=True
        ),
    }

    wall_start = time.perf_counter()
    results: dict[str, list[list[float]]] = {}
    for label, flags in conditions.items():
        traces = []
        for repeat in range(N_REPEATS):
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
                engine, start, spec, seed=31337 + repeat, budget=Budget(
                    max_steps=STEPS_PER_EXECUTION
                )
            )
            trace = [float(theta.project(f)[0]) for f in result.trajectory.frames]
            traces.append(trace)
        results[label] = traces
    wall = time.perf_counter() - wall_start

    lines = ["# Reconnaissance: does anchor rejection restore the ratchet?", ""]
    lines.append(
        f"Start theta_LID = {start_angle:.1f} deg; the event needs "
        f"{threshold:.1f} deg (an advance of {DELTA_DEG}). Swarm of "
        f"{MAX_TRIAL} x {TAU1 * dt_ps:.0f} ps, commit {TAU2 * dt_ps:.0f} ps, "
        f"{STEPS_PER_EXECUTION // (MAX_TRIAL * TAU1 + TAU2)} cycles, "
        f"{STEPS_PER_EXECUTION:,} steps per execution -- identical to the "
        f"earlier run. {N_REPEATS} repeats per condition."
    )
    lines.append("")
    for label, traces in results.items():
        lines.append(f"## {label}")
        lines.append("")
        lines.append("| repeat | per-cycle anchor theta_LID (deg) | net advance |")
        lines.append("| --- | --- | --- |")
        for index, trace in enumerate(traces):
            advance = trace[-1] - start_angle
            lines.append(
                f"| {index} | {', '.join(f'{a:.1f}' for a in trace)} | "
                f"{advance:+.1f} |"
            )
        finals = [t[-1] - start_angle for t in traces]
        peaks = [max(t) - start_angle for t in traces]
        monotone = [
            sum(1 for a, b in zip(t[:-1], t[1:]) if b >= a - 1e-9) / max(len(t) - 1, 1)
            for t in traces
        ]
        lines.append("")
        lines.append(
            f"- Net advance: {np.mean(finals):+.1f} deg mean "
            f"(range {min(finals):+.1f} to {max(finals):+.1f})."
        )
        lines.append(
            f"- Peak advance reached at any cycle: {np.mean(peaks):+.1f} deg mean "
            f"(range {min(peaks):+.1f} to {max(peaks):+.1f})."
        )
        lines.append(
            f"- Fraction of cycle-to-cycle steps that did not regress: "
            f"{np.mean(monotone):.2f} (1.00 would be a strict hill-climb)."
        )
        lines.append("")

    lines.append(f"Cost: {2 * N_REPEATS * STEPS_PER_EXECUTION:,} steps in "
                 f"{wall / 60:.0f} min.")
    (HERE / "recon_ratchet_results.md").write_text("\n".join(lines) + "\n")
    (HERE / "recon_ratchet_traces.json").write_text(
        json.dumps({"start_angle": start_angle, "traces": results}, indent=2) + "\n"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
