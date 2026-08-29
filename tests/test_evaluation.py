"""Outcome estimation, JS divergence, delta_comp, reference committor."""

import numpy as np
import pytest

from pathwayplanner import ActionResult, Outcome, State
from pathwayplanner.backends.toy import double_well_potential
from pathwayplanner.evaluation import (
    OutcomeModel,
    delta_comp,
    estimate_outcomes,
    reference_committor,
)
from pathwayplanner.recipes import Lift, RecipeContract


def make_state(x=0.0, y=0.0, tag=None):
    p = np.array([x, y])
    metadata = {"tag": tag} if tag else {}
    return State(configuration=p, features=p, metadata=metadata)


def const_step(outcome):
    return Lift(lambda s: ActionResult(outcome, [s], cost=1.0))


def test_estimate_outcomes_deterministic():
    model = estimate_outcomes(const_step(Outcome.SUCCESS), make_state(), n=10)
    assert model.n == 10
    assert model.probs()[Outcome.SUCCESS] == pytest.approx(1.0)
    assert len(model.successors) == 10


def test_estimate_outcomes_records_into_contract():
    contract = RecipeContract()
    estimate_outcomes(const_step(Outcome.FAILURE), make_state(), n=5, contract=contract)
    assert contract.outcome_counts[Outcome.FAILURE] == 5


def test_js_divergence_identical_zero_disjoint_one():
    a = OutcomeModel.from_outcomes([Outcome.SUCCESS] * 10)
    b = OutcomeModel.from_outcomes([Outcome.SUCCESS] * 10)
    c = OutcomeModel.from_outcomes([Outcome.FAILURE] * 10)
    assert a.js_divergence(b) == pytest.approx(0.0)
    assert a.js_divergence(c) == pytest.approx(1.0)
    mixed = OutcomeModel.from_outcomes([Outcome.SUCCESS] * 5 + [Outcome.FAILURE] * 5)
    assert 0.0 < a.js_divergence(mixed) < 1.0


def test_delta_comp_fine_abstraction_beats_coarse():
    # P1: 50/50 sends the system to type "a" or type "b" successors.
    # P2: always succeeds from "a", always fails from "b".
    # Fine abstraction (sees the tag): predicted ~= actual ~= 0.5.
    # Coarse abstraction (one class): representative sampling gives 0 or 1.
    rng = np.random.default_rng(0)

    def p1(state):
        tag = "a" if rng.random() < 0.5 else "b"
        return ActionResult(Outcome.SUCCESS, [make_state(tag=tag)], cost=1.0)

    def p2(state):
        outcome = Outcome.SUCCESS if state.metadata.get("tag") == "a" else Outcome.FAILURE
        return ActionResult(outcome, [state], cost=1.0)

    fine = delta_comp(
        Lift(p1), Lift(p2), make_state(), n_runs=200, n_per_class=20,
        abstraction=lambda s: s.metadata.get("tag"),
    )
    coarse = delta_comp(
        Lift(p1), Lift(p2), make_state(), n_runs=200, n_per_class=20,
        abstraction=lambda s: "one_class",
    )
    assert fine.actual == pytest.approx(0.5, abs=0.1)
    assert fine.delta < 0.1
    assert coarse.delta > 0.3


def test_delta_comp_p1_failures_count_against_composition():
    def p1(state):
        return ActionResult(Outcome.FAILURE, [], cost=1.0)

    def p2(state):
        return ActionResult(Outcome.SUCCESS, [state], cost=1.0)

    result = delta_comp(
        Lift(p1), Lift(p2), make_state(), n_runs=20, n_per_class=5,
        abstraction=lambda s: "x",
    )
    assert result.actual == pytest.approx(0.0)
    assert result.predicted == pytest.approx(0.0)


def test_reference_committor_symmetric_double_well():
    # Symmetric double well, A = left well, B = right well: q(0, y) ~= 0.5
    # by symmetry, q ~= 0 in A, q ~= 1 in B.
    grid_x = np.linspace(-1.6, 1.6, 65)
    grid_y = np.linspace(-0.8, 0.8, 33)
    q = reference_committor(
        double_well_potential,
        grid_x,
        grid_y,
        in_a=lambda p: (p[0] + 1.0) ** 2 + p[1] ** 2 < 0.04,
        in_b=lambda p: (p[0] - 1.0) ** 2 + p[1] ** 2 < 0.04,
        kT=0.3,
    )
    mid = q(np.array([0.0, 0.0]))
    assert mid == pytest.approx(0.5, abs=0.05)
    assert q(np.array([-1.0, 0.0])) < 0.05
    assert q(np.array([1.0, 0.0])) > 0.95
