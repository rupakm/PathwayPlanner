"""Outcome semantics and recipe combinator behavior (no dynamics)."""

import numpy as np
import pytest

from pathwayplanner import ActionResult, Outcome, State
from pathwayplanner.recipes import Cond, Lift, Retry, Seq


def make_state(x=0.0, y=0.0, labels=()):
    point = np.array([x, y])
    return State(configuration=point, features=point, labels=set(labels))


def const_step(outcome, next_state=None, cost=1.0):
    def fn(state):
        successors = [next_state] if next_state is not None else []
        return ActionResult(outcome=outcome, successor_states=successors, cost=cost)

    return Lift(fn)


def test_terminal_failure_classification():
    assert Outcome.FAILURE.is_terminal_failure
    assert Outcome.UNSTABLE.is_terminal_failure
    assert Outcome.BUDGET_EXCEEDED.is_terminal_failure
    assert not Outcome.SUCCESS.is_terminal_failure
    assert not Outcome.PARTIAL.is_terminal_failure
    assert not Outcome.ALTERNATIVE.is_terminal_failure


def test_seq_threads_state_and_accumulates_cost():
    s1, s2 = make_state(1.0), make_state(2.0)
    seen = []

    def recording(next_state):
        def fn(state):
            seen.append(state)
            return ActionResult(Outcome.SUCCESS, [next_state], cost=1.0)

        return Lift(fn)

    start = make_state(0.0)
    result = Seq([recording(s1), recording(s2)])(start)
    assert result.outcome is Outcome.SUCCESS
    assert result.cost == pytest.approx(2.0)
    assert seen[0] is start
    assert seen[1] is s1
    assert result.best_state is s2


def test_seq_stops_on_terminal_failure():
    calls = []

    def failing(state):
        calls.append("fail")
        return ActionResult(Outcome.FAILURE, [])

    def never(state):
        calls.append("never")
        return ActionResult(Outcome.SUCCESS, [state])

    result = Seq([Lift(failing), Lift(never)])(make_state())
    assert result.outcome is Outcome.FAILURE
    assert calls == ["fail"]


def test_cond_branches_on_outcome():
    s1 = make_state(1.0)
    guard = const_step(Outcome.PARTIAL, next_state=s1)
    taken = []

    def branch(state):
        taken.append(state)
        return ActionResult(Outcome.SUCCESS, [state], cost=2.0)

    recipe = Cond(guard, {Outcome.PARTIAL: Lift(branch)})
    result = recipe(make_state())
    assert result.outcome is Outcome.SUCCESS
    assert taken == [s1]
    assert result.cost == pytest.approx(3.0)


def test_cond_unmapped_outcome_passes_through():
    guard = const_step(Outcome.FAILURE)
    recipe = Cond(guard, {Outcome.SUCCESS: const_step(Outcome.SUCCESS)})
    assert recipe(make_state()).outcome is Outcome.FAILURE


def test_retry_until_success():
    attempts = []

    def flaky(state):
        attempts.append(1)
        outcome = Outcome.SUCCESS if len(attempts) == 3 else Outcome.FAILURE
        return ActionResult(outcome, [state], cost=1.0)

    result = Retry(Lift(flaky), max_attempts=5)(make_state())
    assert result.outcome is Outcome.SUCCESS
    assert len(attempts) == 3
    assert result.cost == pytest.approx(3.0)


def test_recipe_contract_records_outcomes():
    from pathwayplanner.recipes import RecipeContract

    contract = RecipeContract(pre={"gate_closed"})
    assert contract.success_rate() is None
    assert contract.accepts({"gate_closed", "interface_intact"})
    assert not contract.accepts({"gate_open"})
    contract.record(ActionResult(Outcome.SUCCESS, []))
    contract.record(ActionResult(Outcome.FAILURE, []))
    assert contract.success_rate() == pytest.approx(0.5)
