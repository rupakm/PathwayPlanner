# Stage 3, action 2: close_hinge(LID) on adenylate kinase

Event: theta_LID DECREASES by >= 25.0 deg (uphill). Bursts of 5000 steps x 4 fs = 20 ps, 2 replicas, 3 repeats from each of 2 decorrelated open start states. Crystal endpoints: theta_LID 146.5 (open) -> 106.1 (closed) deg.

Start states: theta_LID = 136.0, 141.7 deg; LID-CORE = 28.4, 29.9 A.

## Outcome distributions

| implementation | success | per start state | outcomes | steps |
| --- | --- | --- | --- | --- |
| biased k=2000 kJ/mol/nm^2 | **1.00** | 1.00, 1.00 | {'success': 6} | 60,000 |
| unbiased (null model) | **0.00** | 0.00, 0.00 | {'failure': 6} | 60,000 |

## Does the intervention do any work?
- Biased success 1.00 vs unbiased 0.00 at equal cost (60,000 vs 60,000 steps).
- The bias raises the success rate materially above the null, so the intervention is doing work on this timescale.

## Relaxation persistence
- biased k=2000 kJ/mol/nm^2: 2/2 openings survived 20 ps unbiased.
- unbiased (null model): no openings to relax.

## Cost
- 120,000 integrator steps for the action matrix (0.5 ns); wall-clock 6 min.
- Per execution: 0.040 ns.
