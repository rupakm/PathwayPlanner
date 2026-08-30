"""Fetch and clean the AdK reference structures: 1AKE (closed) and 4AKE (open).

Stage 3 (PLAN.md) needs two endpoint structures of E. coli adenylate kinase:
the ligand-bound closed form (1AKE, crystallised with the bisubstrate
analogue AP5A) and the apo open form (4AKE). Both are dimers in the
asymmetric unit; the biological unit is a monomer, so chain A alone is the
system of interest and chain B is discarded.

Cleaning is deliberately a plain-text PDB filter rather than a structure-
library round trip:

* No modelling is needed. Both entries cover residues 1-214 with no
  REMARK 465 (missing residues) and no REMARK 470 (missing atoms) records,
  so there is nothing to rebuild and therefore no reason to depend on
  pdbfixer. This is checked, not assumed -- :func:`clean_chain` raises if
  the chain is not the complete contiguous 1-214 AdK sequence.
* Heteroatoms go: AP5A, waters and any ions. The Stage 3 system is apo, and
  keeping the ligand would need parameters that Amber14 does not ship.
* 1AKE has alternate conformations; the A conformer is kept and its altLoc
  column blanked, which is what every downstream PDB reader expects.

Downloads are cached under ``structures/raw/`` so re-runs are offline. A
network failure raises rather than falling through to a partial file: a
truncated PDB would clean without complaint into a plausible-looking but
wrong structure.

Run:  python fetch_structures.py
Writes structures/{1ake,4ake}_chainA.pdb next to this file.
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STRUCTURES = HERE / "structures"
RAW = STRUCTURES / "raw"

RCSB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"
DOWNLOAD_TIMEOUT_S = 60

# The two conformational endpoints of the AdK open <-> closed transition.
ENTRIES = {
    "1ake": "closed, AP5A-bound (Muller & Schulz 1992, J. Mol. Biol. 224:159)",
    "4ake": "open, apo (Muller et al. 1996, Structure 4:147)",
}

# E. coli AdK: 214 residues, numbered 1-214 with no insertion codes.
N_RESIDUES = 214
SEQUENCE_HEAD = ("MET", "ARG", "ILE", "ILE", "LEU", "LEU", "GLY", "ALA", "PRO", "GLY")


def download(pdb_id: str, cache_dir: Path = RAW) -> Path:
    """Return the cached raw PDB for ``pdb_id``, downloading it from RCSB if absent.

    Raises RuntimeError with the underlying network error when the entry is
    not cached and cannot be fetched, so an offline run fails loudly instead
    of producing an empty or truncated structure.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{pdb_id.lower()}.pdb"
    if path.exists() and path.stat().st_size > 0:
        return path

    url = RCSB_URL.format(pdb_id=pdb_id.upper())
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"Could not download {pdb_id.upper()} from {url}: {exc}. "
            f"No cached copy at {path}. Fetch the entry manually and place it "
            f"there, then re-run."
        ) from exc
    if b"ATOM  " not in payload:
        raise RuntimeError(
            f"{url} returned {len(payload)} bytes with no ATOM records; refusing "
            f"to cache a non-structure response."
        )
    path.write_bytes(payload)
    return path


def clean_chain(raw_path: Path, out_path: Path, chain: str = "A") ->tuple[int, int]:
    """Write ``chain`` of ``raw_path`` as a protein-only PDB; return (n_atoms, n_res).

    Keeps ATOM records of the requested chain whose altLoc is blank or ``A``
    (blanking the column), drops every HETATM, and renumbers atom serials.
    Raises ValueError unless the result is the complete contiguous 1-214 AdK
    chain -- the guard that turns a bad download or an unexpected entry into
    an error rather than a silently wrong system.
    """
    kept: list[str] = []
    residues: list[int] = []
    names: dict[int, str] = {}
    for line in raw_path.read_text().splitlines():
        if not line.startswith("ATOM  ") or line[21] != chain:
            continue
        if line[16] not in (" ", "A"):
            continue
        if line[26] != " ":
            raise ValueError(f"{raw_path.name}: insertion code at {line[22:27]!r}")
        serial = len(kept) + 1
        kept.append(f"ATOM  {serial:5d}{line[11:16]} {line[17:]}")
        resid = int(line[22:26])
        if not residues or residues[-1] != resid:
            residues.append(resid)
        names[resid] = line[17:20]

    if residues != list(range(1, N_RESIDUES + 1)):
        raise ValueError(
            f"{raw_path.name} chain {chain}: expected contiguous residues "
            f"1-{N_RESIDUES}, got {len(residues)} residues spanning "
            f"{residues[0] if residues else '-'}-{residues[-1] if residues else '-'}"
        )
    head = tuple(names[i] for i in range(1, len(SEQUENCE_HEAD) + 1))
    if head != SEQUENCE_HEAD:
        raise ValueError(
            f"{raw_path.name} chain {chain}: sequence starts {head}, not the "
            f"E. coli AdK N-terminus {SEQUENCE_HEAD}"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join([*kept, "TER", "END", ""]))
    return len(kept), len(residues)


def main() -> int:
    STRUCTURES.mkdir(parents=True, exist_ok=True)
    for pdb_id, description in ENTRIES.items():
        raw = download(pdb_id)
        out = STRUCTURES / f"{pdb_id}_chainA.pdb"
        n_atoms, n_res = clean_chain(raw, out)
        print(f"{pdb_id.upper()} ({description})")
        print(f"  raw   {raw}")
        print(f"  clean {out}: {n_atoms} atoms, {n_res} residues, chain A only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
