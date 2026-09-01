# Stage 3, action 1: open_hinge(LID) on adenylate kinase

Event: theta_LID advances by >= 25.0 deg. Bursts of 5000 steps x 4 fs = 20 ps, 2 replicas, 3 repeats from each of 2 decorrelated closed start states. Crystal endpoints: theta_LID 106 (closed) -> 146.5 (open) deg.

Start states: theta_LID = 113.2, 108.4 deg; LID-CORE = 22.0, 21.8 A.

## Outcome distributions

| implementation | success | per start state | RMSD to open reached | outcomes | steps |
| --- | --- | --- | --- | --- | --- |
| biased k=2000 kJ/mol/nm^2 | **1.00** | 1.00, 1.00 | 4.23 A (best 3.94) | {'success': 6} | 60,000 |
| unbiased (null model) | **0.00** | 0.00, 0.00 | - | {'failure': 6} | 60,000 |

Start RMSD to the open crystal is 6.68 A; the open basin sits near 2.7 A, so a complete opening would reach roughly that. The event requires a 2.0 A reduction, and the column above reports what was actually delivered -- the number the superseded run never measured.

## Does the intervention do any work?
- Biased success 1.00 vs unbiased 0.00 at equal cost (60,000 vs 60,000 steps).
- The bias raises the success rate materially above the null, so the intervention is doing work on this timescale.

## Relaxation persistence
- biased k=2000 kJ/mol/nm^2: 1/2 openings survived 20 ps unbiased.
- unbiased (null model): no openings to relax.

## Cost
- 120,000 integrator steps for the action matrix (0.5 ns); wall-clock 6 min.
- Per execution: 0.040 ns.
