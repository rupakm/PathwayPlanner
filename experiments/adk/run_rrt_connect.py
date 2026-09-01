"""RRT-Connect between the AdK endpoints, in the (theta_LID, theta_NMP) plane.

Why this, after the greedy driver returned 0/90
-----------------------------------------------
PathGennie's own rrt.py says it plainly: "The greedy driver follows a
monotone progress metric, so it cannot backtrack, change direction, or
move orthogonally to the CV." That is exactly the stall the probes
measured -- the anchor ratchets into the tail of theta_LID's
distribution and then no short trial can beat it. So the earlier result
is a statement about `PathGennieDriver`, not about selection-driven
search in general, and this run tests the strategy that module exists to
provide.

RRT-Connect is unusually well matched to this system. Both endpoints are
experimental structures (1AKE closed, 4AKE open), both are built and
equilibrated here, and their topologies are atom-for-atom identical, so
one OpenMM System serves both. Growing a tree from each end and linking
them in the middle is a different proposition from pushing uphill from
one end: neither tree has to cross the barrier alone.

The CV plane
------------
(theta_LID, theta_NMP) rather than a single coordinate, because the open
mechanistic question for adenylate kinase is *ordering* -- whether the
LID closes before the NMP domain or after -- and in this plane those are
literally different routes across the same square. A tree is free to move
in either coordinate, which a monotone scalar metric cannot do.

Success here is a connected path in CV space, not a Boltzmann-weighted
transition path ensemble. The nodes are joined by short unbiased
segments, so each edge is dynamically feasible, but the path's weight is
not the equilibrium one: this proposes a route, and reweighting it (WE
seeded from the nodes, or umbrella sampling along it) is a separate step.

Usage:
  PYTHONPATH=<burst-api>:<pathgennie>:<pathwayplanner>:<here> \
      python run_rrt_connect.py [--fast]
Writes rrt_connect_results.md next to this file.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

import domains

HERE = Path(__file__).resolve().parent
STRUCTURES = HERE / "structures"
TOPOLOGY = STRUCTURES / "adk_open_topology.pdb"
SYSTEM_XML = STRUCTURES / "adk_open_system.xml"
BUILD_JSON = STRUCTURES / "adk_open_build.json"
OPEN_EQUIL = STRUCTURES / "adk_open_equilibrated.pdb"
CLOSED_EQUIL = STRUCTURES / "adk_closed_equilibrated.pdb"

TEMPERATURE_K = 300.0
# Segment lengths in integrator steps: 5 ps at 4 fs, matching the budget unit
# used for the greedy-driver comparison.
TAU1 = TAU2 = 1250
# Bounds of the (theta_LID, theta_NMP) plane, generous around the endpoints
# (closed 106/44, open 147/73 degrees).
LOWER = [90.0, 30.0]
UPPER = [165.0, 95.0]


def positions(pdb: Path) -> np.ndarray:
    import MDAnalysis as mda

    return mda.Universe(str(pdb)).atoms.positions.astype(float)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--platform", default="OpenCL")
    args = parser.parse_args()

    from openmm import LangevinMiddleIntegrator, Platform, XmlSerializer
    from openmm.app import PDBFile, Simulation
    from openmm.unit import kelvin, picosecond, picoseconds
    from pathgennie.backends.openmm.engine import OpenMMEngine
    from pathgennie.search.rrt import rrt_connect

    n_expand = 3 if args.fast else 4
    max_iter = 12 if args.fast else 40
    connect_tol = 12.0     # degrees in the (theta_LID, theta_NMP) plane

    dt_ps = json.loads(BUILD_JSON.read_text())["dt_ps"]
    system = XmlSerializer.deserialize(SYSTEM_XML.read_text())
    pdb = PDBFile(str(TOPOLOGY))
    integrator = LangevinMiddleIntegrator(
        TEMPERATURE_K * kelvin, 1.0 / picosecond, dt_ps * picoseconds
    )
    try:
        platform = Platform.getPlatformByName(args.platform)
        simulation = Simulation(pdb.topology, system, integrator, platform)
    except Exception:  # noqa: BLE001 - platform availability is environmental
        simulation = Simulation(pdb.topology, system, integrator)
    simulation.context.setPositions(pdb.positions)
    engine = OpenMMEngine(simulation, temperature=TEMPERATURE_K, n_workers=1)

    theta_lid = domains.lid_core_angle(TOPOLOGY)
    theta_nmp = domains.nmp_core_angle(TOPOLOGY)
    to_open = domains.rmsd_to_reference(TOPOLOGY, domains.OPEN_PDB)
    to_closed = domains.rmsd_to_reference(TOPOLOGY, domains.CLOSED_PDB)

    def cv_fn(coords: np.ndarray) -> np.ndarray:
        return np.array(
            [float(theta_lid.project(coords)[0]), float(theta_nmp.project(coords)[0])]
        )

    start = engine.create_handle(positions(CLOSED_EQUIL))
    goal = engine.create_handle(positions(OPEN_EQUIL))
    cv_start, cv_goal = cv_fn(engine.get_coords(start)), cv_fn(engine.get_coords(goal))

    wall = time.perf_counter()
    result = rrt_connect(
        engine, cv_fn, start, goal,
        lower=LOWER, upper=UPPER, tau1=TAU1, tau2=TAU2,
        n_expand=n_expand, seed=20260901,
        max_iter=max_iter, connect_tol=connect_tol,
    )
    elapsed = time.perf_counter() - wall

    path_cvs = [n.cv.tolist() for n in result.path]
    steps = result.tree_size * (n_expand * TAU1 + TAU2)

    lines = ["# RRT-Connect between the AdK endpoints", ""]
    lines.append(
        f"Trees grown from the equilibrated closed structure at "
        f"(theta_LID, theta_NMP) = ({cv_start[0]:.1f}, {cv_start[1]:.1f}) deg and "
        f"the equilibrated open structure at ({cv_goal[0]:.1f}, {cv_goal[1]:.1f}) "
        f"deg, linked when within {connect_tol:.0f} deg. Segments of "
        f"{TAU1 * dt_ps:.0f} ps, {n_expand} trials per extension, at most "
        f"{max_iter} iterations."
    )
    lines.append("")
    lines.append(f"- Connected: **{'yes' if result.success else 'no'}**")
    lines.append(f"- Nodes explored: {result.tree_size}")
    lines.append(f"- Path length: {len(result.path)} nodes")
    lines.append(f"- Approximate cost: {steps:,} integrator steps "
                 f"({steps * dt_ps / 1000:.1f} ns) in {elapsed / 60:.0f} min")
    lines.append("")

    if path_cvs:
        lines.append("## Path through the (theta_LID, theta_NMP) plane")
        lines.append("")
        lines.append("| node | theta_LID | theta_NMP | RMSD open | RMSD closed |")
        lines.append("| --- | --- | --- | --- | --- |")
        for index, node in enumerate(result.path):
            coords = engine.get_coords(node.handle)
            lines.append(
                f"| {index} | {node.cv[0]:.1f} | {node.cv[1]:.1f} | "
                f"{float(to_open.project(coords)[0]):.2f} A | "
                f"{float(to_closed.project(coords)[0]):.2f} A |"
            )
        lines.append("")
        # Which domain moves first is the open mechanistic question for AdK.
        lid = np.array([c[0] for c in path_cvs])
        nmp = np.array([c[1] for c in path_cvs])
        lid_frac = (lid - lid[0]) / (lid[-1] - lid[0]) if lid[-1] != lid[0] else lid * 0
        nmp_frac = (nmp - nmp[0]) / (nmp[-1] - nmp[0]) if nmp[-1] != nmp[0] else nmp * 0
        midpoint = len(path_cvs) // 2
        lines.append(
            f"At the path midpoint the LID has covered {lid_frac[midpoint]:.0%} of "
            f"its total change and the NMP domain {nmp_frac[midpoint]:.0%}. A "
            f"path where one runs well ahead of the other is an ordered "
            f"mechanism; comparable fractions mean the domains move together. "
            f"One path is an anecdote -- distinguishing mechanisms needs the "
            f"route distribution over many runs."
        )
    else:
        lines.append("No path was returned; the trees did not link within the "
                     "iteration budget.")

    (HERE / "rrt_connect_results.md").write_text("\n".join(lines) + "\n")
    (HERE / "rrt_connect_path.json").write_text(
        json.dumps({"start_cv": cv_start.tolist(), "goal_cv": cv_goal.tolist(),
                    "success": bool(result.success), "tree_size": result.tree_size,
                    "path_cv": path_cvs}, indent=2) + "\n"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
