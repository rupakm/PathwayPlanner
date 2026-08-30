"""AdK domain partition, hinges, and the Stage 3 collective-variable spaces.

Adenylate kinase moves as three quasi-rigid domains: a static CORE and two
lids -- LID (ATP side) and NMP (AMP side) -- that swing shut over the
substrates. Stage 3 (PLAN.md) plans `open_hinge`/`close_hinge` actions on
exactly these bodies, so the residue partition and the CVs that measure the
domain motions belong in one module the actions, classifiers and event specs
all import.

Residue definitions
-------------------
The partition below is the one used by Beckstein, Denning, Perilla and Woolf,
"Zipping and unzipping of adenylate kinase: atomistic insights into the
ensemble of open <-> closed transitions", J. Mol. Biol. 394 (2009) 160-176
(Figure 1): for E. coli AdK, CORE = 1-29, 60-121, 160-214; NMP = 30-59;
LID = 122-159. It is verified against the actual numbering of the downloaded
structures -- both 1AKE and 4AKE chain A cover residues 1-214 contiguously
with no insertion codes (see fetch_structures.py), so PDB residue numbers and
literature residue numbers coincide with no offset.

Other papers draw the boundaries slightly differently -- e.g. NMP = 30-67,
LID = 118-167 with CORE = 1-29, 68-117, 161-214 (Muller & Schulz's original
split, still common) -- which moves a handful of hinge residues between
bodies. The Beckstein partition is used here because the two hinge angles
defined below, the standard low-dimensional description of the AdK
transition, come from the same paper and must be consistent with it.

Hinges
------
Hinge numbering follows Henzler-Wildman, Lei, Thai, Kerns, Karplus and Kern,
Nature 450 (2007) 913-916, as tabulated in Beckstein et al. 2009: hinge 1 =
30-32, hinge 2 = 50-54, hinge 3 = 60-61 (the NMP-CORE hinges), hinge 5 =
114-116 and hinge 7 = 158-159 (the LID-CORE hinges). These are the five of
the eight Henzler-Wildman hinges that Beckstein et al. observed transiently
unfolding during the transition -- the "cracking" residues, and therefore the
natural targets for a `weaken_interface`-style action.

Collective variables
--------------------
Five CVSpaces, all consuming (n_atoms, 3) Angstrom frames as produced by the
Trails-MD burst API:

* LID-CORE and NMP-CORE C-alpha centroid distances (EuclideanCV, Angstrom) --
  the cheapest separation of open from closed and the natural bias CVs, since
  trails_md.bursts.BiasSpec(cv="distance") biases exactly a centroid-centroid
  distance between two atom groups.
* theta_LID and theta_NMP hinge angles (PeriodicCV, degrees), defined by
  Beckstein et al. 2009 as the angle between the centres of geometry of the
  backbone and C-beta atoms of three residue windows. A bond-angle value is
  confined to [0, 180], where minimum-image wrapping with period 360 is the
  identity, so the periodic metric agrees with the Euclidean one on every
  physically reachable value; PeriodicCV is used regardless because an angular
  CV that a bias or a classifier might push past a branch cut should carry its
  periodicity in the space, not in the caller.
* RMSD to a reference structure (EuclideanCV, Angstrom), computed over
  C-alpha atoms after optimal superposition. C-alpha only, so a reference
  crystal structure with no hydrogens can be compared against a solvated,
  hydrogenated simulation frame with no atom-name matching.

Run:  python domains.py
Prints the CV values of both reference structures, which is how the claim
"these CVs separate open from closed" is checked rather than assumed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from pathwayplanner.cv import EuclideanCV, PeriodicCV

HERE = Path(__file__).resolve().parent
STRUCTURES = HERE / "structures"
CLOSED_PDB = STRUCTURES / "1ake_chainA.pdb"
OPEN_PDB = STRUCTURES / "4ake_chainA.pdb"

N_RESIDUES = 214

CORE_RANGES = ((1, 29), (60, 121), (160, 214))
NMP_RANGES = ((30, 59),)
LID_RANGES = ((122, 159),)


def _expand(ranges: tuple[tuple[int, int], ...]) -> frozenset[int]:
    return frozenset(r for lo, hi in ranges for r in range(lo, hi + 1))


CORE = _expand(CORE_RANGES)
NMP = _expand(NMP_RANGES)
LID = _expand(LID_RANGES)

NMP_HINGES = {1: (30, 32), 2: (50, 54), 3: (60, 61)}
LID_HINGES = {5: (114, 116), 7: (158, 159)}
HINGES = {**NMP_HINGES, **LID_HINGES}

# Angle windows of Beckstein et al. 2009: (arm, vertex, arm). The vertex group
# is the middle one -- 90-100 (CORE) for theta_NMP, and the 115-125 hinge for
# theta_LID.
THETA_NMP_GROUPS = ((115, 125), (90, 100), (35, 55))
THETA_LID_GROUPS = ((179, 185), (115, 125), (125, 153))

ANGLE_SELECTION = "backbone or name CB"


# ---------------------------------------------------------------------------
# Geometry kernels (pure: coordinates and index lists in, scalars out)
# ---------------------------------------------------------------------------


def centroid(coords: np.ndarray, indices) -> np.ndarray:
    """Unweighted centre of geometry of ``indices`` in an (n_atoms, 3) frame."""
    return np.asarray(coords, dtype=float)[np.asarray(indices, dtype=int)].mean(axis=0)


def centroid_distance(coords: np.ndarray, group_a, group_b) -> float:
    """Distance between the centres of geometry of two atom groups, in frame units."""
    return float(np.linalg.norm(centroid(coords, group_a) - centroid(coords, group_b)))


def centroid_angle(coords: np.ndarray, group_a, vertex, group_b) -> float:
    """Angle in degrees at the ``vertex`` centroid, subtended by two arm centroids."""
    origin = centroid(coords, vertex)
    u = centroid(coords, group_a) - origin
    v = centroid(coords, group_b) - origin
    cosine = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)))
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def kabsch_rmsd(mobile: np.ndarray, reference: np.ndarray) -> float:
    """RMSD between two equal-length (n, 3) point sets after optimal superposition.

    Uses the SVD form of Kabsch's solution with the reflection correction, and
    evaluates the residual in closed form rather than rotating the coordinates,
    which is what makes this cheap enough to call once per trajectory frame.
    """
    mobile = np.asarray(mobile, dtype=float)
    reference = np.asarray(reference, dtype=float)
    if mobile.shape != reference.shape or mobile.ndim != 2 or mobile.shape[1] != 3:
        raise ValueError(
            f"kabsch_rmsd needs two matching (n, 3) arrays; got {mobile.shape} "
            f"and {reference.shape}"
        )
    a = mobile - mobile.mean(axis=0)
    b = reference - reference.mean(axis=0)
    singular = np.linalg.svd(a.T @ b, compute_uv=True)
    u, s, vt = singular
    s = s.copy()
    if np.linalg.det(u @ vt) < 0:
        s[-1] = -s[-1]
    residual = (np.sum(a * a) + np.sum(b * b) - 2.0 * np.sum(s)) / len(a)
    return float(np.sqrt(max(residual, 0.0)))


# ---------------------------------------------------------------------------
# Topology -> atom indices
# ---------------------------------------------------------------------------


def atom_indices(topology, ranges, selection: str = "name CA") -> np.ndarray:
    """0-based atom indices of ``selection`` within the given residue ranges.

    ``topology`` is anything MDAnalysis can open as a Universe (a PDB path or
    an existing Universe). Indices are returned in topology order, which is the
    order of the (n_atoms, 3) frames the burst API hands back.
    """
    universe = _universe(topology)
    resid_spec = " or ".join(f"resid {lo}:{hi}" for lo, hi in ranges)
    group = universe.select_atoms(f"({selection}) and ({resid_spec})")
    if group.n_atoms == 0:
        raise ValueError(
            f"Selection '({selection}) and ({resid_spec})' matched no atoms in "
            f"{topology}"
        )
    return group.indices.astype(int)


def _universe(topology):
    import MDAnalysis as mda

    if hasattr(topology, "select_atoms"):
        return topology
    return mda.Universe(str(topology))


def _reference_ca(reference) -> np.ndarray:
    """C-alpha coordinates of residues 1-214 of a reference structure, in Angstrom."""
    universe = _universe(reference)
    group = universe.select_atoms(f"name CA and resid 1:{N_RESIDUES}")
    if group.n_atoms != N_RESIDUES:
        raise ValueError(
            f"{reference}: expected {N_RESIDUES} C-alpha atoms, found {group.n_atoms}"
        )
    return group.positions.astype(float)


# ---------------------------------------------------------------------------
# CV spaces
# ---------------------------------------------------------------------------


def lid_core_distance(topology) -> EuclideanCV:
    """LID-CORE C-alpha centroid distance in Angstrom, bound to ``topology``."""
    lid = atom_indices(topology, LID_RANGES)
    core = atom_indices(topology, CORE_RANGES)
    return EuclideanCV(lambda frame: centroid_distance(frame, lid, core), dim=1)


def nmp_core_distance(topology) -> EuclideanCV:
    """NMP-CORE C-alpha centroid distance in Angstrom, bound to ``topology``."""
    nmp = atom_indices(topology, NMP_RANGES)
    core = atom_indices(topology, CORE_RANGES)
    return EuclideanCV(lambda frame: centroid_distance(frame, nmp, core), dim=1)


def domain_distance_space(topology) -> EuclideanCV:
    """The 2D (LID-CORE, NMP-CORE) centroid-distance plane in Angstrom.

    The planning space for Stage 3: both lids in one CV vector, so a single
    ChannelClassifier can tell a LID-only opening from an NMP-only one.
    """
    lid = atom_indices(topology, LID_RANGES)
    nmp = atom_indices(topology, NMP_RANGES)
    core = atom_indices(topology, CORE_RANGES)

    def project(frame):
        return np.array(
            [centroid_distance(frame, lid, core), centroid_distance(frame, nmp, core)]
        )

    return EuclideanCV(project, dim=2)


def lid_core_angle(topology) -> PeriodicCV:
    """theta_LID in degrees (Beckstein et al. 2009), bound to ``topology``."""
    return _angle_space(topology, THETA_LID_GROUPS)


def nmp_core_angle(topology) -> PeriodicCV:
    """theta_NMP in degrees (Beckstein et al. 2009), bound to ``topology``."""
    return _angle_space(topology, THETA_NMP_GROUPS)


def _angle_space(topology, groups) -> PeriodicCV:
    arm_a, vertex, arm_b = (
        atom_indices(topology, (window,), ANGLE_SELECTION) for window in groups
    )
    return PeriodicCV(
        lambda frame: centroid_angle(frame, arm_a, vertex, arm_b), periods=[360.0]
    )


def rmsd_to_reference(topology, reference) -> EuclideanCV:
    """C-alpha RMSD in Angstrom to ``reference`` after optimal superposition.

    ``topology`` supplies the C-alpha indices into simulation frames;
    ``reference`` is a structure file whose residues 1-214 provide the target
    coordinates. Matching is by residue order, which is exact here because both
    reference entries and the built system cover residues 1-214 of one chain.
    """
    mobile = atom_indices(topology, ((1, N_RESIDUES),))
    target = _reference_ca(reference)
    if len(mobile) != len(target):
        raise ValueError(
            f"topology has {len(mobile)} C-alpha atoms but reference {reference} "
            f"has {len(target)}"
        )
    return EuclideanCV(
        lambda frame: kabsch_rmsd(np.asarray(frame, dtype=float)[mobile], target), dim=1
    )


def reference_report(topology=OPEN_PDB) -> dict[str, dict[str, float]]:
    """CV values of both reference structures, keyed by CV name then structure.

    The verification that the Stage 3 CVs are usable at all: open and closed
    must be far apart in the distance CVs relative to thermal fluctuation.
    """
    import MDAnalysis as mda

    spaces = {
        "lid_core_distance_A": lid_core_distance(topology),
        "nmp_core_distance_A": nmp_core_distance(topology),
        "theta_lid_deg": lid_core_angle(topology),
        "theta_nmp_deg": nmp_core_angle(topology),
        "rmsd_to_1ake_closed_A": rmsd_to_reference(topology, CLOSED_PDB),
        "rmsd_to_4ake_open_A": rmsd_to_reference(topology, OPEN_PDB),
    }
    frames = {
        name: mda.Universe(str(path)).atoms.positions.astype(float)
        for name, path in (("1AKE closed", CLOSED_PDB), ("4AKE open", OPEN_PDB))
    }
    return {
        cv_name: {
            structure: float(space.project(frame)[0])
            for structure, frame in frames.items()
        }
        for cv_name, space in spaces.items()
    }


def main() -> int:
    for path in (CLOSED_PDB, OPEN_PDB):
        if not path.exists():
            print(f"Missing {path}; run fetch_structures.py first.", file=sys.stderr)
            return 1
    report = reference_report()
    width = max(len(name) for name in report)
    print(f"{'CV':<{width}}  {'1AKE closed':>12}  {'4AKE open':>12}  {'|delta|':>9}")
    for name, values in report.items():
        closed, opened = values["1AKE closed"], values["4AKE open"]
        print(f"{name:<{width}}  {closed:12.2f}  {opened:12.2f}  {abs(opened - closed):9.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
