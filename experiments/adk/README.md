# Adenylate kinase (AdK) system for Stage 3

The simulation system and collective variables for the Stage 3 action
vocabulary in [docs/PLAN.md](../../docs/PLAN.md): `open_hinge`/`close_hinge`
(LID, NMP), `weaken_interface(LID, CORE)`, `rotate_domain(LID)`, `explore`,
`relax`. Nothing here runs an action — this is the substrate they run on.

## What gets built

```
PYTHONPATH="<trails-md-burst-api>:<pathwayplanner>" python fetch_structures.py
PYTHONPATH=... python build_system.py          # ~2.5 min
PYTHONPATH=... python domains.py               # prints the CV table below
```

| File | Produced by | Contents |
| --- | --- | --- |
| `structures/raw/{1ake,4ake}.pdb` | `fetch_structures.py` | RCSB download cache; re-runs are offline |
| `structures/{1ake,4ake}_chainA.pdb` | `fetch_structures.py` | Chain A protein only, 1656 atoms, residues 1–214 |
| `structures/adk_open_system.xml` | `build_system.py` | Serialised OpenMM `System`, 3341 particles |
| `structures/adk_open_topology.pdb` | `build_system.py` | Hydrogenated topology; the atom-index reference for every CV |
| `structures/adk_open_equilibrated.pdb` | `build_system.py` | Minimised + 200 ps at 300 K; the Stage 3 open start frame |
| `structures/adk_open_build.json` | `build_system.py` | The model parameters, recorded so `system.py` can check `dt` |

Build products are gitignored: they are reproducible from the two scripts, and
`tests/test_adk_system.py` skips itself when they are absent.

`system.py` is the `system_file` handed to `trails_md.bursts.BurstSystem`; it
deserialises `adk_open_system.xml` and returns it with a Langevin integrator,
following the same contract as the alanine dipeptide example used in Stage 2.

## Structures

**4AKE** (Müller, Schlauderer, Reinstein & Schulz, *Structure* 4 (1996) 147) —
open, apo, the Stage 3 starting conformation. **1AKE** (Müller & Schulz,
*J. Mol. Biol.* 224 (1992) 159) — closed, crystallised with the bisubstrate
analogue AP5A, used only as an RMSD reference.

Both are dimers in the asymmetric unit; the biological unit is a monomer, so
chain A is kept and chain B discarded. AP5A, waters and 1AKE's alternate
conformers are stripped. Neither entry has `REMARK 465` (missing residues) or
`REMARK 470` (missing atoms) — both cover residues 1–214 contiguously with no
insertion codes — so no loop or side-chain rebuilding is needed and
`fetch_structures.py` has no pdbfixer dependency. `clean_chain` asserts that
completeness, so a truncated download raises instead of silently producing a
plausible-looking wrong structure.

Because PDB numbering is contiguous 1–214 in both entries, **literature residue
numbers and PDB residue numbers coincide with no offset** — the check the domain
definitions below depend on.

## Model choices

**Force field: Amber14** (`amber14-all.xml`, ff14SB protein). The same family as
the Stage 2 alanine dipeptide example, so the step from Stage 2 to Stage 3
changes the system and nothing else, and the reference force field of
essentially all published AdK simulation work.

**Implicit solvent: GBn2** (`implicit/gbn2.xml`; Nguyen, Roe & Simmerling,
*J. Chem. Theory Comput.* 9 (2013) 2020 — Amber `igb=8`), **not OBC2**
(`igb=5`). The AdK open ↔ closed transition is driven by a "salt-bridge zipper"
across the binding cleft (Beckstein et al. 2009), so salt-bridge and
intramolecular-electrostatics energetics is the one quantity this system must
not get systematically wrong — and that is precisely the OBC2 failure mode GBn2
was parameterised to repair (OBC2 over-stabilises salt bridges and biases
toward over-compact, over-helical structures). GBn2 costs more per step; the
mechanism under study is not worth trading for that.

