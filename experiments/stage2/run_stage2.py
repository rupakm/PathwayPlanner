"""Stage 2 evaluation: alanine dipeptide through the Trails-MD adapter (PLAN.md).

Verifies that the Stage 1 language semantics transfer to real MD
unchanged: the same Action/classifier/contract/estimator code, with the
toy backend replaced by TrailsMDBackend (trails_md.bursts, branch
burst-api) and the CV replaced by the periodic (phi, psi) dihedral
space. Only this script and the backend adapter know about trails_md.

System: ACE-ALA-NME (22 atoms), vacuum Amber14, OpenMM CPU platform —
the self-contained example shipped with Trails-MD.

Phases:
  A. Equilibrate: unbiased bursts from the extended start structure;
     the settled basin defines A. B is C7ax at (phi, psi) = (72, -65) deg.
  B. `cross` action, two independent batches: harmonic torsion bias on
     phi toward the C7ax value; ChannelClassifier on the periodic
     (phi, psi) space decides Success/Partial/Failure.
  C. Metrics 1-2: JS divergence between batches; contract calibration.
  D. Committor rollout validation: from success successors, unbiased
     bursts; empirical q_hat = P(reach B before A). Gate: median > 0.5.
  E. Relaxation persistence: RelaxAction on success successors.

Run:  PYTHONPATH=<trails-md-burst-api>:<pathwayplanner> python run_stage2.py [--fast]
Writes results.md next to this file. Trajectories land in runs/ (gitignored).
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from pathwayplanner import Budget, Implementation, Outcome, State
from pathwayplanner.actions.base import Action, ActionResult
from pathwayplanner.actions.relax import RelaxAction
from pathwayplanner.backends.trailsmd import TrailsMDBackend
from pathwayplanner.cv import PeriodicCV
from pathwayplanner.evaluation import estimate_outcomes
from pathwayplanner.outcomes import ChannelClassifier
from pathwayplanner.recipes import Lift, RecipeContract

from trails_md.bursts import BiasSpec, BurstSystem

HERE = Path(__file__).parent
EXAMPLE = Path("/Users/rupak/Code/Trails-MD/examples/alanine_dipeptide")

# Dihedral atom indices in structure.pdb (0-based), verified via MDAnalysis
# selections: phi = C(ACE)-N-CA-C, psi = N-CA-C-N(NME).
PHI_ATOMS = (4, 6, 8, 14)
PSI_ATOMS = (6, 8, 14, 16)

B_CENTER = np.array([72.0, -65.0])  # C7ax
BASIN_RADIUS = 40.0  # degrees, periodic distance in (phi, psi)


def dihedral_deg(coords: np.ndarray, atoms: tuple[int, int, int, int]) -> float:
    """Dihedral angle in degrees from (n_atoms, 3) coordinates (no PBC)."""
    p0, p1, p2, p3 = (np.asarray(coords, dtype=float)[i] for i in atoms)
    b0, b1, b2 = p0 - p1, p2 - p1, p3 - p2
    b1n = b1 / np.linalg.norm(b1)
    v = b0 - np.dot(b0, b1n) * b1n
    w = b2 - np.dot(b2, b1n) * b1n
    x = np.dot(v, w)
    y = np.dot(np.cross(b1n, v), w)
    return float(np.degrees(np.arctan2(y, x)))


def phi_psi(coords: np.ndarray) -> np.ndarray:
    return np.array([dihedral_deg(coords, PHI_ATOMS), dihedral_deg(coords, PSI_ATOMS)])


SPACE = PeriodicCV(phi_psi, periods=[360.0, 360.0])


def in_disc(center):
    return lambda cv: SPACE.distance(cv, center) < BASIN_RADIUS


class CrossAction(Action):
    """Rotate phi into the C7ax basin under a harmonic torsion bias."""

    name = "cross_to_c7ax"

    def __init__(self, a_center: np.ndarray, k: float, n_steps: int, n_replicas: int):
        self.a_center = a_center
        self.k = k
        self.n_steps = n_steps
        self.n_replicas = n_replicas

    def precondition(self, state: State) -> bool:
        return not in_disc(B_CENTER)(SPACE.project(state.features))

    def propose(self, state: State):
        bias = BiasSpec(
            cv="torsion", form="harmonic", k=self.k,
            target=float(np.radians(B_CENTER[0])), atoms=PHI_ATOMS,
        )
        return [
            Implementation(
                cv=SPACE, bias=bias, n_steps=self.n_steps, n_replicas=self.n_replicas
            )
        ]

    def evaluate(self, initial_state, trajectories) -> ActionResult:
        classifier = ChannelClassifier(
            target=in_disc(B_CENTER),
            alternatives={},
            space=SPACE,
            target_point=B_CENTER,
            delta=SPACE.distance(SPACE.project(initial_state.features), B_CENTER),
        )
        return classifier.classify(initial_state, trajectories)


def first_hit(trajectory, a_center) -> str | None:
    """First basin reached along a trajectory: 'A', 'B', or None."""
    for frame in trajectory.frames:
        cv = SPACE.project(frame)
        if in_disc(a_center)(cv):
            return "A"
        if in_disc(B_CENTER)(cv):
            return "B"
    return None


def make_backend(system, workdir: Path, seed: int) -> TrailsMDBackend:
    return TrailsMDBackend(
        system=system, space=SPACE, workdir=workdir, stride=100, base_seed=seed
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    n_batch = 3 if args.fast else 12
    n_replicas = 2 if args.fast else 4
    n_steps = 2000 if args.fast else 10000  # 4 ps / 20 ps at dt=0.002
    n_rollout_states = 2 if args.fast else 6
    n_rollouts = 3 if args.fast else 6
    # Moderate bias: strong enough to drive the phi rotation within a burst
    # in most executions, weak enough to leave outcome heterogeneity for the
    # reproducibility and calibration metrics to measure.
    bias_k = 40.0  # kJ/mol/rad^2

    runs = HERE / "runs"
    if runs.exists():
        shutil.rmtree(runs)
    runs.mkdir(parents=True)

    system = BurstSystem(
        engine_name="openmm",
        engine_kwargs={"platform_name": "CPU", "temperature": 300.0, "dt": 0.002},
        conf=EXAMPLE / "structure.pdb",
        top=EXAMPLE / "structure.pdb",
        system_file=EXAMPLE / "system.py",
    )
    budget = Budget(max_steps=10**9)
    lines = ["# Stage 2 results (alanine dipeptide, vacuum Amber14, OpenMM CPU)", ""]
    lines.append(
        f"Parameters: n_steps={n_steps} (dt=2 fs), replicas={n_replicas}, "
        f"batches of {n_batch}, bias k={bias_k} kJ/mol/rad^2 on phi, "
        f"basin radius {BASIN_RADIUS} deg, B=C7ax {tuple(B_CENTER)}."
    )
    lines.append("")
    wall_start = time.perf_counter()

    # -- Phase A: equilibrate ------------------------------------------------
    import MDAnalysis as mda

    start_coords = mda.Universe(str(EXAMPLE / "structure.pdb")).atoms.positions
    backend_eq = make_backend(system, runs / "equilibrate", seed=100)
    eq_state = State(configuration=EXAMPLE / "structure.pdb", features=start_coords)
    eq_trajs = backend_eq.run_bursts(
        [eq_state],
        Implementation(cv=SPACE, bias=None, n_steps=n_steps, n_replicas=2),
        budget,
    )
    final_frame = eq_trajs[0].frames[-1]
    a_center = SPACE.project(final_frame)
    a_state = State(
        configuration=eq_trajs[0].configurations[-1], features=final_frame
    )
    lines.append("## A. Equilibration")
    lines.append(
        f"- Start (phi, psi) = {np.round(phi_psi(start_coords), 1)}; settled "
        f"A basin center = {np.round(a_center, 1)} deg."
    )
    lines.append("")

    # -- Phase B/C: cross batches, reproducibility, calibration --------------
    def cross_step(batch: int):
        backend = make_backend(system, runs / f"cross_batch{batch}", seed=1000 * batch)
        action = CrossAction(a_center, k=bias_k, n_steps=n_steps, n_replicas=n_replicas)
        return Lift(lambda s: action.run(s, backend, budget))

    contract = RecipeContract()
    model_1 = estimate_outcomes(cross_step(1), a_state, n=n_batch, contract=contract)
    model_2 = estimate_outcomes(cross_step(2), a_state, n=n_batch)
    js = model_1.js_divergence(model_2)
    rate_1 = contract.success_rate() or 0.0
    rate_2 = model_2.probs().get(Outcome.SUCCESS, 0.0)
    calib_err = abs(rate_1 - rate_2)
    lines.append("## B/C. Reproducibility and calibration (cross action)")
    lines.append(f"- Batch 1 outcomes: { {o.value: c for o, c in model_1.counts.items()} }")
    lines.append(f"- Batch 2 outcomes: { {o.value: c for o, c in model_2.counts.items()} }")
    lines.append(f"- JS divergence: **{js:.4f}** (gate: < 0.1) — "
                 f"{'PASS' if js < 0.1 else 'FAIL'}")
    lines.append(f"- Calibration error: **{calib_err:.3f}** (gate: < 0.2) — "
                 f"{'PASS' if calib_err < 0.2 else 'FAIL'}")
    lines.append("")
    repro_pass, calib_pass = js < 0.1, calib_err < 0.2

    successors = [s for s in model_1.successors + model_2.successors
                  if in_disc(B_CENTER)(SPACE.project(s.features))]

    # -- Phase D: committor rollout validation -------------------------------
    lines.append("## D. Committor rollout validation of success labels")
    q_hats = []
    tested = successors[:n_rollout_states]
    for i, succ in enumerate(tested):
        backend = make_backend(system, runs / f"rollout_{i}", seed=7000 + i)
        trajs = backend.run_bursts(
            [succ],
            Implementation(cv=SPACE, bias=None, n_steps=n_steps, n_replicas=n_rollouts),
            budget,
        )
        hits = [first_hit(t, a_center) for t in trajs]
        n_a, n_b = hits.count("A"), hits.count("B")
        if n_a + n_b:
            q_hats.append(n_b / (n_a + n_b))
        lines.append(f"- Successor {i}: hits B={n_b}, A={n_a}, "
                     f"unresolved={len(hits) - n_a - n_b}")
    committor_pass = bool(q_hats) and float(np.median(q_hats)) > 0.5
    lines.append(f"- q_hat per successor: {[round(q, 2) for q in q_hats]}; "
                 f"median {np.median(q_hats) if q_hats else float('nan'):.2f} "
                 f"(gate: > 0.5) — {'PASS' if committor_pass else 'FAIL'}")
    lines.append("")

    # -- Phase E: relaxation persistence -------------------------------------
    lines.append("## E. Relaxation persistence")
    persist = 0
    for i, succ in enumerate(tested):
        backend = make_backend(system, runs / f"relax_{i}", seed=9000 + i)
        # Successors are first-entry frames at the basin edge; settling toward
        # the center is legitimate motion of up to 2*radius, while a return to
        # A is ~180 deg away. The tolerance must separate the two.
        relax = RelaxAction(space=SPACE, tolerance=2 * BASIN_RADIUS,
                            n_steps=n_steps, n_replicas=n_replicas)
        result = relax.run(succ, backend, budget)
        persist += result.outcome is Outcome.SUCCESS
    frac = persist / len(tested) if tested else 0.0
    relax_pass = frac >= 0.5
    lines.append(f"- {persist}/{len(tested)} success successors stable under "
                 f"relax (gate: >= 0.5) — {'PASS' if relax_pass else 'FAIL'}")
    lines.append("")

    # -- Cost -----------------------------------------------------------------
    wall = time.perf_counter() - wall_start
    total_steps = (
        model_1.total_cost + model_2.total_cost
        + len(tested) * n_rollouts * n_steps + len(tested) * n_replicas * n_steps
        + 2 * n_steps
    )
    per_exec = model_1.total_cost / max(n_batch, 1)
    lines.append("## Cost")
    lines.append(f"- Total integrator steps: {int(total_steps):,}; wall-clock "
                 f"{wall:.0f} s.")
    lines.append(f"- Per cross execution: {int(per_exec):,} steps "
                 f"({per_exec * 2e-6:.3f} ns).")
    lines.append("")

    all_pass = repro_pass and calib_pass and committor_pass and relax_pass
    lines.append(f"## Stage 2 gate: {'PASS' if all_pass else 'FAIL'}")
    (HERE / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
