"""OpenMM system loader for the Stage 3 AdK bursts.

Passed as the ``system_file`` of a trails_md.bursts.BurstSystem. The
Trails-MD OpenMM engine imports this module, calls ``make_system`` with
whichever of ``temp``/``dt`` the signature accepts, and then seeds the
returned integrator itself.

Deserialising the System that build_system.py wrote -- rather than rebuilding
it from the force field on every walker -- is what makes every burst of every
Stage 3 action provably the same Hamiltonian, and skips the per-walker
template matching for a 3341-atom protein.

The default ``dt`` is the 4 fs of the hydrogen-mass-repartitioned build. A
caller that passes ``dt`` through BurstSystem.engine_kwargs overrides it, and
the mismatch guard below refuses a step size the system's hydrogen masses
cannot support, since an unstable 4 fs run on unrepartitioned hydrogens fails
as silently drifting energies rather than as an error.
"""

from __future__ import annotations

import json
from pathlib import Path

from openmm import LangevinMiddleIntegrator, XmlSerializer
from openmm.unit import kelvin, picosecond, picoseconds

BASE_DIR = Path(__file__).resolve().parent
STRUCTURES = BASE_DIR / "structures"
SYSTEM_XML = STRUCTURES / "adk_open_system.xml"
BUILD_JSON = STRUCTURES / "adk_open_build.json"

FRICTION_PER_PS = 1.0


def make_system(_topology_source, temp: float = 300.0, dt: float = 0.004):
    """Load the AdK GBn2 implicit-solvent system and its Langevin integrator."""
    if not SYSTEM_XML.exists():
        raise FileNotFoundError(
            f"{SYSTEM_XML} not found; run build_system.py to generate the "
            f"Stage 3 AdK system."
        )
    system = XmlSerializer.deserialize(SYSTEM_XML.read_text())

    built_dt = json.loads(BUILD_JSON.read_text())["dt_ps"] if BUILD_JSON.exists() else dt
    if dt > built_dt + 1e-12:
        raise ValueError(
            f"dt={dt} ps exceeds the {built_dt} ps this system was built for "
            f"(see {BUILD_JSON}); rebuild with build_system.py or lower dt."
        )

    integrator = LangevinMiddleIntegrator(
        temp * kelvin,
        FRICTION_PER_PS / picosecond,
        dt * picoseconds,
    )
    return system, integrator
