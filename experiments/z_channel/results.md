# Z-channel results: single linear CV vs direction-changing recipe

Parameters: kT=0.15, dt=1e-3, force=4.0, 3000 steps/leg, 4 replicas, N=10 runs/strategy; equal total budget (9000 steps of bias per execution). Success for every strategy: a frame inside the B disc (radius 0.25).

## (a) single linear CV, net A->B (+y)
- Outcomes: {'failure': 10}
- Success rate: **0.00**; mean cost 36,000 steps/run

## (b) single linear CV, leg-1 (+x)
- Outcomes: {'partial': 10}
- Success rate: **0.00**; mean cost 36,000 steps/run

## (c) three-leg recipe (+x, +y, -x)
- Outcomes: {'success': 10}
- Success rate: **1.00**; mean cost 36,000 steps/run

## Verdict
- Best single-CV success: 0.00 (gate: <= 0.1); recipe success: 1.00 (gate: >= 0.7).
- Gate: PASS — a plan that changes direction mid-path, with a separate CV per leg, is required and sufficient on this landscape.

Scope of the claim. This defeats every *linear* CV by construction, since legs 1 and 3 have opposite x direction. It does not defeat all single coordinates: arc length along the polyline is one nonlinear CV that would drive the whole path. The landscape was also engineered to make the point, so it is an existence proof that composition can be necessary, not evidence about how often real systems are like this.
