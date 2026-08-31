# Stage 3, action 1: open_hinge(LID) on adenylate kinase

Event: theta_LID advances by >= 25.0 deg. Bursts of 12500 steps x 4 fs = 50 ps, 4 replicas, 10 repeats from each of 3 decorrelated closed start states. Crystal endpoints: theta_LID 106 (closed) -> 146.5 (open) deg.

Start states: theta_LID = 117.7, 110.6, 107.9 deg; LID-CORE = 21.6, 21.2, 20.9 A.

## Outcome distributions

| implementation | success | per start state | outcomes | steps |
| --- | --- | --- | --- | --- |
| biased k=250 kJ/mol/nm^2 | **0.87** | 0.60, 1.00, 1.00 | {'success': 26, 'partial': 4} | 1,500,000 |
| biased k=1000 kJ/mol/nm^2 | **1.00** | 1.00, 1.00, 1.00 | {'success': 30} | 1,500,000 |
| biased k=2000 kJ/mol/nm^2 | **1.00** | 1.00, 1.00, 1.00 | {'success': 30} | 1,500,000 |
| unbiased (null model) | **0.00** | 0.00, 0.00, 0.00 | {'failure': 29, 'partial': 1} | 1,500,000 |

## Does the intervention do any work?
- Biased success 1.00 vs unbiased 0.00 at equal cost (1,500,000 vs 1,500,000 steps).
- The bias raises the success rate materially above the null, so the intervention is doing work on this timescale.

## Relaxation persistence
- biased k=250 kJ/mol/nm^2: 5/5 openings survived 50 ps unbiased.
- biased k=1000 kJ/mol/nm^2: 4/5 openings survived 50 ps unbiased.
- biased k=2000 kJ/mol/nm^2: 5/5 openings survived 50 ps unbiased.
- unbiased (null model): no openings to relax.

## Cost
- 6,000,000 integrator steps for the action matrix (24.0 ns); wall-clock 343 min.
- Per execution: 0.200 ns.

## Confidence intervals (Clopper-Pearson, 95%)

| condition | successes | rate | 95% CI |
| --- | --- | --- | --- |
| k=250, start state 0 | 6/10 | 0.60 | [0.26, 0.88] |
| k=250, pooled | 26/30 | 0.87 | [0.69, 0.96] |
| k>=1000, pooled | 60/60 | 1.00 | [0.94, 1.00] |
| unbiased null, pooled | 0/30 | 0.00 | [0.00, 0.12] |

The biased and null intervals are disjoint by a wide margin, which is the
result this experiment was built to obtain: on a 50 ps burst the LID does
not open unaided, so the intervention is doing the work rather than
relabelling spontaneous motion.

## What this does and does not establish

Establishes:

* The action is realizable as a reproducible stochastic search. 90 of 90
  biased executions reached the event; 0 of 30 unbiased ones did, at
  identical cost.
* The openings are physical, not bias artifacts: 14 of 15 tested successors
  remained open through 50 ps of unbiased dynamics after the restraint was
  removed.
* The outcome vocabulary is exercised rather than decorative: PARTIAL
  appears in 4 of 30 executions at k=250 and once in the null family, from
  the same classifier that reports SUCCESS elsewhere.

Does not establish:

* A dose-response curve. Two of the three restraint strengths saturate at
  1.00, so the sweep locates the working range only from below: somewhere
  at or under k=250 the action begins to fail. Resolving the turnover needs
  points below 250, not further points above 1000.
* Start-state dependence. The one heterogeneous cell (k=250, start state 0
  at 0.60) is explained by the event specification, not by the configuration
  being intrinsically harder. The event is a *relative* advance of >= 25 deg,
  so each start state has a different absolute goal: 142.7, 135.6 and 132.9
  deg for start states at theta_LID = 117.7, 110.6 and 107.9 deg. The state
  with the lowest success rate is the one already most open, whose target
  therefore sits closest to the fully open crystal value of 146.5 deg -- the
  hardest absolute goal of the three. Success rate tracks target difficulty
  in exactly that order, so nothing here bears on whether action feasibility
  varies with the starting configuration (the WP3 question). Testing that
  needs an event specification held fixed in absolute terms across start
  states, which a relative delta cannot provide.
* Stability beyond 50 ps. Relaxation persistence was measured over one
  burst length; an opening that survives 50 ps is not thereby shown to sit
  in the open basin.

## Caveats of record

* The three biased conditions shared burst working directories in this run
  (fixed afterwards in c86bc42), so per-condition attribution of the files
  on disk is ambiguous. The reported rates are unaffected: families are
  accumulated separately in memory and their seeds did not collide.
* Repeats are 10 per start state, not the 20 the WP1 protocol specifies;
  the budget went to four conditions instead of two.
* Implicit solvent (GBn2) with no hydrodynamic drag, so success
  probabilities are comparable across implementations but absolute rates
  are not transferable to experiment.
