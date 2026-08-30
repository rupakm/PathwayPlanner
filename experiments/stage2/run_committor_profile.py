"""Committor profile across the alanine dipeptide barrier (Stage 2 follow-up).

The Stage 2 evaluation validated success labels by rolling out from
first-entry frames, which sit inside the target basin and therefore have
q = 1 by construction. This script replaces that weak check with a
committor profile measured on transition-region frames.

Method. Biased cross bursts supply configurations spanning the phi range
between C7eq and C7ax; frames are binned by phi, and from a
representative of each bin unbiased rollouts estimate

    q_hat(x) = P(reach B before A | start at x, unbiased dynamics).

Sampling the starting configurations from biased trajectories is
legitimate: the committor is a property of a configuration under the
unbiased dynamics, independent of how that configuration was generated.
Only the rollouts must be unbiased, and they are.

Two things are checked:
  1. Monotonicity — q_hat increases with phi across the barrier, i.e. the
     profile is a sigmoid from ~0 in the reactant basin to ~1 in the
     product basin, rather than a step at the basin boundary.
  2. Label validity — frames the ChannelClassifier would call SUCCESS
     (inside the B disc) have q_hat > 0.5, and the crossing point of the
     profile lies between the two basins rather than inside either.

Usage: PYTHONPATH=<trails-md-burst-api>:<pathwayplanner> python run_committor_profile.py [--fast]
Writes committor_profile.md next to this file.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from pathwayplanner import Budget, Implementation, State
from pathwayplanner.backends.trailsmd import TrailsMDBackend

from run_stage2 import (  # noqa: E402  (same-directory experiment module)
    B_CENTER,
    BASIN_RADIUS,
    EXAMPLE,
    PHI_ATOMS,
    SPACE,
    in_disc,
    phi_psi,
)
from trails_md.bursts import BiasSpec, BurstSystem  # noqa: E402

HERE = Path(__file__).parent


def make_backend(system, workdir: Path, seed: int, stride: int = 50) -> TrailsMDBackend:
    return TrailsMDBackend(
        system=system, space=SPACE, workdir=workdir, stride=stride, base_seed=seed
    )


def rollout_fate(trajectory, a_center) -> str | None:
    """First basin reached along an unbiased rollout: 'A', 'B', or None."""
    for frame in trajectory.frames:
        cv = SPACE.project(frame)
        if in_disc(a_center)(cv):
            return "A"
        if in_disc(B_CENTER)(cv):
            return "B"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    n_seed_bursts = 6 if args.fast else 14
    n_rollouts = 6 if args.fast else 20
    burst_steps = 4000 if args.fast else 10000
    rollout_steps = 4000 if args.fast else 10000
    bias_k = 40.0

    runs = HERE / "runs_profile"
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
    wall_start = time.perf_counter()

    # -- Equilibrate to define the reactant basin A -------------------------
    import MDAnalysis as mda

    start_coords = mda.Universe(str(EXAMPLE / "structure.pdb")).atoms.positions
    eq_backend = make_backend(system, runs / "equilibrate", seed=11)
    eq_state = State(configuration=EXAMPLE / "structure.pdb", features=start_coords)
    eq_trajs = eq_backend.run_bursts(
        [eq_state],
        Implementation(cv=SPACE, bias=None, n_steps=burst_steps, n_replicas=2),
        budget,
    )
    a_state = State(
        configuration=eq_trajs[0].configurations[-1], features=eq_trajs[0].frames[-1]
    )
    a_center = SPACE.project(a_state.features)

    # -- Seed configurations spanning the barrier ---------------------------
    bias = BiasSpec(
        cv="torsion", form="harmonic", k=bias_k,
        target=float(np.radians(B_CENTER[0])), atoms=PHI_ATOMS,
    )
    pool: list[tuple[float, np.ndarray, object]] = []
    for i in range(n_seed_bursts):
        # A short save stride: under bias the barrier region is crossed in a
        # few hundred steps, so a coarse stride leaves the uncommitted phi
        # range unsampled entirely.
        backend = make_backend(system, runs / f"seed_{i}", seed=2000 + 31 * i, stride=10)
        trajs = backend.run_bursts(
            [a_state],
            Implementation(cv=SPACE, bias=bias, n_steps=burst_steps, n_replicas=2),
            budget,
        )
        for traj in trajs:
            for frame, config in zip(traj.frames, traj.configurations):
                pool.append((float(phi_psi(frame)[0]), frame, config))

    # -- Two-pass scan: bracket the crossing, then refine inside it ---------
    # The committor turns over sharply in phi for this system, so a uniform
    # scan wastes rollouts deep inside the basins and under-resolves the
    # transition. Pass 1 locates the interval where q_hat crosses 0.5; pass 2
    # samples that interval finely with more rollouts per point, which is the
    # same isocommittor-refinement idea used in the Trails-MD committor
    # estimator, applied here to the choice of validation points.

    def representatives_for(edges, source):
        picks: list[tuple[float, State]] = []
        for low, high in zip(edges[:-1], edges[1:]):
            members = sorted(
                (p for p in source if low <= p[0] < high), key=lambda p: p[0]
            )
            if not members:
                continue
            phi, frame, config = members[len(members) // 2]
            picks.append((phi, State(configuration=config, features=frame)))
        return picks

    def measure(picks, n_rep, tag):
        out = []
        for i, (phi, state) in enumerate(picks):
            backend = make_backend(
                system, runs / f"rollout_{tag}_{i}", seed=5000 + 97 * i + hash(tag) % 991
            )
            trajs = backend.run_bursts(
                [state],
                Implementation(cv=SPACE, bias=None, n_steps=rollout_steps,
                               n_replicas=n_rep),
                budget,
            )
            fates = [rollout_fate(t, a_center) for t in trajs]
            n_a, n_b = fates.count("A"), fates.count("B")
            resolved = n_a + n_b
            cv = SPACE.project(state.features)
            out.append(
                {
                    "phi": phi,
                    "features": state.features,
                    "q_hat": n_b / resolved if resolved else float("nan"),
                    "n_b": n_b,
                    "n_a": n_a,
                    "unresolved": len(fates) - resolved,
                    "pass": tag,
                    "region": "B" if in_disc(B_CENTER)(cv)
                    else ("A" if in_disc(a_center)(cv) else "transition"),
                }
            )
        return out

    coarse = measure(
        representatives_for(np.arange(-100.0, 101.0, 10.0), pool), n_rollouts, "coarse"
    )

    # Bracket: the last point below 0.5 and the first above it.
    resolved_coarse = [r for r in coarse if not np.isnan(r["q_hat"])]
    below = [r for r in resolved_coarse if r["q_hat"] < 0.5]
    above = [r for r in resolved_coarse if r["q_hat"] >= 0.5]
    refined: list[dict] = []
    bracket = None
    if below and above:
        lo = max(r["phi"] for r in below)
        hi = min(r["phi"] for r in above if r["phi"] > lo)
        bracket = (lo, hi)
        refined = measure(
            representatives_for(np.linspace(lo, hi, 7), pool),
            2 * n_rollouts,
            "refined",
        )

    rows = coarse + refined
    wall = time.perf_counter() - wall_start

    # -- Report and gates ---------------------------------------------------
    lines = ["# Committor profile across the alanine dipeptide barrier", ""]
    lines.append(
        f"Parameters: {n_seed_bursts} biased seeding bursts (k={bias_k} "
        f"kJ/mol/rad^2, {burst_steps} steps), {n_rollouts} unbiased rollouts of "
        f"{rollout_steps} steps per representative, basin radius "
        f"{BASIN_RADIUS} deg. A basin center {np.round(a_center, 1)} deg, "
        f"B = C7ax {tuple(B_CENTER)} deg."
    )
    lines.append("")
    lines.append("| phi (deg) | pass | region | q_hat | B | A | unresolved |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for row in sorted(rows, key=lambda r: r["phi"]):
        lines.append(
            f"| {row['phi']:.1f} | {row['pass']} | {row['region']} | "
            f"{row['q_hat']:.2f} | {row['n_b']} | {row['n_a']} | "
            f"{row['unresolved']} |"
        )
    lines.append("")
    if bracket is not None:
        lines.append(f"Crossing bracketed by the coarse pass to phi in "
                     f"[{bracket[0]:.1f}, {bracket[1]:.1f}] deg; refined pass "
                     f"sampled inside it.")
    else:
        lines.append("The coarse pass did not bracket a crossing.")
    lines.append("")

    resolved_rows = [r for r in rows if not np.isnan(r["q_hat"])]
    qs = [r["q_hat"] for r in resolved_rows]
    phis = [r["phi"] for r in resolved_rows]

    # Gate 1: the profile increases with phi (Spearman-style rank check).
    rank_corr = (
        float(np.corrcoef(np.argsort(np.argsort(phis)),
                          np.argsort(np.argsort(qs)))[0, 1])
        if len(resolved_rows) > 2 else float("nan")
    )
    monotone_pass = rank_corr > 0.7
    lines.append(f"- Rank correlation of q_hat with phi: **{rank_corr:.2f}** "
                 f"(gate: > 0.7) — {'PASS' if monotone_pass else 'FAIL'}")

    # Gate 2: every frame the classifier would label SUCCESS has q_hat > 0.5.
    success_rows = [r for r in resolved_rows if r["region"] == "B"]
    labels_pass = bool(success_rows) and all(r["q_hat"] > 0.5 for r in success_rows)
    lines.append(f"- SUCCESS-labelled frames with q_hat > 0.5: "
                 f"{sum(r['q_hat'] > 0.5 for r in success_rows)}/"
                 f"{len(success_rows)} — {'PASS' if labels_pass else 'FAIL'}")

    # Gate 3: the profile is non-trivial — at least one transition-region
    # frame is genuinely uncommitted (0.1 < q_hat < 0.9), which is what the
    # Stage 2 first-entry check could not show.
    transition_rows = [r for r in resolved_rows if r["region"] == "transition"]
    intermediate = [r for r in transition_rows if 0.1 < r["q_hat"] < 0.9]
    nontrivial_pass = len(intermediate) >= 1
    lines.append(f"- Transition-region frames with 0.1 < q_hat < 0.9: "
                 f"{len(intermediate)}/{len(transition_rows)} — "
                 f"{'PASS' if nontrivial_pass else 'FAIL'}")
    if intermediate:
        lines.append(
            "  - uncommitted frames at phi = "
            + ", ".join(f"{r['phi']:.0f} deg (q_hat {r['q_hat']:.2f})"
                        for r in intermediate)
        )

    # Diagnostic: is phi alone a reaction coordinate? If two configurations
    # at nearly the same phi have very different committors, it is not —
    # the remaining variance lives in psi (and the solvent-free system's
    # other degrees of freedom). This is measured, not assumed.
    degenerate = []
    ordered = sorted(resolved_rows, key=lambda r: r["phi"])
    for first, second in zip(ordered[:-1], ordered[1:]):
        if abs(second["phi"] - first["phi"]) < 5.0 and abs(
            second["q_hat"] - first["q_hat"]
        ) > 0.5:
            degenerate.append((first, second))
    lines.append("")
    lines.append("### Is phi alone the reaction coordinate?")
    if degenerate:
        for first, second in degenerate:
            lines.append(
                f"- phi {first['phi']:.1f} deg (q_hat {first['q_hat']:.2f}) vs "
                f"phi {second['phi']:.1f} deg (q_hat {second['q_hat']:.2f}): "
                f"{abs(second['phi'] - first['phi']):.1f} deg apart in phi, "
                f"{abs(second['q_hat'] - first['q_hat']):.2f} apart in q_hat; "
                f"psi = {phi_psi(first['features'])[1]:.0f} vs "
                f"{phi_psi(second['features'])[1]:.0f} deg."
            )
        lines.append(
            "- These pairs differ in phi *and* in psi, and the configurations "
            "were harvested from phi-biased trajectories along which the two "
            "coordinates are correlated. This scan therefore cannot attribute "
            "the committor to either coordinate; see analyze_committor_space.py "
            "for the collinearity diagnostic and what would be needed to "
            "separate them."
        )
    else:
        lines.append(
            "- No near-degenerate phi pairs with divergent committors were "
            "sampled; this scan is consistent with phi being sufficient, "
            "but does not establish it."
        )
    lines.append("")
    lines.append(f"Wall-clock {wall:.0f} s.")
    lines.append("")
    all_pass = monotone_pass and labels_pass and nontrivial_pass
    lines.append(f"## Gate: {'PASS' if all_pass else 'FAIL'}")

    (HERE / "committor_profile.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
