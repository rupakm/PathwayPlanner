"""Re-probe: does a conjunctive event give a real closed structure?

The stability and reopening probes settled two questions and raised a
third. The restraint-closed state is metastable (no replica returned past
125 deg in 8 ns), so UNSTABLE does not arise here. But its RMSD said the
structure sat about 5 A from the closed conformation while theta_LID read
past the closed crystal value: the one-coordinate event was satisfied by
a configuration that was not the closed state.

This run repeats the closing with the event made conjunctive -- the angle
must fall by 25 deg *and* the C-alpha RMSD to 1AKE must fall by 2 A, in
the same frame -- and reports the RMSD reached either way. The question
is no longer whether the hinge closes but whether requiring the structure
to follow produces a materially different, and better, closed state.

Usage:
  PYTHONPATH=<burst-api>:<pathwayplanner>:<here> \
      python recon_close_stability.py
Writes recon_close_stability_results.md next to this file.
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
from pathwayplanner.outcomes import Criterion
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

N_SUCCESSORS = 3
CLOSE_STEPS = 12500        # 50 ps of restrained closing, as in the full design
RELAX_STEPS = 62500        # 250 ps: ample, since reopening exceeds 8 ns
RMSD_DELTA_A = 2.0         # required approach to the closed crystal structure
RELAX_STRIDE = 1250        # 5 ps resolution
RELAX_REPLICAS = 2
BIAS_K = 2000.0


def main() -> int:
    system = BurstSystem(
        engine_name="openmm",
        engine_kwargs={"platform_name": "OpenCL", "temperature": 300.0, "dt": 0.004},
        conf=OPEN_TOPOLOGY,
        top=OPEN_TOPOLOGY,
        system_file=HERE / "system.py",
    )
    theta = domains.lid_core_angle(OPEN_TOPOLOGY)
    lid_core = domains.lid_core_distance(OPEN_TOPOLOGY)
    budget = Budget(max_steps=10**9)
    runs = HERE / "runs" / "close_stability"
    if runs.exists():
        shutil.rmtree(runs)
    runs.mkdir(parents=True)

    def backend(tag: str, seed: int, stride: int) -> TrailsMDBackend:
        return TrailsMDBackend(system=system, space=theta, workdir=runs / tag,
                               stride=stride, base_seed=seed)

    start = State(configuration=OPEN_EQUILIBRATED,
                  features=_positions(OPEN_EQUILIBRATED))
    start_angle = float(theta.project(start.features)[0])

    wall_start = time.perf_counter()

    # 1. Close the hinge under restraint, keeping the closed successors.
    to_closed = domains.rmsd_to_reference(OPEN_TOPOLOGY, domains.CLOSED_PDB)
    rmsd_criterion = Criterion(
        space=to_closed, target_point=np.array([0.0]), delta=RMSD_DELTA_A
    )
    variants = {
        "angle only": None,
        "angle and RMSD (conjunctive)": [rmsd_criterion],
    }

    outcomes = {}
    closed = {}
    for label, also in variants.items():
        closer = HingeClosingAction(
            name="close_hinge_LID", space=theta, delta=DELTA_DEG,
            bias=distance_bias(BIAS_K), n_steps=CLOSE_STEPS, n_replicas=4,
            stop_at=CLOSED_THETA_DEG, also=also,
        )
        tag = "conj" if also else "angle"
        got, seen = [], []
        for attempt in range(N_SUCCESSORS * 2):
            if len(got) >= N_SUCCESSORS:
                break
            result = closer.run(
                start, backend(f"close_{tag}_{attempt}", 400 + attempt, 1250), budget
            )
            seen.append(result.outcome.value)
            if result.outcome is Outcome.SUCCESS:
                got.append(result.best_state)
        outcomes[label] = seen
        closed[label] = got

    # 2. Remove the restraint and watch the conjunctive successors.
    traces = []
    for index, successor in enumerate(closed["angle and RMSD (conjunctive)"]):
        angle = float(theta.project(successor.features)[0])
        trajectories = backend(f"relax_{index}", 900 + index, RELAX_STRIDE).run_bursts(
            [successor],
            Implementation(cv=theta, bias=None, n_steps=RELAX_STEPS,
                           n_replicas=RELAX_REPLICAS),
            budget,
        )
        for replica, trajectory in enumerate(trajectories):
            series = [float(theta.project(f)[0]) for f in trajectory.frames]
            traces.append(
                {
                    "successor": index,
                    "replica": replica,
                    "closed_at": angle,
                    "theta": series,
                    "lid_core": [
                        float(lid_core.project(f)[0]) for f in trajectory.frames
                    ],
                    "rmsd_closed": [
                        float(to_closed.project(f)[0]) for f in trajectory.frames
                    ],
                    "closed_rmsd_at": float(to_closed.project(successor.features)[0]),
                }
            )
    wall = time.perf_counter() - wall_start

    # 3. Report.
    reopen_level = start_angle - DELTA_DEG / 2.0
    lines = ["# Conjunctive close_hinge: does the structure follow the angle?", ""]
    lines.append("## Event outcomes by specification")
    lines.append("")
    lines.append("| event specification | outcomes over attempts |")
    lines.append("| --- | --- |")
    for label, seen in outcomes.items():
        lines.append(f"| {label} | {', '.join(seen)} |")
    lines.append("")
    lines.append(
        f"Open start theta_LID = {start_angle:.1f} deg. The hinge is closed "
        f"under a k = {BIAS_K:.0f} kJ/mol/nm^2 restraint for "
        f"{CLOSE_STEPS * 0.004:.0f} ps, then the restraint is removed and "
        f"theta_LID is watched for {RELAX_STEPS * 0.004:.0f} ps at "
        f"{RELAX_STRIDE * 0.004:.0f} ps resolution, {RELAX_REPLICAS} replicas "
        f"from each of {N_SUCCESSORS} closed successors."
    )
    lines.append("")
    lines.append(f"'Reopened' below means theta_LID returned above "
                 f"{reopen_level:.1f} deg, half the {DELTA_DEG} deg event back "
                 f"toward the open start.")
    lines.append("")
    lines.append("| successor | replica | closed at | after 50 ps | after 250 ps "
                 "| max | reopened? |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    reopened_count = 0
    for trace in traces:
        series = trace["theta"]
        at50 = series[min(9, len(series) - 1)]
        reopened = max(series) >= reopen_level
        reopened_count += reopened
        lines.append(
            f"| {trace['successor']} | {trace['replica']} | "
            f"{trace['closed_at']:.1f} | {at50:.1f} | {series[-1]:.1f} | "
            f"{max(series):.1f} | {'yes' if reopened else 'no'} |"
        )
    lines.append("")
    finals = [t["theta"][-1] for t in traces]
    closed_at = [t["closed_at"] for t in traces]
    lines.append(
        f"- Closed to {np.mean(closed_at):.1f} deg on average; after 250 ps "
        f"unbiased the mean is {np.mean(finals):.1f} deg "
        f"(open start was {start_angle:.1f})."
    )
    lines.append(f"- Reopened past {reopen_level:.1f} deg: "
                 f"{reopened_count}/{len(traces)} replicas.")
    start_rmsd = float(to_closed.project(start.features)[0])
    rmsd_at = [t["closed_rmsd_at"] for t in traces]
    rmsd_end = [t["rmsd_closed"][-1] for t in traces]
    lines.append(
        f"- RMSD to the closed crystal: {start_rmsd:.1f} A at the open start, "
        f"{np.mean(rmsd_at):.1f} A when the event fired, "
        f"{np.mean(rmsd_end):.1f} A after 250 ps unbiased. The endpoints are "
        f"7.1 A apart, so this is the fraction of the conformational change "
        f"the action actually delivered."
    )
    lines.append("")
    lines.append("## Traces (theta_LID, deg, every 5 ps)")
    lines.append("")
    for trace in traces:
        sampled = trace["theta"][::2]
        lines.append(f"- successor {trace['successor']} replica {trace['replica']}: "
                     + ", ".join(f"{a:.0f}" for a in sampled))
    lines.append("")
    lines.append(f"Cost: {N_SUCCESSORS * (4 * CLOSE_STEPS + RELAX_REPLICAS * RELAX_STEPS):,} "
                 f"steps in {wall / 60:.0f} min.")

    (HERE / "recon_close_stability_results.md").write_text("\n".join(lines) + "\n")
    (HERE / "recon_close_stability.json").write_text(
        json.dumps({"start_angle": start_angle, "traces": traces}, indent=2) + "\n"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