**Implicit rather than explicit solvent.** Stage 3 needs ≥20 repeats from ≥3
start states for each of ~6 actions. Explicit TIP3P solvation of AdK with a box
margin large enough for the open state is ~40k atoms; implicit GBn2 is 3341,
and removing solvent friction speeds the domain motion itself. The cost is
real: implicit solvent has no hydrodynamic drag and no water-mediated contacts,
so absolute rates are not transferable. Stage 3 measures *relative* action
success probabilities and outcome distributions, which is what the budget can
buy.

**No nonbonded cutoff.** Measured on this machine's OpenCL platform, `NoCutoff`
runs at 145 ns/day against 270 ns/day for a 2 nm `CutoffNonPeriodic` — 1.9×
slower. It is still the right choice: the LID–CORE centroid separation is
21–31 Å, so a 2 nm cutoff would truncate exactly the cross-cleft electrostatics
that open and close the lids. At 3341 atoms the full O(N²) sum is affordable.

**Hydrogen mass repartitioning, on by default.** `hydrogenMass=4 amu` with
`constraints=HBonds` permits a 4 fs step (Hopkins et al., *J. Chem. Theory
Comput.* 11 (2015) 1864), doubling throughput with no change to the equilibrium
ensemble. `build_system.py --no-hmr` builds the 2 fs system instead; the step
size is recorded in `adk_open_build.json` and `system.py` refuses a `dt` larger
than the hydrogen masses support, because an unstable 4 fs run on
unrepartitioned hydrogens shows up as slowly drifting energies rather than as
an error.

**Integrator:** `LangevinMiddleIntegrator`, 300 K, friction 1 ps⁻¹, dt 4 fs.

## Domain definitions

From Beckstein, Denning, Perilla & Woolf, "Zipping and unzipping of adenylate
kinase: atomistic insights into the ensemble of open ↔ closed transitions",
*J. Mol. Biol.* 394 (2009) 160–176, Figure 1:

| Domain | Residues | Size |
| --- | --- | --- |
| CORE | 1–29, 60–121, 160–214 | 146 |
| NMP | 30–59 | 30 |
| LID | 122–159 | 38 |

Other papers draw the boundaries differently — Müller & Schulz's original split
(NMP 30–67, LID 118–167, CORE 1–29, 68–117, 161–214) is still widely used and
moves a handful of hinge residues between bodies. The Beckstein partition is
used here because the two hinge angles below come from the same paper and must
be consistent with it.

**Hinges**, numbered as in Henzler-Wildman, Lei, Thai, Kerns, Karplus & Kern,
*Nature* 450 (2007) 913–916, as tabulated by Beckstein et al.:

| Hinge | Residues | Joins |
| --- | --- | --- |
| 1 | 30–32 | NMP–CORE |
| 2 | 50–54 | NMP–CORE |
| 3 | 60–61 | NMP–CORE |
| 5 | 114–116 | LID–CORE |
| 7 | 158–159 | LID–CORE |

These are the five of the eight Henzler-Wildman hinges that Beckstein et al.
observed transiently unfolding during the transition — the "cracking" residues,
and therefore the natural targets for a `weaken_interface`-style action.

## Collective variables

All five consume `(n_atoms, 3)` Ångström frames as returned by the Trails-MD
burst API, and are bound to a topology once at construction.

- **`lid_core_distance`, `nmp_core_distance`** — Cα centroid distances
  (`EuclideanCV`, Å). The natural bias CVs, because
  `trails_md.bursts.BiasSpec(cv="distance")` biases exactly a centroid–centroid
  distance between two atom groups. `domain_distance_space` bundles both into
  the 2D planning space, so one classifier can tell a LID-only opening from an
  NMP-only one.
- **`lid_core_angle` (θ_LID), `nmp_core_angle` (θ_NMP)** — `PeriodicCV` in
  degrees, period 360. Beckstein et al.'s definition: the angle between the
  centres of geometry of the backbone and Cβ atoms of three residue windows,
  θ_NMP over (115–125, **90–100**, 35–55) and θ_LID over (179–185,
  **115–125**, 125–153), the bold window being the vertex. A bond angle lives
  in [0, 180], where minimum-image wrapping at period 360 is the identity, so
  the periodic metric agrees with the Euclidean one on every physically
  reachable value; `PeriodicCV` is used regardless so that an angular CV a bias
  or classifier might push past a branch cut carries its periodicity in the
  space rather than in the caller.
