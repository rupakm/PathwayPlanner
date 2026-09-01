# Stage 3, action 1: open_hinge(LID) on adenylate kinase

Event: theta_LID advances by >= 25.0 deg. Bursts of 12500 steps x 4 fs = 50 ps, 4 replicas, 10 repeats from each of 3 decorrelated closed start states. Crystal endpoints: theta_LID 106 (closed) -> 146.5 (open) deg.

Start states: theta_LID = 117.7, 110.6, 107.9 deg; LID-CORE = 21.6, 21.2, 20.9 A.

## Outcome distributions

| implementation | success | per start state | RMSD to open reached | outcomes | steps |
| --- | --- | --- | --- | --- | --- |
| biased k=1000 kJ/mol/nm^2 | **1.00** | 1.00, 1.00, 1.00 | 3.82 A (best 3.19) | {'success': 30} | 1,500,000 |
| biased k=2000 kJ/mol/nm^2 | **1.00** | 1.00, 1.00, 1.00 | 3.78 A (best 3.09) | {'success': 30} | 1,500,000 |
| biased k=4000 kJ/mol/nm^2 | **1.00** | 1.00, 1.00, 1.00 | 3.78 A (best 2.83) | {'success': 30} | 1,500,000 |
| unbiased (null model) | **0.00** | 0.00, 0.00, 0.00 | - | {'failure': 30} | 1,500,000 |

Start RMSD to the open crystal is 6.97 A; the open basin sits near 2.7 A, so a complete opening would reach roughly that. The event requires a 2.0 A reduction, and the column above reports what was actually delivered -- the number the superseded run never measured.

## Does the intervention do any work?
- Biased success 1.00 vs unbiased 0.00 at equal cost (1,500,000 vs 1,500,000 steps).
- The bias raises the success rate materially above the null, so the intervention is doing work on this timescale.

## Relaxation after the restraint is removed

Reported as a signed direction, not a pass/fail verdict. The progress
coordinate is s = RMSD(closed) - RMSD(open), so positive means nearer the
open reference; each trajectory supplies its own baseline at release.

| implementation | s at release | s after 50 ps | change | advancing |
| --- | --- | --- | --- | --- |
| k=1000 kJ/mol/nm^2 | +1.14 | -0.35 | -1.49 +/- 1.31 | 3/20 |
| k=2000 kJ/mol/nm^2 | +1.28 | -0.75 | -2.02 +/- 1.04 | 1/20 |
| k=4000 kJ/mol/nm^2 | +1.40 | -0.34 | -1.74 +/- 0.97 | 2/20 |

Every condition retreats: across 60 trajectories the ensemble moves from
+1.27 A on the open side to -0.48 A, a mean change of -1.75 A, with 54 of
60 moving back toward closed. The restraint delivers most of the structural
change and the system returns a substantial part of it on release.

**Why this is not reported as a persistence pass/fail, and why UNSTABLE is
not claimed.** Earlier versions of this experiment gated persistence on
coordinate drift. No threshold is defensible: theta_LID's own fluctuation is
8-11 deg and the measured mean drift over this window is 11.4 deg, so a
2.5-sigma tolerance passes almost everything and a 1-sigma tolerance fails
almost everything. Neither reports direction. The question is also ill-posed
for these configurations: at 3.78 A from the open crystal with the open basin
near 2.7 A, they lie on a gradient rather than in a basin, and such a
structure always relaxes.

Establishing that a structure has committed to a basin requires the
committor, estimated from trajectories long enough to reach one. Most of
these 50 ps trajectories reach neither basin -- they end near the midpoint,
4.81 A from open against 4.33 A from closed, with 19 of 60 still on the open
side. `UNSTABLE` is therefore not claimed here; it is reserved for a
committor-backed statement, which is the subject of the Stage 3 committor
experiment (`docs/stage3-committor-experiment.md`).

**Physical note.** Apo adenylate kinase's equilibrium is the open state, so a
systematic retreat from an opened structure is not what the thermodynamics
alone would suggest. Two explanations are open and are not distinguished by
these data: the restraint may over-strain the structures, or 50 ps may be too
short to observe the subsequent downhill relaxation toward open after an
initial elastic recoil.

## Cost
- 6,000,000 integrator steps for the action matrix (24.0 ns); wall-clock 289 min.
- Per execution: 0.200 ns.
