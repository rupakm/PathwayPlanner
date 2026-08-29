"""Trails-MD adapter: mapping Implementation/Budget onto the burst API.

Unit tests inject a fake run_bursts function and duck-typed BurstResults,
so they run without trails-md installed; the wiring test that resolves
the real trails_md.bursts.run_bursts is skipped when it is absent.
"""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from pathwayplanner import Budget, Implementation, Outcome, State
from pathwayplanner.backends.trailsmd import TrailsMDBackend
from pathwayplanner.cv import EuclideanCV

# CV: x coordinate of the first atom (frames are (n_atoms, 3) arrays).
SPACE = EuclideanCV(lambda coords: np.asarray(coords, dtype=float)[0, :1], dim=1)


def fake_result(x_values, success=True, steps=100):
    coords = np.array([[[x, 0.0, 0.0]] for x in x_values]) if success else None
    return SimpleNamespace(
        trajectory_path=Path("/dev/null"),
        frame_refs=[f"ref{i}" for i in range(len(x_values))] if success else [],
        coordinates=coords,
        steps_run=steps if success else 0,
        seed=1,
        success=success,
    )


def make_backend(results, record):
    def fake_run_bursts(system, start_frames, **kwargs):
        record.update(kwargs, start_frames=list(start_frames), system=system)
        return results

    return TrailsMDBackend(
        system="SYSTEM",
        space=SPACE,
        workdir=Path("/tmp/unused"),
        stride=5,
        base_seed=42,
        run_bursts_fn=fake_run_bursts,
    )


def test_run_bursts_maps_implementation_and_budget():
    record = {}
    backend = make_backend([fake_result([0.1, 0.2])], record)
    state = State(configuration=Path("start.pdb"), features=np.array([0.0]))
    impl = Implementation(cv=SPACE, bias="BIAS_SPEC", n_steps=500, n_replicas=3)

    trajectories = backend.run_bursts([state], impl, Budget(max_steps=200))

    assert record["start_frames"] == [Path("start.pdb")]
    assert record["system"] == "SYSTEM"
    assert record["n_steps"] == 200  # budget caps the implementation
    assert record["n_replicas_per_frame"] == 3
    assert record["bias"] == "BIAS_SPEC"
    assert record["stride"] == 5
    assert record["base_seed"] == 42
    assert len(trajectories) == 1


def test_trajectories_keep_raw_frames_with_configurations_and_cost():
    backend = make_backend([fake_result([0.1, 0.7], steps=250)], {})
    state = State(configuration=Path("start.pdb"), features=np.array([0.0]))
    impl = Implementation(cv=SPACE, n_steps=100, n_replicas=1)

    [traj] = backend.run_bursts([state], impl, Budget())

    # Frames are raw (n_atoms, 3) coordinates; projection is the consumer's job.
    np.testing.assert_allclose(traj.frames, [[[0.1, 0, 0]], [[0.7, 0, 0]]])
    np.testing.assert_allclose([SPACE.project(f) for f in traj.frames], [[0.1], [0.7]])
    assert list(traj.configurations) == ["ref0", "ref1"]
    assert traj.cost == 250


def test_failed_replicas_are_dropped():
    results = [fake_result([0.1]), fake_result([], success=False), fake_result([0.3])]
    backend = make_backend(results, {})
    state = State(configuration=Path("start.pdb"), features=np.array([0.0]))
    trajectories = backend.run_bursts(
        [state], Implementation(cv=SPACE, n_steps=10, n_replicas=3), Budget()
    )
    assert len(trajectories) == 2


def test_success_without_coordinates_raises():
    bad = SimpleNamespace(
        trajectory_path=Path("x.xtc"), frame_refs=["r"], coordinates=None,
        steps_run=10, seed=1, success=True,
    )
    backend = make_backend([bad], {})
    state = State(configuration=Path("start.pdb"), features=np.array([0.0]))
    with pytest.raises(RuntimeError, match="coordinates"):
        backend.run_bursts(
            [state], Implementation(cv=SPACE, n_steps=10, n_replicas=1), Budget()
        )


def test_make_state_projects_given_coordinates():
    backend = make_backend([], {})
    coords = np.array([[1.5, 0.0, 0.0], [9.0, 9.0, 9.0]])
    state = backend.make_state(Path("frame.pdb"), coordinates=coords)
    assert state.configuration == Path("frame.pdb")
    np.testing.assert_allclose(state.features, [1.5])


def test_end_to_end_with_classifier():
    """The adapter's output feeds the standard classifier unchanged."""
    from pathwayplanner.outcomes import ThresholdClassifier

    backend = make_backend([fake_result([0.0, 0.9, 2.1])], {})
    state = State(configuration=Path("start.pdb"), features=np.array([[0.0, 0, 0]]))
    impl = Implementation(cv=SPACE, n_steps=10, n_replicas=1)
    trajectories = backend.run_bursts([state], impl, Budget())
    clf = ThresholdClassifier(space=SPACE, target_point=np.array([2.0]), delta=1.5)
    # initial_state features here are already (n_atoms, 3)-like for SPACE.
    result = clf.classify(
        State(configuration=None, features=np.array([[0.0, 0.0, 0.0]])), trajectories
    )
    assert result.outcome is Outcome.SUCCESS


def test_default_run_bursts_resolves_real_module():
    pytest.importorskip("trails_md.bursts")
    backend = TrailsMDBackend(
        system=None, space=SPACE, workdir=Path("/tmp/unused"), base_seed=0
    )
    from trails_md.bursts import run_bursts as real

    assert backend._resolve_run_bursts() is real
