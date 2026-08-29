# Z-channel results: single CV vs direction-changing recipe

Parameters: kT=0.15, dt=1e-3, force=4.0, 3000 steps/leg, 4 replicas, N=30 runs/strategy; equal total budget (9000 steps of bias per execution). Success for every strategy: a frame inside the B disc (radius 0.25).

## (a) single CV, net A->B (+y)
- Outcomes: {'failure': 30}
- Success rate: **0.00**; mean cost 36,000 steps/run

## (b) single CV, leg-1 (+x)
- Outcomes: {'partial': 30}
- Success rate: **0.00**; mean cost 36,000 steps/run

## (c) three-leg recipe (+x, +y, -x)
- Outcomes: {'success': 30}
- Success rate: **1.00**; mean cost 36,000 steps/run

## Verdict
- Best single-CV success: 0.00 (gate: <= 0.1); recipe success: 1.00 (gate: >= 0.7).
- Gate: PASS — a plan that changes direction mid-path, with a separate CV per leg, is required and sufficient on this landscape.
