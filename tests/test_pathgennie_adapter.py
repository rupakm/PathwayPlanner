"""PathGennie adapter: driver-based event search as an action implementation.

Runs against the real pathgennie library (ToyLangevinEngine on the
Wolfe-Quapp surface); skipped when pathgennie is not installed.
"""

import numpy as np
import pytest

pytest.importorskip("pathgennie")

from pathgennie.core.toy import ToyLangevinEngine  # noqa: E402

from pathwayplanner import Budget, Outcome  # noqa: E402
from pathwayplanner.backends.pathgennie import (  # noqa: E402
    DriverSearchSpec,
    run_driver_search,
    search_to_action_result,
)
from pathwayplanner.cv import EuclideanCV  # noqa: E402

# Wolfe-Quapp minima (same surface in pathgennie.core.toy and our toy backend).
# Start positions are (n_atoms, 3) Angstrom arrays, per the engine contract.
MIN_A = np.array([-1.174, 1.477])
MIN_B = np.array([1.124, -1.486])
START_A = np.array([[MIN_A[0], MIN_A[1], 0.0]])


def projection(coords: np.ndarray) -> np.ndarray:
    """(n_atoms, 3) toy coordinates -> 2D CV (the x, y position)."""
    return np.asarray(coords, dtype=float).reshape(-1, 3)[0, :2]


SPACE = EuclideanCV(projection, dim=2)


def near_b(coords: np.ndarray) -> bool:
    return bool(SPACE.distance(SPACE.project(coords), MIN_B) < 0.4)


def make_spec(max_cycle=60):
    return DriverSearchSpec(
        space=SPACE,
        event=near_b,
        target_cv=MIN_B,
        tau1=150,
        tau2=150,
        max_trial=8,
        max_cycle=max_cycle,
        sigma=0.1,
    )


def test_search_converges_to_target_event():
    engine = ToyLangevinEngine(dt=0.002, kT=0.8)
    result = run_driver_search(
        engine, START_A, make_spec(), seed=1, budget=Budget(max_steps=10_000_000)
    )
    assert result.converged
    final_cv = SPACE.project(result.trajectory.frames[-1])
    assert np.linalg.norm(final_cv - MIN_B) < 0.4
    # Configurations retained: full coordinates per saved frame, restartable.
    assert result.trajectory.configurations is not None
    assert len(result.trajectory.configurations) == len(result.trajectory.frames)
    assert result.cost > 0


def test_budget_caps_cycles():
    engine = ToyLangevinEngine(dt=0.002, kT=0.8)
    # One cycle costs max_trial*tau1 + tau2 = 1350 steps; budget allows 2 cycles.
    result = run_driver_search(
        engine, START_A, make_spec(max_cycle=60), seed=2, budget=Budget(max_steps=2700)
    )
    assert result.n_cycles <= 2
    assert not result.converged


def test_search_to_action_result_success_and_budget_exceeded():
    engine = ToyLangevinEngine(dt=0.002, kT=0.8)
    ok = run_driver_search(
        engine, START_A, make_spec(), seed=3, budget=Budget(max_steps=10_000_000)
    )
    action_result = search_to_action_result(ok)
    assert action_result.outcome is Outcome.SUCCESS
    assert action_result.best_state is not None
    # Successor features are the converged frame's coordinates.
    assert np.linalg.norm(SPACE.project(action_result.best_state.features) - MIN_B) < 0.4

    capped = run_driver_search(
        engine, START_A, make_spec(), seed=4, budget=Budget(max_steps=2700)
    )
    action_result = search_to_action_result(capped)
    assert action_result.outcome is Outcome.BUDGET_EXCEEDED
    # The search still reports where it got to.
    assert action_result.best_state is not None


def test_start_position_goes_through_the_angstrom_contract():
    """The engine entry point must be create_handle, not create_state.

    Both PathGennie engines document create_handle as taking (n_atoms, 3)
    Angstrom coordinates, and get_coords as returning them. create_state is
    not uniform: the OpenMM engine passes its argument straight to
    Context.setPositions, where a bare array means nanometres, so routing
    Angstrom coordinates there would silently inflate the structure tenfold.
    """
    seen = {}

    class RecordingEngine(ToyLangevinEngine):
        def create_state(self, position):
            seen["create_state"] = np.asarray(position)
            return super().create_state(position)

        def create_handle(self, coords):
            seen["create_handle"] = np.asarray(coords)
            return super().create_handle(coords)

    engine = RecordingEngine(dt=0.002, kT=0.8)
    start = np.array([[MIN_A[0], MIN_A[1], 0.0]])
    run_driver_search(
        engine, start, make_spec(max_cycle=1), seed=5, budget=Budget(max_steps=1400)
    )
    assert "create_handle" in seen, "adapter must use the Angstrom contract"
    assert "create_state" not in seen
    np.testing.assert_allclose(seen["create_handle"], start)


def test_seeded_search_is_reproducible():
    spec = make_spec()
    runs = []
    for _ in range(2):
        engine = ToyLangevinEngine(dt=0.002, kT=0.8)
        runs.append(
            run_driver_search(engine, START_A, spec, seed=7, budget=Budget(max_steps=10_000_000))
        )
    np.testing.assert_array_equal(runs[0].trajectory.frames, runs[1].trajectory.frames)
    assert runs[0].converged == runs[1].converged
