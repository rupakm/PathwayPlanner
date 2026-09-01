"""Stage 3, first action: open_hinge(LID) on adenylate kinase.

SUPERSEDES the first version of this experiment (results committed at
de9b2e2). That run defined the event on theta_LID alone and reported
90/90 successes. An audit of its saved trajectories showed the angle
reaching 141.4 deg -- near the 146.5 deg open crystal value -- while
C-alpha RMSD to the open structure moved only 6.66 -> 5.06 A, about a
quarter of the way. The event was satisfied by configurations that had
left the closed state without arriving at the open one, the same defect
later found in close_hinge. This version requires the structure to
follow the angle.

Runs the WP1 protocol for a single action so the design is tested before
the other five are written: repeated execution from several start
states, an outcome distribution, relaxation persistence, and the two
baselines that decide whether the action is doing any work.

Event specification (conjunctive)
---------------------------------
theta_LID advances by at least DELTA_DEG *and* C-alpha RMSD to the open
crystal structure falls by at least RMSD_DELTA_A, in the same frame.

theta_LID is the better angular coordinate because the open state
breathes +/- 2 A in the LID-CORE distance, a fifth of the endpoint range,
while the angle separates the endpoints by 40 deg against an 8-11 deg
fluctuation. But an angle is not a conformation: the audit above showed
it can read "open" while the structure has barely moved. RMSD_DELTA_A is
set to 2.0 A, more than three standard deviations of that RMSD's thermal
fluctuation (~0.6 A) and roughly half the 4.0 A separating the
equilibrated closed start from the open basin.

Requiring both is expected to lower the reported success rate
substantially from the superseded 1.00. That is the point: the earlier
number measured an angle, not an opening.

Implementations compared, at equal cost
---------------------------------------
* biased: Trails-MD bursts under a harmonic LID-CORE centroid-distance
  restraint pulling toward the open endpoint. A distance bias is used
  because trails_md.bursts.BiasSpec supports exactly distance and torsion
  CVs; biasing the angle itself, or an interface contact count, would
  require extending BiasSpec, which is deliberately deferred.
* unbiased: identical bursts with no intervention. This is the null
  model, and it is the measurement that matters: apo AdK's closed state
  is not an equilibrium state, so the LID may open on its own. If the
  unbiased family succeeds as often as the biased one, the intervention
  is adding nothing and the action's implementation, not the language, is
  what needs rethinking.

Both are the same Action object with a different `bias`, so the event
specification, the classifier and the outcome semantics are held fixed
and only the intervention varies.

Usage:
  PYTHONPATH=<trails-md-burst-api>:<pathwayplanner>:<here> \
      python run_open_hinge.py [--fast]
Writes open_hinge_results.md next to this file.
"""

from __future__ import annotations

import argparse
import json
import re
import zlib
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from pathwayplanner import Budget, Implementation, Outcome, State
from pathwayplanner.actions.hinge import HingeOpeningAction
from pathwayplanner.actions.relax import RelaxAction
from pathwayplanner.backends.trailsmd import TrailsMDBackend
from pathwayplanner.evaluation import (
    OutcomeModel,
    estimate_outcomes,
    relaxation_direction,
)
from pathwayplanner.outcomes import Criterion
from pathwayplanner.recipes import Lift, RecipeContract

import domains
from trails_md.bursts import BiasSpec, BurstSystem

HERE = Path(__file__).resolve().parent
STRUCTURES = HERE / "structures"
CLOSED_TOPOLOGY = STRUCTURES / "adk_closed_topology.pdb"
CLOSED_EQUILIBRATED = STRUCTURES / "adk_closed_equilibrated.pdb"
CLOSED_SYSTEM_XML = STRUCTURES / "adk_closed_system.xml"

