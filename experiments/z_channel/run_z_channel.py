"""Z-channel evaluation: a plan that must change direction mid-path.

The Z-channel's minimum-energy path is the polyline A=(0,0) -> (2,0) ->
(2,1) -> B=(0,1). Leg 1 runs +x and leg 3 runs -x, so any single linear
CV has non-positive progress on one of them; the direct A->B shortcut is
sealed by a wall of ~40 kT. The hypothesis under test:

    A single-CV action cannot realize the A->B transition, while a
    recipe composing three leg actions with different CVs (and a
    direction reversal) can, under the same total budget.

Strategies compared, N executions each:
  (a) single action, constant bias along the net A->B direction (+y);
  (b) single action, constant bias along leg 1 (+x) — the best single leg;
  (c) recipe Seq[leg(+x to x=2), leg(+y to y=1), leg(-x to x=0)] with
      outcome-aware threading (a failed leg aborts the recipe).

Each strategy gets the same per-execution step budget (3 legs' worth).
Success for every strategy is the same event: a frame inside the B disc.

Usage: python experiments/z_channel/run_z_channel.py [--fast]
Writes results.md next to this file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from pathwayplanner import Budget, Implementation, Outcome, State
from pathwayplanner.actions.base import Action, ActionResult
from pathwayplanner.backends.toy import (
    Z_CHANNEL_A,
    Z_CHANNEL_B,
    ToyBackend,
    z_channel_gradient,
)
from pathwayplanner.cv import EuclideanCV
from pathwayplanner.evaluation import estimate_outcomes
from pathwayplanner.outcomes import ThresholdClassifier
from pathwayplanner.recipes import Lift, Seq

HERE = Path(__file__).parent

XY = EuclideanCV(lambda f: np.asarray(f, dtype=float)[:2], dim=2)
B_RADIUS = 0.25


def in_b(frame: np.ndarray) -> bool:
    return XY.distance(XY.project(frame), Z_CHANNEL_B) < B_RADIUS


class LegAction(Action):
    """Drive one 1D CV toward a target value under a constant force.

    The CV is a linear projection axis; the classifier's success criterion
    is progress to within `tolerance` of the target along that axis.
    """

    def __init__(
        self,
        name: str,
        axis: np.ndarray,
        target_value: float,
        force: float,
        n_steps: int,
        n_replicas: int,
        tolerance: float = 0.15,
    ):
        self.name = name
        self.axis = np.asarray(axis, dtype=float)
        self.space = EuclideanCV(
            lambda f, a=self.axis: np.array([float(np.dot(np.asarray(f)[:2], a))]),
            dim=1,
        )
        self.target_value = target_value
        self.force = force
        self.n_steps = n_steps
        self.n_replicas = n_replicas
        self.tolerance = tolerance

    def precondition(self, state: State) -> bool:
        return True

    def propose(self, state: State):
        push = self.force * self.axis * np.sign(
            self.target_value - float(self.space.project(state.features)[0])
        )
        return [
            Implementation(
                cv=self.space,
                bias=lambda x, p=push: p,
                n_steps=self.n_steps,
                n_replicas=self.n_replicas,
            )
        ]

    def evaluate(self, initial_state, trajectories) -> ActionResult:
        start = float(self.space.project(initial_state.features)[0])
        needed = abs(self.target_value - start) - self.tolerance
        classifier = ThresholdClassifier(
            space=self.space,
            target_point=np.array([self.target_value]),
            delta=max(needed, 0.0),
        )
        return classifier.classify(initial_state, trajectories)


class DirectAction(LegAction):
    """Single-CV attempt at the whole transition: success only counts if a
    frame actually lands in the B disc (same event as the recipe)."""

    def evaluate(self, initial_state, trajectories) -> ActionResult:
        result = super().evaluate(initial_state, trajectories)
        hit = any(in_b(f) for t in trajectories for f in t.frames)
        if not hit and result.outcome is Outcome.SUCCESS:
            result.outcome = Outcome.PARTIAL
        if hit:
            result.outcome = Outcome.SUCCESS
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    n_runs = 10 if args.fast else 30
    n_steps = 3000
    n_replicas = 4
    force = 4.0
    kT = 0.15
    budget = Budget(max_steps=10**9)

    def backend(seed):
        return ToyBackend(gradient=z_channel_gradient, dt=1e-3, kT=kT, seed=seed)

    def start_state(bk):
        return bk.make_state(Z_CHANNEL_A.copy())

    def leg(name, axis, target):
        return LegAction(name, np.array(axis), target, force, n_steps, n_replicas)

    # Strategy (a): net A->B direction (+y), 3x the per-leg budget.
    def direct_step(seed):
        bk = backend(seed)
        action = DirectAction(
            "direct_y", np.array([0.0, 1.0]), Z_CHANNEL_B[1], force,
            3 * n_steps, n_replicas,
        )
        return Lift(lambda s: action.run(s, bk, budget)), start_state(bk)

    # Strategy (b): best single leg (+x), same total budget.
    def leg1_only_step(seed):
        bk = backend(seed)
        action = DirectAction(
            "direct_x", np.array([1.0, 0.0]), 2.0, force, 3 * n_steps, n_replicas
        )
        return Lift(lambda s: action.run(s, bk, budget)), start_state(bk)

    # Strategy (c): the three-leg recipe; same total step budget per run.
    def recipe_step(seed):
        bk = backend(seed)
        legs = [
            leg("leg1_+x", [1.0, 0.0], 2.0),
            leg("leg2_+y", [0.0, 1.0], 1.0),
            leg("leg3_-x", [1.0, 0.0], 0.0),
        ]
        steps = [Lift(lambda s, a=a: a.run(s, bk, budget)) for a in legs]

        def run_and_verify(state):
            result = Seq(steps)(state)
            # The recipe's success is the same event as the direct strategies':
            # a final state inside the B disc.
            if result.outcome is Outcome.SUCCESS and (
                result.best_state is None or not in_b(result.best_state.features)
            ):
                result.outcome = Outcome.PARTIAL
            return result

        return Lift(run_and_verify), start_state(bk)

    strategies = {
        "(a) single linear CV, net A->B (+y)": direct_step,
        "(b) single linear CV, leg-1 (+x)": leg1_only_step,
        "(c) three-leg recipe (+x, +y, -x)": recipe_step,
    }

    lines = ["# Z-channel results: single linear CV vs direction-changing recipe", ""]
    lines.append(
        f"Parameters: kT={kT}, dt=1e-3, force={force}, {n_steps} steps/leg, "
        f"{n_replicas} replicas, N={n_runs} runs/strategy; equal total budget "
        f"({3 * n_steps} steps of bias per execution). Success for every "
        f"strategy: a frame inside the B disc (radius {B_RADIUS})."
    )
    lines.append("")
    rates = {}
    for label, make in strategies.items():
        counts = {}
        cost = 0.0
        for i in range(n_runs):
            step, s0 = make(seed=10_000 + 137 * i)
            model = estimate_outcomes(step, s0, n=1)
            for o, c in model.counts.items():
                counts[o] = counts.get(o, 0) + c
            cost += model.total_cost
        total = sum(counts.values())
        rate = counts.get(Outcome.SUCCESS, 0) / total
        rates[label] = rate
        lines.append(f"## {label}")
        lines.append(f"- Outcomes: { {o.value: c for o, c in counts.items()} }")
        lines.append(f"- Success rate: **{rate:.2f}**; mean cost "
                     f"{cost / n_runs:,.0f} steps/run")
        lines.append("")

    single_best = max(rates[k] for k in rates if k.startswith("(a)") or k.startswith("(b)"))
    recipe_rate = rates["(c) three-leg recipe (+x, +y, -x)"]
    gate = single_best <= 0.1 and recipe_rate >= 0.7
    lines.append("## Verdict")
    lines.append(
        f"- Best single-CV success: {single_best:.2f} (gate: <= 0.1); "
        f"recipe success: {recipe_rate:.2f} (gate: >= 0.7)."
    )
    lines.append(f"- Gate: {'PASS' if gate else 'FAIL'} — a plan that changes "
                 "direction mid-path, with a separate CV per leg, is required "
                 "and sufficient on this landscape.")
    lines.append("")
    lines.append(
        "Scope of the claim. This defeats every *linear* CV by construction, "
        "since legs 1 and 3 have opposite x direction. It does not defeat all "
        "single coordinates: arc length along the polyline is one nonlinear CV "
        "that would drive the whole path. The landscape was also engineered to "
        "make the point, so it is an existence proof that composition can be "
        "necessary, not evidence about how often real systems are like this."
    )
    (HERE / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if gate else 1


if __name__ == "__main__":
    sys.exit(main())
