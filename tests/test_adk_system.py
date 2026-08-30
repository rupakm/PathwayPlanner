"""Smoke test for the Stage 3 AdK system: real bursts through the real backend.

Skipped unless build_system.py has been run, because the OpenMM System, the
hydrogenated topology and the equilibrated start frame are build products
rather than committed assets. When they exist this runs actual MD -- two short
unbiased replicas -- so it catches the wiring failures that unit tests with a
fake run_bursts cannot: a system_file that will not deserialise, a start frame
whose atom order disagrees with the topology, a burst that comes back with the
wrong number of frames.

Requires trails-md on the path with the burst API (trails_md.bursts).
"""

import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
ADK = REPO / "experiments" / "adk"
sys.path.insert(0, str(ADK))

STRUCTURES = ADK / "structures"
SYSTEM_XML = STRUCTURES / "adk_open_system.xml"
TOPOLOGY_PDB = STRUCTURES / "adk_open_topology.pdb"
EQUILIBRATED_PDB = STRUCTURES / "adk_open_equilibrated.pdb"

pytestmark = pytest.mark.skipif(
    not (SYSTEM_XML.exists() and TOPOLOGY_PDB.exists() and EQUILIBRATED_PDB.exists()),
    reason="AdK system not built; run experiments/adk/build_system.py",
)

N_ATOMS = 3341
N_STEPS = 400
STRIDE = 100
N_REPLICAS = 2

# CV values of the two crystal endpoints, from domains.py.
OPEN_LID_CORE_A = 30.8
CLOSED_LID_CORE_A = 21.0

# Floor for LID-CORE in the open state, chosen so the assertion holds at any
# burst length. The endpoint midpoint (25.9 A) does not: unbiased 500 ps
# replicas reach 24.34 A (README.md), below that midpoint, so raising N_STEPS
# would make the test fail on ordinary breathing. This floor sits under the
# measured minimum with margin while staying clear of the closed state, so it
# still catches a genuine collapse. The RMSD comparison in the same test is
# the primary discriminator and is length-independent by construction.
OPEN_LID_CORE_FLOOR_A = 23.0


def _fastest_platform() -> str:
    """First available OpenMM platform in descending order of speed."""
    from openmm import Platform

    available = {
        Platform.getPlatform(i).getName() for i in range(Platform.getNumPlatforms())
    }
    for name in ("CUDA", "HIP", "OpenCL", "CPU"):
        if name in available:
            return name
    raise RuntimeError("No OpenMM platform available")


@pytest.fixture(scope="module")
def trajectories(tmp_path_factory):
    """Two short unbiased AdK replicas from the equilibrated open start frame."""
    pytest.importorskip("trails_md.bursts")
    import domains
    from trails_md.bursts import BurstSystem

    from pathwayplanner import Budget, Implementation, State
    from pathwayplanner.backends.trailsmd import TrailsMDBackend

    space = domains.domain_distance_space(TOPOLOGY_PDB)
    system = BurstSystem(
        engine_name="openmm",
        engine_kwargs={
            "platform_name": _fastest_platform(),
            "temperature": 300.0,
            "dt": 0.004,
        },
        conf=EQUILIBRATED_PDB,
        top=EQUILIBRATED_PDB,
        system_file=ADK / "system.py",
    )
    backend = TrailsMDBackend(
        system=system,
        space=space,
        workdir=tmp_path_factory.mktemp("adk_smoke"),
        stride=STRIDE,
        base_seed=17,
    )
    start = State(configuration=EQUILIBRATED_PDB, features=np.empty(0))
    return backend.run_bursts(
        [start],
        Implementation(cv=space, bias=None, n_steps=N_STEPS, n_replicas=N_REPLICAS),
        Budget(max_steps=10**9),
    )


def test_bursts_return_the_expected_trajectory_shape(trajectories):
    assert len(trajectories) == N_REPLICAS
    for trajectory in trajectories:
        assert trajectory.frames.shape == (N_STEPS // STRIDE, N_ATOMS, 3)
        assert np.isfinite(trajectory.frames).all()
        assert trajectory.cost == N_STEPS


def test_all_cvs_are_finite_on_every_frame(trajectories):
    import domains

    spaces = {
        "lid_core": domains.lid_core_distance(TOPOLOGY_PDB),
        "nmp_core": domains.nmp_core_distance(TOPOLOGY_PDB),
        "theta_lid": domains.lid_core_angle(TOPOLOGY_PDB),
        "theta_nmp": domains.nmp_core_angle(TOPOLOGY_PDB),
        "rmsd_closed": domains.rmsd_to_reference(TOPOLOGY_PDB, domains.CLOSED_PDB),
        "rmsd_open": domains.rmsd_to_reference(TOPOLOGY_PDB, domains.OPEN_PDB),
    }
    for trajectory in trajectories:
        for frame in trajectory.frames:
            for name, space in spaces.items():
                value = space.project(frame)
                assert np.isfinite(value).all(), name


def test_short_unbiased_bursts_stay_in_the_open_state(trajectories):
    import domains

    lid_core = domains.lid_core_distance(TOPOLOGY_PDB)
    to_open = domains.rmsd_to_reference(TOPOLOGY_PDB, domains.OPEN_PDB)
    to_closed = domains.rmsd_to_reference(TOPOLOGY_PDB, domains.CLOSED_PDB)

    for trajectory in trajectories:
        for frame in trajectory.frames:
            assert float(to_open.project(frame)[0]) < float(to_closed.project(frame)[0])
            assert float(lid_core.project(frame)[0]) > OPEN_LID_CORE_FLOOR_A