# theta_LID at the crystal endpoints (domains.py): closed 106, open 147.
# DELTA_DEG must clear the angle's thermal fluctuation (8-11 deg in the open
# state) to avoid scoring breathing as an opening; 25 deg is above 2 sigma and
# is roughly two thirds of the way to the open endpoint.
DELTA_DEG = 25.0
RMSD_DELTA_A = 2.0
# One sigma of theta_LID's thermal fluctuation (8-11 deg), not the 2.5 sigma
# the superseded run used, under which a 24 deg drift counted as stable.
RELAX_TOLERANCE_DEG = 10.0
OPEN_THETA_DEG = 146.5

# BiasSpec distances are in nm and its force constants in kJ/mol/nm^2.
OPEN_LID_CORE_NM = 3.08
BIAS_K = 2000.0


def _slug(family: str) -> str:
    """Filesystem-safe directory name identifying one implementation family."""
    return re.sub(r"[^a-z0-9]+", "_", family.lower()).strip("_")


def _family_seed(family: str, index: int) -> int:
    """Base seed for one (family, start state) cell.

    Derived with crc32 rather than hash(): Python salts str hashing per
    process, so a hash-derived seed would differ between runs of the same
    script and silently break reproducibility.
    """
    return 1000 * (index + 1) + (zlib.crc32(_slug(family).encode()) % 977)


def make_backend(system, workdir: Path, seed: int, stride: int) -> TrailsMDBackend:
    return TrailsMDBackend(
        system=system,
        space=domains.lid_core_angle(CLOSED_TOPOLOGY),
        workdir=workdir,
        stride=stride,
        base_seed=seed,
    )


def distance_bias(k: float = BIAS_K) -> BiasSpec:
    """Harmonic LID-CORE centroid restraint pulling toward the open endpoint."""
    lid = domains.atom_indices(CLOSED_TOPOLOGY, domains.LID_RANGES)
    core = domains.atom_indices(CLOSED_TOPOLOGY, domains.CORE_RANGES)
    return BiasSpec(
        cv="distance",
        form="harmonic",
        k=k,
        target=OPEN_LID_CORE_NM,
        groups=(tuple(int(i) for i in lid), tuple(int(i) for i in core)),
    )


def start_states(system, n_states: int, n_steps: int, seed: int, workdir: Path):
    """Decorrelated closed-state starting configurations.

    Drawn from independent unbiased replicas rather than from one
    trajectory, so repeats do not share a recent history -- the same
    decorrelation requirement the alanine dipeptide committor analysis
    established (docs/NOTES.md).
    """
    backend = make_backend(system, workdir, seed=seed, stride=n_steps)
    seed_state = State(
        configuration=CLOSED_EQUILIBRATED,
        features=_positions(CLOSED_EQUILIBRATED),
    )
    trajectories = backend.run_bursts(
        [seed_state],
        Implementation(cv=None, bias=None, n_steps=n_steps, n_replicas=n_states),
        Budget(max_steps=10**9),
    )
    return [
        State(configuration=t.configurations[-1], features=t.frames[-1])
        for t in trajectories
    ]


