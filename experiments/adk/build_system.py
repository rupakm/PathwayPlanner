"""Build the Stage 3 AdK OpenMM system from the 4AKE (open, apo) structure.

Runs once to produce the three committed-by-regeneration assets that
system.py and the Trails-MD BurstSystem consume:

* ``structures/adk_open_system.xml`` -- the serialised OpenMM System.
* ``structures/adk_open_topology.pdb`` -- the hydrogenated topology, used as
  the BurstSystem ``conf``/``top`` and as the atom-index reference for the
  CVs in domains.py.
* ``structures/adk_open_equilibrated.pdb`` -- minimised and briefly
  equilibrated coordinates; the Stage 3 open-state start frame.

Model choices, and why
----------------------
**Force field: Amber14 (ff14SB protein).** The same family as the alanine
dipeptide example, so Stage 2 -> Stage 3 changes the system and nothing else,
and the reference force field of essentially all published AdK simulation
work.

**Implicit solvent: GBn2** (``implicit/gbn2.xml``; Nguyen, Roe & Simmerling,
J. Chem. Theory Comput. 9 (2013) 2020, Amber ``igb=8``) rather than OBC2
(``igb=5``). The AdK open <-> closed transition is driven by a "salt-bridge
zipper" across the binding cleft (Beckstein et al. 2009), so the one quantity
this system must not get systematically wrong is salt-bridge and
intramolecular-electrostatics energetics -- precisely the failure mode GBn2
was parameterised to repair in OBC2, which over-stabilises salt bridges and
biases toward over-compact, over-helical structures. GBn2 costs somewhat more
per step than OBC2; the mechanism being studied is not worth trading for that.

Implicit rather than explicit solvent because Stage 3 needs at least 20
repeats from at least 3 start states for each of ~6 actions. Explicit TIP3P
solvation of AdK with a margin large enough for the open state is ~40k atoms;
implicit GBn2 is 3341, and removing solvent friction also speeds the domain
motion itself. The cost of that choice is real -- implicit solvent has no
hydrodynamic drag and no water-mediated contacts, so absolute rates are not
transferable -- but Stage 3 measures *relative* action success probabilities
and outcome distributions, which is what the budget has to buy.

**No nonbonded cutoff.** ``NoCutoff`` is 1.9x slower here than a 2 nm
``CutoffNonPeriodic`` (measured: 145 vs 270 ns/day on this machine's OpenCL
platform), but AdK's LID-CORE centroid separation is 21-31 Angstrom, so a
2 nm cutoff would truncate exactly the cross-cleft electrostatics that open
and close the lids. At 3341 atoms the full O(N^2) sum is affordable.

**Hydrogen mass repartitioning, on by default.** ``hydrogenMass=4 amu`` with
``constraints=HBonds`` permits a 4 fs step (Hopkins et al., J. Chem. Theory
Comput. 11 (2015) 1864), doubling throughput with no change to the
equilibrium ensemble. ``--no-hmr`` builds the 2 fs system instead; the step
size is written into the system so that system.py and every burst agree.

Run:  python build_system.py [--no-hmr] [--equilibrate-ps 200] [--platform CPU]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from openmm import LangevinMiddleIntegrator, Platform, XmlSerializer, unit
from openmm.app import HBonds, Modeller, NoCutoff, PDBFile, Simulation

HERE = Path(__file__).resolve().parent
STRUCTURES = HERE / "structures"
OPEN_PDB = STRUCTURES / "4ake_chainA.pdb"
CLOSED_PDB = STRUCTURES / "1ake_chainA.pdb"

# Both conformational endpoints get a system: `open_hinge` has to start from a
# closed-like structure, and `close_hinge` from an open one, so Stage 3 needs
# both. The apo closed state is not an equilibrium state -- without substrate
# the LID is expected to open on its own -- so its equilibration is kept short
# and the resulting theta_LID is reported, to confirm the starting structure
# is still closed before any action runs from it.
SOURCE_PDB = {"open": OPEN_PDB, "closed": CLOSED_PDB}


def artifacts(state: str) -> dict[str, Path]:
    """Output paths for a built state ("open" or "closed")."""
    return {
        "system_xml": STRUCTURES / f"adk_{state}_system.xml",
        "topology_pdb": STRUCTURES / f"adk_{state}_topology.pdb",
        "equilibrated_pdb": STRUCTURES / f"adk_{state}_equilibrated.pdb",
        "build_json": STRUCTURES / f"adk_{state}_build.json",
    }


_OPEN = artifacts("open")
SYSTEM_XML = _OPEN["system_xml"]
TOPOLOGY_PDB = _OPEN["topology_pdb"]
EQUILIBRATED_PDB = _OPEN["equilibrated_pdb"]
BUILD_JSON = _OPEN["build_json"]

FORCE_FIELD = ("amber14-all.xml", "implicit/gbn2.xml")
TEMPERATURE_K = 300.0
FRICTION_PER_PS = 1.0
HMR_HYDROGEN_MASS_AMU = 4.0
HMR_TIMESTEP_PS = 0.004
PLAIN_TIMESTEP_PS = 0.002


def build_system(pdb_path: Path = OPEN_PDB, hmr: bool = True):
    """Return (topology, positions, system, dt_ps) for the apo open AdK monomer.

    Adds hydrogens at pH 7 to the heavy-atom crystal structure -- 4AKE has no
    missing residues or atoms, so no loop or side-chain rebuilding is needed --
    and creates the GBn2 implicit-solvent system described in the module
    docstring.
    """
    from openmm.app import ForceField

    pdb = PDBFile(str(pdb_path))
    forcefield = ForceField(*FORCE_FIELD)
    modeller = Modeller(pdb.topology, pdb.positions)
    modeller.addHydrogens(forcefield, pH=7.0)
    hydrogen_mass = (HMR_HYDROGEN_MASS_AMU if hmr else 1.0) * unit.amu
    system = forcefield.createSystem(
        modeller.topology,
        nonbondedMethod=NoCutoff,
        constraints=HBonds,
        hydrogenMass=hydrogen_mass,
    )
    dt_ps = HMR_TIMESTEP_PS if hmr else PLAIN_TIMESTEP_PS
    return modeller.topology, modeller.positions, system, dt_ps


def equilibrate(topology, positions, system, dt_ps: float, ps: float, platform: str):
    """Minimise, then run ``ps`` picoseconds of Langevin dynamics at 300 K.

    Returns (final positions, achieved ns/day). The run is short by design: it
    relieves crystal-structure strain and lets the added hydrogens settle,
    without sampling far enough to leave the open basin that defines the
    Stage 3 start state.
    """
    integrator = LangevinMiddleIntegrator(
        TEMPERATURE_K * unit.kelvin,
        FRICTION_PER_PS / unit.picosecond,
        dt_ps * unit.picoseconds,
    )
    simulation = Simulation(
        topology, system, integrator, Platform.getPlatformByName(platform)
    )
    simulation.context.setPositions(positions)
    simulation.minimizeEnergy()
    simulation.context.setVelocitiesToTemperature(TEMPERATURE_K * unit.kelvin, 1234)

    n_steps = max(1, round(ps / dt_ps))
    start = time.perf_counter()
    simulation.step(n_steps)
    state = simulation.context.getState(getPositions=True, getEnergy=True)
    elapsed = time.perf_counter() - start
    ns_per_day = n_steps * dt_ps / 1000.0 / elapsed * 86400.0
    return state.getPositions(), ns_per_day, n_steps, elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-hmr", dest="hmr", action="store_false")
    parser.add_argument("--equilibrate-ps", type=float, default=200.0)
    parser.add_argument("--platform", default="OpenCL")
    parser.add_argument(
        "--state",
        choices=sorted(SOURCE_PDB),
        default="open",
        help="which conformational endpoint to build",
    )
    args = parser.parse_args()

    source = SOURCE_PDB[args.state]
    out = artifacts(args.state)
    if not source.exists():
        print(f"Missing {source}; run fetch_structures.py first.", file=sys.stderr)
        return 1

    topology, positions, system, dt_ps = build_system(source, hmr=args.hmr)
    STRUCTURES.mkdir(parents=True, exist_ok=True)
    out["system_xml"].write_text(XmlSerializer.serialize(system))
    with out["topology_pdb"].open("w") as handle:
        PDBFile.writeFile(topology, positions, handle)

    final, ns_per_day, n_steps, elapsed = equilibrate(
        topology, positions, system, dt_ps, args.equilibrate_ps, args.platform
    )
    with out["equilibrated_pdb"].open("w") as handle:
        PDBFile.writeFile(topology, final, handle)

    out["build_json"].write_text(
        json.dumps(
            {
                "force_field": list(FORCE_FIELD),
                "nonbonded_method": "NoCutoff",
                "constraints": "HBonds",
                "hydrogen_mass_amu": HMR_HYDROGEN_MASS_AMU if args.hmr else 1.0,
                "dt_ps": dt_ps,
                "temperature_K": TEMPERATURE_K,
                "friction_per_ps": FRICTION_PER_PS,
                "n_atoms": system.getNumParticles(),
                "equilibration_ps": args.equilibrate_ps,
                "equilibration_platform": args.platform,
                "equilibration_ns_per_day": round(ns_per_day, 1),
                "state": args.state,
                "source_pdb": source.name,
            },
            indent=2,
        )
        + "\n"
    )

    print(f"WROTE {out['system_xml']} ({system.getNumParticles()} particles)")
    print(f"WROTE {out['topology_pdb']}")
    print(f"WROTE {out['equilibrated_pdb']}")
    print(
        f"Equilibrated {n_steps} steps x {dt_ps * 1000:.0f} fs = "
        f"{args.equilibrate_ps:.0f} ps on {args.platform} in {elapsed:.0f} s "
        f"({ns_per_day:.0f} ns/day)"
    )
    _report_state(out["topology_pdb"], out["equilibrated_pdb"], source)
    return 0


def _report_state(topology_pdb: Path, equilibrated_pdb: Path, source: Path) -> None:
    """Print the hinge CVs of the crystal and equilibrated structures.

    The apo closed state is not an equilibrium state, so equilibration can
    itself start opening the LID. Printing theta_LID before and after is how a
    starting structure is confirmed to still represent the state it is meant
    to, rather than assumed to.
    """
    import MDAnalysis as mda

    import domains

    theta_lid = domains.lid_core_angle(topology_pdb)
    theta_nmp = domains.nmp_core_angle(topology_pdb)
    lid_core = domains.lid_core_distance(topology_pdb)
    frames = {
        "crystal": mda.Universe(str(source)).atoms.positions.astype(float),
        "equilibrated": mda.Universe(str(equilibrated_pdb)).atoms.positions.astype(float),
    }
    print(f"{'':<14}{'theta_LID':>10}{'theta_NMP':>11}{'LID-CORE':>10}")
    for label, frame in frames.items():
        if len(frame) != len(mda.Universe(str(topology_pdb)).atoms):
            # The crystal frame has no hydrogens, so CV spaces bound to the
            # hydrogenated topology cannot index it; report only what applies.
            crystal_spaces = (
                domains.lid_core_angle(source),
                domains.nmp_core_angle(source),
                domains.lid_core_distance(source),
            )
            values = [float(s.project(frame)[0]) for s in crystal_spaces]
        else:
            values = [
                float(s.project(frame)[0]) for s in (theta_lid, theta_nmp, lid_core)
            ]
        print(f"{label:<14}{values[0]:10.2f}{values[1]:11.2f}{values[2]:10.2f}")


if __name__ == "__main__":
    sys.exit(main())
