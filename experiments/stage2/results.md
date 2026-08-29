# Stage 2 results (alanine dipeptide, vacuum Amber14, OpenMM CPU)

Parameters: n_steps=10000 (dt=2 fs), replicas=4, batches of 12, bias k=40.0 kJ/mol/rad^2 on phi, basin radius 40.0 deg, B=C7ax (np.float64(72.0), np.float64(-65.0)).

## A. Equilibration
- Start (phi, psi) = [180. 180.]; settled A basin center = [-79.9  80.8] deg.

## B/C. Reproducibility and calibration (cross action)
- Batch 1 outcomes: {'success': 12}
- Batch 2 outcomes: {'success': 12}
- JS divergence: **0.0000** (gate: < 0.1) — PASS
- Calibration error: **0.000** (gate: < 0.2) — PASS

## D. Committor rollout validation of success labels
- Successor 0: hits B=6, A=0, unresolved=0
- Successor 1: hits B=6, A=0, unresolved=0
- Successor 2: hits B=6, A=0, unresolved=0
- Successor 3: hits B=6, A=0, unresolved=0
- Successor 4: hits B=6, A=0, unresolved=0
- Successor 5: hits B=6, A=0, unresolved=0
- q_hat per successor: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]; median 1.00 (gate: > 0.5) — PASS

## E. Relaxation persistence
- 6/6 success successors stable under relax (gate: >= 0.5) — PASS

## Cost
- Total integrator steps: 1,580,000; wall-clock 493 s.
- Per cross execution: 40,000 steps (0.080 ns).

## Stage 2 gate: PASS

## Limitations of this evaluation (analysis notes)

1. The outcome distribution is degenerate: at k=40 kJ/mol/rad^2 and 20 ps,
   all 24 cross executions succeeded, so the reproducibility and calibration
   gates pass trivially. They verify machinery, not statistical behavior; a
   weaker bias regime with mixed outcomes is needed for a discriminating
   version of metrics 1-2 on this system.
2. The rollout q_hat = 1.0 values are partly by construction: success
   successors are first-entry frames already inside the B disc, and a state
   inside the absorbing boundary has q = 1 by definition. The physically
   informative content is that no rollout fell back to A and that all
   successors persisted in B for a further 20 ps unbiased (phase E). A
   sharper committor validation would evaluate q_hat on pre-entry
   transition-region frames; deferred to Stage 3.
3. Single implementation family exercised (biased bursts via Trails-MD).
   The PathGennie selection-driven family was validated on its toy engine
   in the adapter tests; running it on this MD system requires its OpenMM
   backend setup and is deferred.

## Acceptance criterion: language layer unchanged

The language layer (actions/, outcomes/, recipes/, evaluation/, cv.py) is
identical to the Stage 1 code; this evaluation introduced only this script.
The same CrossAction/ChannelClassifier/RelaxAction/estimator pattern ran
against real OpenMM dynamics through the TrailsMDBackend adapter.