- **`rmsd_to_reference`** — Cα RMSD (`EuclideanCV`, Å) after optimal Kabsch
  superposition. Cα-only so a hydrogen-free crystal reference can be compared
  against a hydrogenated simulation frame with no atom-name matching.

### Measured values

`python domains.py`, both crystal structures, CVs bound to the 4AKE topology:

| CV | 1AKE (closed) | 4AKE (open) | \|Δ\| |
| --- | ---: | ---: | ---: |
| LID–CORE centroid distance (Å) | 20.98 | 30.81 | 9.83 |
| NMP–CORE centroid distance (Å) | 18.19 | 22.29 | 4.10 |
| θ_LID (deg) | 106.08 | 146.54 | 40.47 |
| θ_NMP (deg) | 44.31 | 73.01 | 28.69 |
| RMSD to 1AKE (Å) | 0.00 | 7.13 | 7.13 |
| RMSD to 4AKE (Å) | 7.13 | 0.00 | 7.13 |

θ_LID 106° → 147° and θ_NMP 44° → 73° reproduce the published values of
Beckstein et al. (≈105° → ≈150° and ≈45° → ≈75°), and the 7.1 Å Cα RMSD between
the endpoints matches the standard figure for this pair. That agreement is what
pins down the vertex group of each angle — the definitions are verified by the
numbers they produce, not merely copied.

The built system, in the same CVs:

| CV | 4AKE + H | after 200 ps equilibration |
| --- | ---: | ---: |
| LID–CORE (Å) | 30.81 | 29.53 |
| NMP–CORE (Å) | 22.29 | 22.08 |
| θ_LID (deg) | 146.54 | 143.84 |
| θ_NMP (deg) | 73.01 | 65.77 |
| RMSD to 1AKE closed (Å) | 7.13 | 6.13 |
| RMSD to 4AKE open (Å) | 0.00 | 2.27 |

The equilibrated frame is 2.3 Å from the open crystal structure and 6.1 Å from
the closed one: relaxed, still unambiguously open.

## Cost

Measured on this machine (Apple GPU via the OpenMM OpenCL platform, one
device), through `TrailsMDBackend` and `trails_md.bursts.run_bursts`:

| Workload | Wall clock | Throughput |
| --- | ---: | ---: |
| 200 ps equilibration (direct OpenMM) | 135 s | 128 ns/day |
| 4 replicas × 10 ps (one burst call) | 27.0 s | 128 ns/day aggregate |
| 4 replicas × 100 ps (one burst call) | 255.5 s | 135 ns/day aggregate |
| Smoke test: 2 replicas × 1.6 ps, incl. setup | 6.6 s | — |

The local execution backend serialises replicas onto the single GPU device, so
aggregate throughput equals single-replica throughput; a multi-GPU node would
scale replicas linearly. Extrapolating to the Stage 3 protocol at 4 replicas ×
100 ps per action execution: **≈256 s per execution**, so 20 repeats × 3 start
states = 60 executions is **≈4.3 h per action**, and the six-action vocabulary
plus the three baselines lands around **1.5–2 device-days**. Affordable on one
GPU; comfortable on a small cluster.

## Known risk for Stage 3

The apo open state is broad in GBn2. Over unbiased 100 ps bursts the LID–CORE
distance already samples 26–31 Å from a 29.5 Å start, i.e. the lid breathes
across a third of the 9.8 Å open-to-closed range on the timescale of a single
burst. Stage 3's `Unstable` outcome classifier and its basin radii have to be
calibrated against that spontaneous breathing, or an `open_hinge` success will
be indistinguishable from thermal noise. The θ_LID angle, which changes by 40°
between the endpoints, may separate the basins more sharply than the distance
does and is the fallback event coordinate.
