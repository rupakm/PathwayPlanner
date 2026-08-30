"""OpenMM system loader for the closed-state AdK bursts.

The counterpart of system.py for the closed endpoint, passed as the
``system_file`` of a trails_md.bursts.BurstSystem when an action starts
from the closed structure (`open_hinge`).

Deliberately self-contained rather than importing the shared loader from
system.py: the Trails-MD engine imports this module by file path, in
worker processes whose sys.path is not under this experiment's control,
and a bare-name import of a sibling module is exactly the shadowing
hazard that PYTHONPATH ordering has already caused here once.
"""

from __future__ import annotations

import json
from pathlib import Path

from openmm import LangevinMiddleIntegrator, XmlSerializer
from openmm.unit import kelvin, picosecond, picoseconds

BASE_DIR = Path(__file__).resolve().parent
STRUCTURES = BASE_DIR / "structures"
SYSTEM_XML = STRUCTURES / "adk_closed_system.xml"
BUILD_JSON = STRUCTURES / "adk_closed_build.json"

FRICTION_PER_PS = 1.0


def make_system(_topology_source, temp: float = 300.0, dt: float = 0.004):
    """Load the closed AdK GBn2 system and its Langevin integrator."""
    if not SYSTEM_XML.exists():
        raise FileNotFoundError(
            f"{SYSTEM_XML} not found; run "
            f"'build_system.py --state closed' to generate it."
        )
    if not BUILD_JSON.exists():
        raise FileNotFoundError(
            f"{BUILD_JSON} not found; it records the step size the system's "
            f"hydrogen masses were repartitioned for, and without it the guard "
            f"below cannot run. Rebuild with build_system.py --state closed."
        )
    built_dt = json.loads(BUILD_JSON.read_text())["dt_ps"]
    if dt > built_dt + 1e-12:
        raise ValueError(
            f"dt={dt} ps exceeds the {built_dt} ps this system was built for "
            f"(see {BUILD_JSON}); rebuild with build_system.py or lower dt."
        )
    system = XmlSerializer.deserialize(SYSTEM_XML.read_text())
    integrator = LangevinMiddleIntegrator(
        temp * kelvin,
        FRICTION_PER_PS / picosecond,
        dt * picoseconds,
    )
    return system, integrator
