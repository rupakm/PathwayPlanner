# Committor profile across the alanine dipeptide barrier

Parameters: 14 biased seeding bursts (k=40.0 kJ/mol/rad^2, 10000 steps), 20 unbiased rollouts of 10000 steps per representative, basin radius 40.0 deg. A basin center [-79.3  50.2] deg, B = C7ax (np.float64(72.0), np.float64(-65.0)) deg.

| phi (deg) | pass | region | q_hat | B | A | unresolved |
| --- | --- | --- | --- | --- | --- | --- |
| -54.4 | coarse | A | 0.00 | 0 | 20 | 0 |
| -40.7 | coarse | A | 0.00 | 0 | 20 | 0 |
| -38.0 | coarse | transition | 0.00 | 0 | 20 | 0 |
| -27.3 | coarse | transition | 0.00 | 0 | 20 | 0 |
| -14.0 | coarse | transition | 0.00 | 0 | 20 | 0 |
| -5.1 | coarse | transition | 0.00 | 0 | 20 | 0 |
| 4.0 | coarse | transition | 0.00 | 0 | 20 | 0 |
| 14.0 | coarse | transition | 0.00 | 0 | 20 | 0 |
| 14.1 | refined | transition | 0.00 | 0 | 40 | 0 |
| 15.7 | refined | transition | 0.00 | 0 | 40 | 0 |
| 17.9 | refined | transition | 0.00 | 0 | 40 | 0 |
| 19.8 | refined | transition | 0.00 | 0 | 40 | 0 |
| 21.6 | refined | transition | 0.00 | 0 | 40 | 0 |
| 22.4 | refined | transition | 0.00 | 0 | 40 | 0 |
| 23.7 | coarse | transition | 1.00 | 20 | 0 | 0 |
| 37.3 | coarse | transition | 1.00 | 20 | 0 | 0 |
| 47.8 | coarse | B | 1.00 | 20 | 0 | 0 |
| 56.9 | coarse | B | 1.00 | 20 | 0 | 0 |
| 64.5 | coarse | transition | 1.00 | 20 | 0 | 0 |
| 72.4 | coarse | B | 1.00 | 20 | 0 | 0 |
| 81.8 | coarse | B | 1.00 | 20 | 0 | 0 |
| 91.4 | coarse | transition | 1.00 | 20 | 0 | 0 |

Crossing bracketed by the coarse pass to phi in [14.0, 23.7] deg; refined pass sampled inside it.

- Rank correlation of q_hat with phi: **0.62** (gate: > 0.7) — FAIL
- SUCCESS-labelled frames with q_hat > 0.5: 4/4 — PASS
- Transition-region frames with 0.1 < q_hat < 0.9: 0/16 — FAIL

### Is phi alone the reaction coordinate?
- phi 22.4 deg (q_hat 0.00) vs phi 23.7 deg (q_hat 1.00): 1.3 deg apart in phi, 1.00 apart in q_hat; psi = 20 vs -41 deg.
- Conclusion: **no** — configurations that agree in phi disagree in committor, so the biasing coordinate is not the reaction coordinate even on this system, where phi is conventionally treated as sufficient.

Wall-clock 1405 s.

## Gate: FAIL
