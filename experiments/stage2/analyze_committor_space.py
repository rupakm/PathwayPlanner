"""Is the committor a function of (phi, psi), or of phi alone?

The committor profile script reports q_hat against phi, which bins a
two-dimensional CV space by one of its coordinates and therefore cannot
distinguish "phi is an adequate coordinate" from "phi is inadequate and
the scatter is psi showing through". This script answers that question
from the data the profile run already wrote to disk.

Reconstruction. Nothing is re-simulated. The burst API's file-based
transport saved, for every measurement point, the exact starting
configuration (`burst_0/start_0.pdb`) and every unbiased rollout
launched from it (`burst_0/iteration_0_*.xtc`); this script recovers
(phi, psi) of each start and the A/B fate of each rollout from those
files.

Two analyses:

1. Pairs. For measurement points close in phi, how different are their
   committors, and how far apart are they in psi? A large committor gap
   between configurations that agree in phi but differ in psi is direct
   evidence that phi alone does not determine the committor.

2. Binomial models. Logistic fits to the rollout counts using periodic
   (sin, cos) features, comparing

       A:  logit q = a + b sin(phi) + c cos(phi)
       B:  logit q = a + b sin(phi) + c cos(phi) + d sin(psi) + e cos(psi)

   by penalized log-likelihood and an approximate likelihood-ratio test.
   An L2 penalty keeps coefficients finite: many points sit at q_hat = 0
   or 1 exactly, which is perfect separation for an unpenalized fit.

Usage: PYTHONPATH=<trails-md-burst-api>:<pathwayplanner> python analyze_committor_space.py
Writes committor_space.md next to this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import chi2

from run_stage2 import B_CENTER, BASIN_RADIUS, EXAMPLE, SPACE, phi_psi  # noqa: E402

HERE = Path(__file__).parent
RUNS = HERE / "runs_profile"
TOPOLOGY = EXAMPLE / "structure.pdb"
PENALTY = 1e-2


def load_universe(path: Path, topology: Path):
    import MDAnalysis as mda

    return mda.Universe(str(topology), str(path))


def basin_of(cv: np.ndarray, a_center: np.ndarray) -> str | None:
    if SPACE.distance(cv, a_center) < BASIN_RADIUS:
        return "A"
    if SPACE.distance(cv, B_CENTER) < BASIN_RADIUS:
        return "B"
    return None


def collect(a_center: np.ndarray) -> list[dict]:
    """Rebuild every measurement point from the saved burst directories."""
    points = []
    for directory in sorted(RUNS.glob("rollout_*")):
        burst = directory / "burst_0"
        start_pdb = burst / "start_0.pdb"
        trajectories = sorted(burst.glob("iteration_0_*.xtc"))
        if not start_pdb.exists() or not trajectories:
            continue
        start = load_universe(start_pdb, TOPOLOGY).atoms.positions
        phi, psi = phi_psi(start)

        n_a = n_b = unresolved = 0
        for trajectory in trajectories:
            universe = load_universe(trajectory, TOPOLOGY)
            fate = None
            for _ in universe.trajectory:
                fate = basin_of(SPACE.project(universe.atoms.positions), a_center)
                if fate is not None:
                    break
            if fate == "A":
                n_a += 1
            elif fate == "B":
                n_b += 1
            else:
                unresolved += 1
        resolved = n_a + n_b
        points.append(
            {
                "name": directory.name,
                "phi": float(phi),
                "psi": float(psi),
                "n_a": n_a,
                "n_b": n_b,
                "unresolved": unresolved,
                "q_hat": n_b / resolved if resolved else float("nan"),
            }
        )
    return points


def features(points, with_psi: bool) -> np.ndarray:
    phi = np.radians([p["phi"] for p in points])
    columns = [np.ones(len(points)), np.sin(phi), np.cos(phi)]
    if with_psi:
        psi = np.radians([p["psi"] for p in points])
        columns += [np.sin(psi), np.cos(psi)]
    return np.column_stack(columns)


def fit_binomial(X: np.ndarray, n_b: np.ndarray, n_total: np.ndarray):
    """Penalized binomial logistic fit; returns (coefficients, log-likelihood)."""

    def negative_ll(beta):
        z = np.clip(X @ beta, -30.0, 30.0)
        ll = np.sum(n_b * z - n_total * np.logaddexp(0.0, z))
        return -ll + PENALTY * float(beta[1:] @ beta[1:])

    result = minimize(negative_ll, np.zeros(X.shape[1]), method="L-BFGS-B")
    z = np.clip(X @ result.x, -30.0, 30.0)
    ll = float(np.sum(n_b * z - n_total * np.logaddexp(0.0, z)))
    return result.x, ll


def main() -> int:
    # The reactant basin center: recovered from the equilibration burst that
    # the profile run performed, exactly as that run defined it.
    eq = RUNS / "equilibrate" / "burst_0"
    eq_traj = sorted(eq.glob("iteration_0_*.xtc"))[0]
    universe = load_universe(eq_traj, TOPOLOGY)
    # Index the final frame directly. Iterating a Universe.trajectory to
    # exhaustion rewinds it to frame 0, which would silently take the
    # extended starting structure as the reactant basin instead of the
    # equilibrated one.
    universe.trajectory[-1]
    a_center = SPACE.project(universe.atoms.positions)

    points = [p for p in collect(a_center) if not np.isnan(p["q_hat"])]
    if len(points) < 5:
        print(f"Only {len(points)} usable measurement points; run the profile first.")
        return 1

    lines = ["# Is the committor determined by phi alone, or by (phi, psi)?", ""]
    lines.append(
        f"Reconstructed from {len(points)} measurement points saved by the "
        f"committor profile run; no dynamics were re-run. Reactant basin "
        f"center {np.round(a_center, 1)} deg, product basin {tuple(B_CENTER)} deg, "
        f"basin radius {BASIN_RADIUS} deg."
    )
    lines.append("")
    lines.append("| phi (deg) | psi (deg) | q_hat | B | A | unresolved |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for p in sorted(points, key=lambda r: r["phi"]):
        lines.append(
            f"| {p['phi']:.1f} | {p['psi']:.1f} | {p['q_hat']:.2f} | "
            f"{p['n_b']} | {p['n_a']} | {p['unresolved']} |"
        )
    lines.append("")

    # -- 1. Pairs close in phi ---------------------------------------------
    lines.append("## 1. Configurations that agree in phi")
    ordered = sorted(points, key=lambda r: r["phi"])
    close_pairs = [
        (a, b)
        for a, b in zip(ordered[:-1], ordered[1:])
        if abs(b["phi"] - a["phi"]) < 5.0
    ]
    divergent = [(a, b) for a, b in close_pairs if abs(b["q_hat"] - a["q_hat"]) > 0.5]
    if close_pairs:
        lines.append(f"- {len(close_pairs)} pairs within 5 deg in phi; "
                     f"{len(divergent)} of them differ by more than 0.5 in q_hat.")
        for a, b in close_pairs:
            lines.append(
                f"  - phi {a['phi']:.1f} / {b['phi']:.1f} deg "
                f"(delta {abs(b['phi'] - a['phi']):.1f}), "
                f"psi {a['psi']:.1f} / {b['psi']:.1f} deg "
                f"(delta {abs(b['psi'] - a['psi']):.1f}), "
                f"q_hat {a['q_hat']:.2f} / {b['q_hat']:.2f}"
            )
    else:
        lines.append("- No pairs within 5 deg in phi were sampled.")
    lines.append("")

    # -- 2. Binomial model comparison --------------------------------------
    n_b = np.array([p["n_b"] for p in points], dtype=float)
    n_total = np.array([p["n_a"] + p["n_b"] for p in points], dtype=float)
    _, ll_phi = fit_binomial(features(points, with_psi=False), n_b, n_total)
    _, ll_both = fit_binomial(features(points, with_psi=True), n_b, n_total)
    delta = 2.0 * (ll_both - ll_phi)
    p_value = float(chi2.sf(delta, df=2)) if delta > 0 else 1.0
    aic_phi = -2 * ll_phi + 2 * 3
    aic_both = -2 * ll_both + 2 * 5
    lines.append("## 2. Binomial model comparison")
    lines.append(f"- Model A, phi only: log-likelihood {ll_phi:.2f}, AIC {aic_phi:.2f}")
    lines.append(f"- Model B, phi and psi: log-likelihood {ll_both:.2f}, "
                 f"AIC {aic_both:.2f}")
    lines.append(f"- Likelihood-ratio statistic {delta:.2f} on 2 df, "
                 f"approximate p = {p_value:.4f} "
                 f"(approximate: an L2 penalty of {PENALTY} is applied because "
                 f"points at q_hat = 0 or 1 give perfect separation).")
    better = "psi adds explanatory power" if aic_both < aic_phi else (
        "psi does not improve the fit by AIC"
    )
    lines.append(f"- Verdict by AIC: **{better}**.")
    lines.append("")

    # -- 3. Collinearity: can this design attribute anything to psi? --------
    phis = np.array([p["phi"] for p in points])
    psis = np.array([p["psi"] for p in points])
    collinearity = float(np.corrcoef(phis, psis)[0, 1])
    q0 = [p for p in points if p["q_hat"] < 0.5]
    q1 = [p for p in points if p["q_hat"] >= 0.5]
    phi_gap = (max(p["phi"] for p in q0), min(p["phi"] for p in q1))
    phi_separates = phi_gap[0] < phi_gap[1]
    lines.append("## 3. Can this design attribute the committor to a coordinate?")
    lines.append(f"- Pearson correlation of phi with psi across the sampled "
                 f"configurations: **{collinearity:.3f}**.")
    lines.append(
        f"- phi ranges: q_hat < 0.5 reaches {phi_gap[0]:.1f} deg, q_hat >= 0.5 "
        f"starts at {phi_gap[1]:.1f} deg — phi "
        f"{'separates the two classes without overlap' if phi_separates else 'does not separate the classes'}."
    )
    lines.append("")

    lines.append("## Interpretation")
    lines.append(
        f"- The committor turns over sharply within the sampled ensemble, "
        f"between phi {phi_gap[0]:.1f} and {phi_gap[1]:.1f} deg — equivalently "
        f"between psi {[p['psi'] for p in q0 if p['phi'] == phi_gap[0]][0]:.1f} "
        f"and {[p['psi'] for p in q1 if p['phi'] == phi_gap[1]][0]:.1f} deg."
    )
    if abs(collinearity) > 0.8:
        lines.append(
            f"- **This dataset cannot attribute the committor to phi or to psi "
            f"individually.** Every configuration was harvested from "
            f"phi-biased trajectories, along which psi follows phi; the two "
            f"coordinates are correlated at r = {collinearity:.3f} across the "
            f"measurement points. The pair that straddles the transition "
            f"differs in both coordinates at once, and the model comparison in "
            f"section 2 is confounded by the same collinearity: with two "
            f"near-collinear predictors, the larger model can fit a sharper "
            f"threshold without any genuine psi dependence. The AIC gap is "
            f"therefore not evidence that psi matters."
        )
        lines.append(
            "- Separating the two requires configurations that break the "
            "correlation: hold phi fixed by restraint and sample a range of "
            "psi, then measure the committor across that range. Until that is "
            "done, the honest statement is that the transition is sharp in the "
            "sampled ensemble, and which coordinate controls it is open."
        )
    elif divergent:
        lines.append(
            "- Configurations agreeing in phi to within 5 deg have committors "
            "differing by more than 0.5, and phi and psi are not strongly "
            "collinear here, so phi alone does not determine the committor."
        )
    else:
        lines.append(
            "- No pair agreeing in phi showed a large committor gap; this "
            "dataset gives no evidence against phi as a sufficient coordinate, "
            "which is weak evidence rather than confirmation."
        )
    lines.append(
        "- The classifier and CV space used throughout Stage 2 are the full "
        "periodic (phi, psi) plane; only the profile's *reporting axis* was "
        "phi. Nothing here indicts the Stage 2 evaluation: it bears on how the "
        "profile should be described, not on how the actions were classified."
    )
    (HERE / "committor_space.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
