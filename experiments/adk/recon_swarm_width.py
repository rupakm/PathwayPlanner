"""Does a wider swarm reach further into the tail? A budget-neutral probe.

The instrumented run showed the selection-driven search stalls where the
best of four 5 ps trials can no longer exceed the anchor -- about +10 deg,
close to one standard deviation of theta_LID's thermal fluctuation. That
diagnosis makes a quantitative prediction: the best of m draws from a
roughly Gaussian distribution sits about sqrt(2 ln m) standard deviations
above the mean, so widening the swarm should push the reachable angle up
as sqrt(2 ln m) -- a factor of 1.58 from m=4 to m=32.

Budget is held at the 50,000 steps of one earlier execution, which forces
the trade the probe is about: a cycle costs m*tau1 + tau2, so more trials
buys fewer cycles.

    m= 4 ->  6,250/cycle -> 8 cycles
    m= 8 -> 11,250/cycle -> 4 cycles
    m=16 -> 21,250/cycle -> 2 cycles
    m=32 -> 41,250/cycle -> 1 cycle

The ratchet is enabled throughout, since the question is whether a wider
swarm lets a hill-climb keep climbing rather than stall.

Reported per condition: the mean best-trial advance over the anchor it was
drawn from (the direct tail-reach measurement, which is what the sqrt(2 ln m)
prediction is about) and the peak anchor advance reached.

Usage:
  PYTHONPATH=<burst-api>:<pathgennie>:<pathwayplanner>:<here> \
      python recon_swarm_width.py
Writes recon_swarm_width_results.md next to this file.
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
from instrument_pathgennie import SegmentRecorder, cycles_from
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
TAU1 = TAU2 = 1250
WIDTHS = [4, 8, 16, 32]
N_REPEATS = 3


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

    wall_start = time.perf_counter()
    summary = {}
    for width in WIDTHS:
        cycles_per_execution = STEPS_PER_EXECUTION // (width * TAU1 + TAU2)
        reaches, peaks, successes = [], [], 0
        for repeat in range(N_REPEATS):
            engine = SegmentRecorder(inner, theta)
            spec = DriverSearchSpec(
                space=theta,
                event=opened,
                target_cv=np.array([OPEN_THETA_DEG]),
                tau1=TAU1,
                tau2=TAU2,
                max_trial=width,
                max_cycle=cycles_per_execution,
                reject_worse_anchor=True,
                reject_worse_tau2=True,
            )
            result = run_driver_search(
                engine, start, spec, seed=9001 + 37 * repeat + width,
                budget=Budget(max_steps=STEPS_PER_EXECUTION),
            )
            anchors = [float(theta.project(f)[0]) for f in result.trajectory.frames]
            peaks.append(max(anchors) - start_angle)
            successes += bool(result.converged)
            # Tail reach: how far the best trial of a cycle sat above the
            # anchor that cycle started from.
            previous = start_angle
            for cycle in cycles_from(engine.log, width):
                reaches.append(cycle["best_trial"] - previous)
                previous = max(previous, cycle["commit_end"])
        summary[width] = {
            "cycles": cycles_per_execution,
            "mean_reach": float(np.mean(reaches)),
            "max_reach": float(np.max(reaches)),
            "mean_peak": float(np.mean(peaks)),
            "max_peak": float(np.max(peaks)),
            "successes": successes,
            "n_cycles_sampled": len(reaches),
        }
    wall = time.perf_counter() - wall_start

    base = summary[WIDTHS[0]]["mean_reach"]
    lines = ["# Does a wider swarm reach further into the tail?", ""]
    lines.append(
        f"Start theta_LID = {start_angle:.1f} deg, event threshold "
        f"{threshold:.1f} deg (advance {DELTA_DEG}). Every execution spends "
        f"{STEPS_PER_EXECUTION:,} steps with tau1 = tau2 = "
        f"{TAU1 * dt_ps:.0f} ps and the ratchet on, so swarm width is bought "
        f"with cycles. {N_REPEATS} repeats per width."
    )
    lines.append("")
    lines.append("| trials m | cycles | mean best-trial reach | max reach | "
                 "mean peak advance | max peak | successes | predicted reach |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for width in WIDTHS:
        d = summary[width]
        predicted = base * np.sqrt(np.log(width) / np.log(WIDTHS[0]))
        lines.append(
            f"| {width} | {d['cycles']} | {d['mean_reach']:+.1f} deg | "
            f"{d['max_reach']:+.1f} | {d['mean_peak']:+.1f} deg | "
            f"{d['max_peak']:+.1f} | {d['successes']}/{N_REPEATS} | "
            f"{predicted:+.1f} deg |"
        )
    lines.append("")
    lines.append(
        "`Predicted reach` scales the m=4 measurement by sqrt(ln m / ln 4), the "
        "growth of the expected maximum of m Gaussian draws. Agreement supports "
        "the regression-to-the-mean account of the stall; a flat or slower "
        "curve means the trials are not independent draws -- 5 ps segments "
        "starting from the same anchor are correlated, which would cap the "
        "benefit of widening the swarm."
    )
    lines.append("")
    lines.append(f"Cost: {N_REPEATS * sum(summary[w]['cycles'] * (w * TAU1 + TAU2) for w in WIDTHS):,} "
                 f"steps in {wall / 60:.0f} min.")

    (HERE / "recon_swarm_width_results.md").write_text("\n".join(lines) + "\n")
    (HERE / "recon_swarm_width.json").write_text(
        json.dumps({"start_angle": start_angle, "threshold": threshold,
                    "summary": summary}, indent=2) + "\n"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
