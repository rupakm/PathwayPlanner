"""End-to-end: a minimal action on the toy double well.

Defines a throwaway "cross_barrier" action (well at x=-1 to well at
x=+1) and checks the whole pipeline: propose -> execute on ToyBackend ->
ThresholdClassifier -> ActionResult, plus registry and compiler wiring.
"""

import numpy as np
import pytest

from pathwayplanner import Budget, Implementation, Outcome, State
from pathwayplanner.actions import Action, register, create, available
from pathwayplanner.backends import ToyBackend
from pathwayplanner.compiler import RuleBasedCompiler
from pathwayplanner.outcomes import ThresholdClassifier


def x_coordinate(frame: np.ndarray) -> float:
    return float(frame[0])


@register("cross_barrier")
class CrossBarrierAction(Action):
    """Drive x from the left well toward the right well by at least delta."""

    name = "cross_barrier"

    def __init__(self, delta: float = 1.5):
        self.delta = delta
        self.classifier = ThresholdClassifier(cv=x_coordinate, delta=delta)

    def precondition(self, state: State) -> bool:
        return state.features[0] < 0.0

    def propose(self, state: State):
        # A gentle constant push in +x; the toy stand-in for a weak bias.
        return [
            Implementation(
                cv=x_coordinate,
                bias=lambda x: np.array([6.0, 0.0]),
                n_steps=2000,
                n_replicas=8,
            )
        ]

    def evaluate(self, initial_state, trajectories):
        return self.classifier.classify(initial_state, trajectories)


def test_registry_round_trip():
    assert "cross_barrier" in available()
    action = create("cross_barrier", delta=1.0)
    assert isinstance(action, CrossBarrierAction)
    assert action.delta == 1.0


def test_action_succeeds_with_bias():
    backend = ToyBackend(seed=42)
    start = backend.make_state(np.array([-1.0, 0.0]))
    action = create("cross_barrier")
    result = action.run(start, backend, Budget(max_steps=10_000))
    assert result.outcome is Outcome.SUCCESS
    assert result.best_state is not None
    assert result.best_state.features[0] >= 0.5
    assert result.cost > 0
    assert result.implementation is not None


def test_action_fails_without_enough_budget():
    backend = ToyBackend(seed=7)
    start = backend.make_state(np.array([-1.0, 0.0]))
    action = create("cross_barrier")
    result = action.run(start, backend, Budget(max_steps=5))
    assert result.outcome in (Outcome.FAILURE, Outcome.PARTIAL)


def test_precondition_failure_is_semantic_not_exception():
    backend = ToyBackend()
    start = backend.make_state(np.array([1.0, 0.0]))
    result = create("cross_barrier").run(start, backend, Budget())
    assert result.outcome is Outcome.FAILURE
    assert result.metadata["reason"] == "precondition_failed"


def test_rule_based_compiler_falls_back_to_proposal():
    backend = ToyBackend()
    start = backend.make_state(np.array([-1.0, 0.0]))
    action = create("cross_barrier")
    compiler = RuleBasedCompiler()
    impl = compiler.compile(start, action)
    assert impl.n_replicas == 8

    # A rule overrides the proposal.
    small = Implementation(cv=x_coordinate, n_steps=10, n_replicas=1)
    compiler.add_rule(lambda s, a: True, lambda s, a: small)
    assert compiler.compile(start, action) is small


def test_backend_reproducible_with_seed():
    def run_once():
        backend = ToyBackend(seed=123)
        start = backend.make_state(np.array([-1.0, 0.0]))
        impl = Implementation(cv=x_coordinate, n_steps=50, n_replicas=2)
        return backend.run_bursts([start], impl, Budget())

    a, b = run_once(), run_once()
    for ta, tb in zip(a, b):
        np.testing.assert_array_equal(ta.frames, tb.frames)


def test_optional_backends_are_import_guarded():
    from pathwayplanner.backends import trailsmd, pathgennie

    if not trailsmd.HAVE_TRAILS_MD:
        with pytest.raises(ImportError):
            trailsmd.make_backend()
    if not pathgennie.HAVE_PATHGENNIE:
        with pytest.raises(ImportError):
            pathgennie.make_backend()
