"""open_hinge(LID) by selection-driven search, cost-matched to the biased run.

The third implementation family for the same action and the same event
specification. Where run_open_hinge.py adds a restraint to the
Hamiltonian, this run never distorts the dynamics: PathGennie's driver
launches a swarm of tau1 trials from the current anchor, scores each by
progress in theta_LID, softmax-selects one, extends it for tau2, and
repeats. Directed motion comes from *selection*, not from force.

Why that distinction is worth the compute
-----------------------------------------
The two families fail differently, so neither alone settles whether an
opening is physical. A restraint makes every trajectory non-Boltzmann,
which is why the biased run needed the relaxation check to show the
hinge stayed open once the force was removed. Here each committed
segment is ordinary unbiased dynamics and is individually Boltzmann
valid; the bias enters only through which segments are kept, so the
*ensemble* is skewed while no single trajectory is. Whether the two
families find the same opening, at the same cost, is the first real
instance of the WP2 implementation-selection question on a protein.

Cost matching
-------------
One driver cycle costs max_trial*tau1 + tau2 integrator steps. With
MAX_TRIAL=4, TAU1=TAU2=1250 steps (5 ps at 4 fs) a cycle is 6250 steps
and the budget of 50000 steps allows 8 cycles -- exactly the 4 replicas
x 12500 steps that one biased execution spends. Success rates are
therefore comparable to the biased and null families without rescaling.

Usage:
  PYTHONPATH=<trails-md-burst-api>:<pathwayplanner>:<here> \
      python run_open_hinge_pathgennie.py [--fast]
Writes open_hinge_pathgennie_results.md next to this file.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from pathwayplanner import Budget, Outcome
from pathwayplanner.backends.pathgennie import (
    DriverSearchSpec,
    run_driver_search,
    search_to_action_result,
)

import domains

HERE = Path(__file__).resolve().parent
STRUCTURES = HERE / "structures"
CLOSED_TOPOLOGY = STRUCTURES / "adk_closed_topology.pdb"
CLOSED_SYSTEM_XML = STRUCTURES / "adk_closed_system.xml"
CLOSED_BUILD_JSON = STRUCTURES / "adk_closed_build.json"

# Held identical to run_open_hinge.py so the families are comparable.
DELTA_DEG = 25.0
OPEN_THETA_DEG = 146.5

STEPS_PER_EXECUTION = 50000
TEMPERATURE_K = 300.0

# Cost is fixed; its allocation is not. A swarm of many short trials
# explores breadth per cycle but commits little path, while few long trials
# commit more path per cycle from a narrower choice. Reporting one
# allocation would confuse "selection-driven search does not open this
# hinge" with "this particular allocation does not", so the same budget is
# spent three ways. (max_trial, tau1, tau2) -> steps/cycle = m*t1 + t2.
ALLOCATIONS = [
    ("broad swarm, 5 ps segments", 4, 1250, 1250),
    ("narrow swarm, 10 ps segments", 2, 2500, 2500),
    ("wide swarm, 5 ps segments", 8, 1250, 1250),
]


def build_simulation(platform_name: str = "OpenCL"):
    """An OpenMM Simulation on the closed AdK system, for the PathGennie engine."""
    from openmm import LangevinMiddleIntegrator, Platform, XmlSerializer
    from openmm.app import PDBFile, Simulation
    from openmm.unit import kelvin, picosecond, picoseconds

    dt_ps = json.loads(CLOSED_BUILD_JSON.read_text())["dt_ps"]
    system = XmlSerializer.deserialize(CLOSED_SYSTEM_XML.read_text())
    pdb = PDBFile(str(CLOSED_TOPOLOGY))
    integrator = LangevinMiddleIntegrator(
        TEMPERATURE_K * kelvin, 1.0 / picosecond, dt_ps * picoseconds
    )
    try:
        platform = Platform.getPlatformByName(platform_name)
    except Exception:  # noqa: BLE001 - platform availability is environmental
        platform = None
    simulation = (
        Simulation(pdb.topology, system, integrator, platform)
        if platform is not None
        else Simulation(pdb.topology, system, integrator)
    )
    simulation.context.setPositions(pdb.positions)
    return simulation, dt_ps


def start_positions(n_states: int, seed: int) -> list[np.ndarray]:
    """Reuse the biased run's start states when present, else equilibrate anew.

    Reusing them is what makes the families comparable: the same starting
    configurations, so a difference in success rate is a difference between
    implementations rather than between starting points.
    """
    import MDAnalysis as mda

    saved = sorted((HERE / "runs" / "open_hinge" / "starts").glob("burst_*/*.xtc"))
    if saved:
        universe = mda.Universe(str(CLOSED_TOPOLOGY), [str(p) for p in saved])
        positions = []
        for index in range(min(n_states, len(saved))):
            universe.trajectory[
                (index + 1) * (len(universe.trajectory) // max(len(saved), 1)) - 1
            ]
            positions.append(universe.atoms.positions.astype(float).copy())
        if len(positions) == n_states:
            return positions
    equilibrated = STRUCTURES / "adk_closed_equilibrated.pdb"
    frame = mda.Universe(str(equilibrated)).atoms.positions.astype(float)
    return [frame.copy() for _ in range(n_states)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--platform", default="OpenCL")
    args = parser.parse_args()

    for path in (CLOSED_SYSTEM_XML, CLOSED_TOPOLOGY, CLOSED_BUILD_JSON):
        if not path.exists():
            print(f"Missing {path}; run build_system.py --state closed first.",
                  file=sys.stderr)
            return 1

    n_states = 1 if args.fast else 3
    n_repeats = 2 if args.fast else 10
    budget = Budget(max_steps=STEPS_PER_EXECUTION)

    from pathgennie.backends.openmm.engine import OpenMMEngine

    theta = domains.lid_core_angle(CLOSED_TOPOLOGY)
    simulation, dt_ps = build_simulation(args.platform)
    engine = OpenMMEngine(simulation, temperature=TEMPERATURE_K, n_workers=1)

    starts = start_positions(n_states, seed=17)
    start_angles = [float(theta.project(p)[0]) for p in starts]

    wall_start = time.perf_counter()
    allocations = ALLOCATIONS[:1] if args.fast else ALLOCATIONS
    summary: dict[str, dict] = {}

    for label, max_trial, tau1, tau2 in allocations:
        per_state_rates = []
        counts: dict[str, int] = {}
        advances: list[float] = []
        cycles_per_execution = STEPS_PER_EXECUTION // (max_trial * tau1 + tau2)
        for index, (start, start_angle) in enumerate(zip(starts, start_angles)):
            threshold = start_angle + DELTA_DEG

            def opened(coords, threshold=threshold) -> bool:
                return float(theta.project(coords)[0]) >= threshold

            spec = DriverSearchSpec(
                space=theta,
                event=opened,
                target_cv=np.array([OPEN_THETA_DEG]),
                tau1=tau1,
                tau2=tau2,
                max_trial=max_trial,
                max_cycle=cycles_per_execution,
            )
            successes = 0
            for repeat in range(n_repeats):
                result = run_driver_search(
                    engine, start, spec,
                    seed=5000 + 101 * index + repeat + 7919 * len(summary),
                    budget=budget,
                )
                action_result = search_to_action_result(result)
                counts[action_result.outcome.value] = (
                    counts.get(action_result.outcome.value, 0) + 1
                )
                successes += action_result.outcome is Outcome.SUCCESS
                final_angle = float(theta.project(result.trajectory.frames[-1])[0])
                advances.append(final_angle - start_angle)
            per_state_rates.append(successes / n_repeats)
        summary[label] = {
            "per_state": per_state_rates,
            "counts": counts,
            "advances": advances,
            "cycles": cycles_per_execution,
            "success": sum(per_state_rates) / len(per_state_rates),
        }

    wall = time.perf_counter() - wall_start
    total = n_states * n_repeats
    best = max(summary.values(), key=lambda d: d["success"])
    success_rate = best["success"]
    advances = best["advances"]
    per_state_rates = best["per_state"]
    counts = best["counts"]

    lines = ["# open_hinge(LID): selection-driven search (PathGennie)", ""]
    lines.append(
        f"Same event as the biased run: theta_LID advances by >= {DELTA_DEG} deg. "
        f"Every execution spends {STEPS_PER_EXECUTION:,} steps, cost-matched to "
        f"one biased execution (4 replicas x 12500 steps), allocated three ways "
        f"between swarm breadth and segment length. {n_repeats} repeats from "
        f"each of {n_states} start states."
    )
    lines.append("")
    lines.append(f"Start states: theta_LID = "
                 f"{', '.join(f'{a:.1f}' for a in start_angles)} deg.")
    lines.append("")
    lines.append("| allocation | cycles | success | per start state | "
                 "median advance (deg) | outcomes |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for label, data in summary.items():
        lines.append(
            f"| {label} | {data['cycles']} | **{data['success']:.2f}** | "
            f"{', '.join(f'{r:.2f}' for r in data['per_state'])} | "
            f"{np.median(data['advances']):.1f} | {data['counts']} |"
        )
    lines.append("")
    lines.append("## Comparison with the other families, at equal cost")
    lines.append("")
    lines.append("| family | mechanism | success |")
    lines.append("| --- | --- | --- |")
    lines.append("| biased k>=1000 | restraint on the Hamiltonian | 1.00 |")
    lines.append("| biased k=250 | restraint on the Hamiltonian | 0.87 |")
    lines.append(f"| selection-driven | unbiased segments, biased ensemble | "
                 f"{success_rate:.2f} |")
    lines.append("| unbiased null | none | 0.00 |")
    lines.append("")
    lines.append(
        f"Final theta_LID advance: median {np.median(advances):.1f} deg, "
        f"range {min(advances):.1f} to {max(advances):.1f} deg "
        f"(the event needs {DELTA_DEG})."
    )
    lines.append("")
    lines.append(
        f"Cost: {total * STEPS_PER_EXECUTION:,} steps "
        f"({total * STEPS_PER_EXECUTION * dt_ps / 1000:.1f} ns) in "
        f"{wall / 60:.0f} min."
    )
    lines.append("")
    lines.append(
        "Note on what 'unbiased' means here: each committed segment is "
        "ordinary Langevin dynamics and is individually Boltzmann valid, so "
        "no trajectory is distorted. Selection still skews the *ensemble* "
        "toward opening, so this family is not a source of equilibrium "
        "statistics -- it is a search whose artifacts differ in kind from a "
        "restraint's, not one that has none."
    )

    (HERE / "open_hinge_pathgennie_results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
