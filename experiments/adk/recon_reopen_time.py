"""How long does a restraint-closed LID stay closed?

The stability probe watched 250 ps and found five of six replicas still
closed -- but one had drifted +26 deg and was reopening when the window
ended, which a single 131.3 deg threshold reported as "no". Two lessons
are built in here: watch long enough to see the event, and report a
graded recovery rather than one arbitrary cut.

This runs 1 ns of unbiased dynamics per replica and records first-passage
times to three reopening levels, so the result is a survival curve at
several definitions instead of a verdict at one. It also tracks C-alpha
RMSD to both crystal endpoints, which says where the structure actually
goes rather than only what one angle does.

The number this is for: the relaxation window the full close_hinge run
should use. A persistence measurement made over a window much shorter
than the reopening time looks decisive while being uninformative, which
is what a 250 ps window would have produced.

Usage:
  PYTHONPATH=<burst-api>:<pathwayplanner>:<here> \
      python recon_reopen_time.py
Writes recon_reopen_time_results.md next to this file.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from pathwayplanner import Budget, Implementation, Outcome, State
from pathwayplanner.actions.hinge import HingeClosingAction
from pathwayplanner.backends.trailsmd import TrailsMDBackend

import domains
from run_close_hinge import (
    CLOSED_THETA_DEG,
    DELTA_DEG,
    OPEN_EQUILIBRATED,
    OPEN_TOPOLOGY,
    _positions,
    distance_bias,
)
from trails_md.bursts import BurstSystem

HERE = Path(__file__).resolve().parent

N_SUCCESSORS = 2
N_REPLICAS = 4
CLOSE_STEPS = 12500          # 50 ps of restrained closing
WATCH_STEPS = 250000         # 1 ns of unbiased watching
WATCH_STRIDE = 1250          # 5 ps resolution
BIAS_K = 2000.0

# Graded reopening levels rather than one threshold: partway back, most of
# the way back, and effectively returned to the open basin.
LEVELS_DEG = [115.0, 125.0, 135.0]


def first_passage(series, level, dt_ps):
    """Time in ps at which `series` first reaches `level`, or None."""
    for index, value in enumerate(series):
        if value >= level:
            return (index + 1) * dt_ps
    return None


def main() -> int:
    system = BurstSystem(
        engine_name="openmm",
        engine_kwargs={"platform_name": "OpenCL", "temperature": 300.0, "dt": 0.004},
        conf=OPEN_TOPOLOGY, top=OPEN_TOPOLOGY, system_file=HERE / "system.py",
    )
    theta = domains.lid_core_angle(OPEN_TOPOLOGY)
    to_open = domains.rmsd_to_reference(OPEN_TOPOLOGY, domains.OPEN_PDB)
    to_closed = domains.rmsd_to_reference(OPEN_TOPOLOGY, domains.CLOSED_PDB)
    budget = Budget(max_steps=10**9)
    runs = HERE / "runs" / "reopen_time"
    if runs.exists():
        shutil.rmtree(runs)
    runs.mkdir(parents=True)

    def backend(tag, seed, stride):
        return TrailsMDBackend(system=system, space=theta, workdir=runs / tag,
                               stride=stride, base_seed=seed)

    start = State(configuration=OPEN_EQUILIBRATED,
                  features=_positions(OPEN_EQUILIBRATED))
    start_angle = float(theta.project(start.features)[0])
    frame_dt_ps = WATCH_STRIDE * 0.004

    wall_start = time.perf_counter()
    closer = HingeClosingAction(
        name="close_hinge_LID", space=theta, delta=DELTA_DEG,
        bias=distance_bias(BIAS_K), n_steps=CLOSE_STEPS, n_replicas=4,
        stop_at=CLOSED_THETA_DEG,
    )
    closed = []
    attempt = 0
    while len(closed) < N_SUCCESSORS:
        result = closer.run(start, backend(f"close_{attempt}", 500 + attempt, 1250), budget)
        attempt += 1
        if result.outcome is Outcome.SUCCESS:
            closed.append(result.best_state)

    traces = []
    for index, successor in enumerate(closed):
        trajectories = backend(f"watch_{index}", 1300 + index, WATCH_STRIDE).run_bursts(
            [successor],
            Implementation(cv=theta, bias=None, n_steps=WATCH_STEPS,
                           n_replicas=N_REPLICAS),
            budget,
        )
        for replica, trajectory in enumerate(trajectories):
            series = [float(theta.project(f)[0]) for f in trajectory.frames]
            traces.append(
                {
                    "successor": index,
                    "replica": replica,
                    "closed_at": float(theta.project(successor.features)[0]),
                    "theta": series,
                    "rmsd_open_final": float(to_open.project(trajectory.frames[-1])[0]),
                    "rmsd_closed_final": float(
                        to_closed.project(trajectory.frames[-1])[0]
                    ),
                    "passages": {
                        str(level): first_passage(series, level, frame_dt_ps)
                        for level in LEVELS_DEG
                    },
                }
            )
    wall = time.perf_counter() - wall_start

    lines = ["# How long does a restraint-closed LID stay closed?", ""]
    lines.append(
        f"Open start theta_LID = {start_angle:.1f} deg, closed under a "
        f"k = {BIAS_K:.0f} kJ/mol/nm^2 restraint, then watched unbiased for "
        f"{WATCH_STEPS * 0.004 / 1000:.1f} ns at {frame_dt_ps:.0f} ps "
        f"resolution. {N_REPLICAS} replicas from each of {N_SUCCESSORS} closed "
        f"successors. Crystal endpoints: 146.5 (open), 106.1 (closed)."
    )
    lines.append("")
    lines.append("| successor | replica | closed at | final | max | "
                 + " | ".join(f"t to {int(v)} deg" for v in LEVELS_DEG)
                 + " | RMSD open / closed |")
    lines.append("| --- | --- | --- | --- | --- | " + " | ".join("---" for _ in LEVELS_DEG)
                 + " | --- |")
    for t in traces:
        passages = " | ".join(
            "-" if t["passages"][str(v)] is None else f"{t['passages'][str(v)]:.0f} ps"
            for v in LEVELS_DEG
        )
        lines.append(
            f"| {t['successor']} | {t['replica']} | {t['closed_at']:.1f} | "
            f"{t['theta'][-1]:.1f} | {max(t['theta']):.1f} | {passages} | "
            f"{t['rmsd_open_final']:.1f} / {t['rmsd_closed_final']:.1f} A |"
        )
    lines.append("")

    total_ns = len(traces) * WATCH_STEPS * 0.004 / 1000
    for level in LEVELS_DEG:
        times = [t["passages"][str(level)] for t in traces]
        seen = [x for x in times if x is not None]
        if seen:
            # Crude MFPT: total watched time divided by events observed. With
            # censored replicas this underestimates nothing and overestimates
            # when events cluster early, so treat it as an order of magnitude.
            mfpt = total_ns * 1000 / len(seen)
            lines.append(
                f"- Reached {int(level)} deg in {len(seen)}/{len(traces)} replicas; "
                f"first passages {', '.join(f'{x:.0f}' for x in sorted(seen))} ps; "
                f"crude mean first-passage time ~{mfpt:.0f} ps "
                f"({total_ns:.1f} ns watched / {len(seen)} events)."
            )
        else:
            lines.append(
                f"- Reached {int(level)} deg in 0/{len(traces)} replicas, so the "
                f"mean first-passage time exceeds ~{total_ns * 1000:.0f} ps of "
                f"aggregate watching."
            )
    lines.append("")
    lines.append("## Traces (theta_LID, deg, every 20 ps)")
    lines.append("")
    for t in traces:
        lines.append(f"- s{t['successor']} r{t['replica']}: "
                     + ", ".join(f"{a:.0f}" for a in t["theta"][::4]))
    lines.append("")
    lines.append(f"Cost: {N_SUCCESSORS * (4 * CLOSE_STEPS + N_REPLICAS * WATCH_STEPS):,} "
                 f"steps ({total_ns:.1f} ns watched) in {wall / 60:.0f} min.")

    (HERE / "recon_reopen_time_results.md").write_text("\n".join(lines) + "\n")
    (HERE / "recon_reopen_time.json").write_text(
        json.dumps({"start_angle": start_angle, "levels": LEVELS_DEG,
                    "traces": traces}, indent=2) + "\n"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