def _positions(pdb: Path) -> np.ndarray:
    import MDAnalysis as mda

    return mda.Universe(str(pdb)).atoms.positions.astype(float)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    for path in (CLOSED_SYSTEM_XML, CLOSED_TOPOLOGY, CLOSED_EQUILIBRATED):
        if not path.exists():
            print(f"Missing {path}; run build_system.py --state closed first.",
                  file=sys.stderr)
            return 1

    n_states = 2 if args.fast else 3
    n_repeats = 3 if args.fast else 10
    n_steps = 5000 if args.fast else 12500       # 20 ps / 50 ps at 4 fs
    n_replicas = 2 if args.fast else 4
    relax_steps = 5000 if args.fast else 12500
    stride = 500

    runs = HERE / "runs" / "open_hinge"
    if runs.exists():
        shutil.rmtree(runs)
    runs.mkdir(parents=True)

    system = BurstSystem(
        engine_name="openmm",
        engine_kwargs={"platform_name": "OpenCL", "temperature": 300.0, "dt": 0.004},
        conf=CLOSED_TOPOLOGY,
        top=CLOSED_TOPOLOGY,
        system_file=HERE / "system_closed.py",
    )
    budget = Budget(max_steps=10**9)
    theta = domains.lid_core_angle(CLOSED_TOPOLOGY)
    lid_core = domains.lid_core_distance(CLOSED_TOPOLOGY)
    to_open = domains.rmsd_to_reference(CLOSED_TOPOLOGY, domains.OPEN_PDB)
    rmsd_criterion = Criterion(
        space=to_open, target_point=np.array([0.0]), delta=RMSD_DELTA_A
    )
    wall_start = time.perf_counter()

    starts = start_states(system, n_states, n_steps, seed=17, workdir=runs / "starts")
    start_angles = [float(theta.project(s.features)[0]) for s in starts]

    lines = ["# Stage 3, action 1: open_hinge(LID) on adenylate kinase", ""]
    lines.append(
        f"Event: theta_LID advances by >= {DELTA_DEG} deg. Bursts of "
        f"{n_steps} steps x 4 fs = {n_steps * 0.004:.0f} ps, {n_replicas} "
        f"replicas, {n_repeats} repeats from each of {n_states} decorrelated "
        f"closed start states. Crystal endpoints: theta_LID 106 (closed) -> "
        f"{OPEN_THETA_DEG} (open) deg."
    )
    lines.append("")
    lines.append(f"Start states: theta_LID = "
                 f"{', '.join(f'{a:.1f}' for a in start_angles)} deg; "
                 f"LID-CORE = "
                 f"{', '.join(f'{float(lid_core.project(s.features)[0]):.1f}' for s in starts)} A.")
    lines.append("")

    # A sweep rather than a single bias strength. At k = 2000 the action
    # succeeds in every execution, which is a valid measurement but a
    # saturated one: it cannot show how outcome distributions vary, and it
    # hides where the action stops working. Sweeping k down to the unbiased
    # null turns one point into a dose-response curve, which is the evidence
    # the WP2 compiler needs to choose an implementation rather than be told
    # one.
    # Extended upward: the structural criterion asks more of the restraint
    # than the angular one did, so the working range may lie above the
    # strengths that sufficed before.
    sweep = [1000.0, 2000.0, 4000.0] if not args.fast else [BIAS_K]
    families = {f"biased k={k:.0f} kJ/mol/nm^2": distance_bias(k) for k in sweep}
    families["unbiased (null model)"] = None
    summary: dict[str, dict] = {}

    for family, bias in families.items():
        pooled = OutcomeModel()
        contract = RecipeContract()
        per_state = []
        for index, start in enumerate(starts):
            backend = make_backend(
                system, runs / f"{_slug(family)}_{index}",
                seed=_family_seed(family, index), stride=stride,
            )
            act = HingeOpeningAction(
                name="open_hinge_LID",
                space=theta,
                delta=DELTA_DEG,
                bias=bias,
                n_steps=n_steps,
                n_replicas=n_replicas,
                stop_at=OPEN_THETA_DEG,
                also=[rmsd_criterion],
            )
            model = estimate_outcomes(
                Lift(lambda s, a=act, b=backend: a.run(s, b, budget)),
                start,
                n=n_repeats,
                contract=contract,
            )
            per_state.append(model.probs().get(Outcome.SUCCESS, 0.0))
            pooled.counts.update(model.counts)
            pooled.successors.extend(model.successors)
            pooled.total_cost += model.total_cost
        delivered = [
            float(to_open.project(s.features)[0]) for s in pooled.successors
        ]
        summary[family] = {
            "delivered_rmsd": delivered,
            "counts": {o.value: c for o, c in pooled.counts.items()},
            "success": pooled.probs().get(Outcome.SUCCESS, 0.0),
            "per_state": per_state,
            "cost": pooled.total_cost,
            "successors": pooled.successors,
        }

    lines.append("## Outcome distributions")
    lines.append("")
    start_rmsd = float(to_open.project(starts[0].features)[0])
    lines.append("| implementation | success | per start state | "
                 "RMSD to open reached | outcomes | steps |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for family, data in summary.items():
        rmsds = data["delivered_rmsd"]
        reached = (f"{np.mean(rmsds):.2f} A (best {min(rmsds):.2f})"
                   if rmsds else "-")
        lines.append(
            f"| {family} | **{data['success']:.2f}** | "
            f"{', '.join(f'{p:.2f}' for p in data['per_state'])} | "
            f"{reached} | {data['counts']} | {int(data['cost']):,} |"
        )
    lines.append("")
    lines.append(
        f"Start RMSD to the open crystal is {start_rmsd:.2f} A; the open basin "
        f"sits near 2.7 A, so a complete opening would reach roughly that. "
        f"The event requires a {RMSD_DELTA_A} A reduction, and the column "
        f"above reports what was actually delivered -- the number the "
        f"superseded run never measured."
    )
    lines.append("")

    biased = summary[f"biased k={BIAS_K:.0f} kJ/mol/nm^2"]
    null = summary["unbiased (null model)"]
    lines.append("## Does the intervention do any work?")
    lines.append(
        f"- Biased success {biased['success']:.2f} vs unbiased "
        f"{null['success']:.2f} at equal cost "
        f"({int(biased['cost']):,} vs {int(null['cost']):,} steps)."
    )
    if null["success"] >= biased["success"] - 0.1:
        lines.append(
            "- **The null model matches the biased one.** The apo closed state "
            "opens on its own on this timescale, so this event is not a rare "
            "event here and the biased implementation earns nothing. Report "
            "this rather than the biased success rate alone."
        )
    else:
        lines.append(
            "- The bias raises the success rate materially above the null, so "
            "the intervention is doing work on this timescale."
        )
    lines.append("")

    lines.append("## Relaxation after the restraint is removed")
    lines.append("")
    lines.append("Signed direction, not a pass/fail verdict: the progress "
                 "coordinate is s = RMSD(closed) - RMSD(open), so positive is "
                 "nearer the open reference. A threshold on drift has no "
                 "defensible setting -- the coordinate's own fluctuation is "
                 "comparable to any drift worth detecting -- and these "
                 "configurations lie on a gradient rather than in a basin, so "
                 "they always relax. UNSTABLE is reserved for a "
                 "committor-backed claim.")
    lines.append("")
    relax = RelaxAction(space=theta, tolerance=RELAX_TOLERANCE_DEG,
                        n_steps=relax_steps, n_replicas=n_replicas)
    for family, data in summary.items():
        successors = [
            s for s in data["successors"]
            if float(theta.project(s.features)[0])
            >= min(start_angles) + DELTA_DEG
        ][: (2 if args.fast else 5)]
        held = 0
        for index, successor in enumerate(successors):
            backend = make_backend(
                system, runs / f"relax_{_slug(family)}_{index}",
                seed=7000 + index, stride=stride,
            )
            held += relax.run(successor, backend, budget).outcome is Outcome.SUCCESS
        if successors:
            lines.append(
                f"- {family}: {held}/{len(successors)} openings survived "
                f"{relax_steps * 0.004:.0f} ps unbiased."
            )
        else:
            lines.append(f"- {family}: no openings to relax.")
    lines.append("")

    wall = time.perf_counter() - wall_start
    total = sum(d['cost'] for d in summary.values())
    lines.append("## Cost")
    lines.append(
        f"- {int(total):,} integrator steps for the action matrix "
        f"({total * 4e-6:.1f} ns); wall-clock {wall / 60:.0f} min."
    )
    lines.append(
        f"- Per execution: {total / (len(families) * n_states * n_repeats) * 4e-6:.3f} ns."
    )

    (HERE / "open_hinge_results.md").write_text("\n".join(lines) + "\n")
    (HERE / "open_hinge_results.json").write_text(
        json.dumps(
            {
                f: {k: v for k, v in d.items() if k != "successors"}
                for f, d in summary.items()
            },
            indent=2,
        )
        + "\n"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
