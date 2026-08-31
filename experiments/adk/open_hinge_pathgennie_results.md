# open_hinge(LID): selection-driven search (PathGennie)

Same event as the biased run: theta_LID advances by >= 25.0 deg. Swarm of 4 trials x 5 ps, commit 5 ps, up to 8 cycles = 50,000 steps per execution -- cost-matched to one biased execution (4 replicas x 12500 steps). 2 repeats from each of 1 start states.

Start states: theta_LID = 117.7 deg.

| implementation | success | per start state | outcomes |
| --- | --- | --- | --- |
| selection-driven (PathGennie) | **0.00** | 0.00 | {'budget_exceeded': 2} |

## Comparison with the other families, at equal cost

| family | mechanism | success |
| --- | --- | --- |
| biased k>=1000 | restraint on the Hamiltonian | 1.00 |
| biased k=250 | restraint on the Hamiltonian | 0.87 |
| selection-driven | unbiased segments, biased ensemble | 0.00 |
| unbiased null | none | 0.00 |

Final theta_LID advance: median 5.8 deg, range 0.8 to 10.7 deg (the event needs 25.0).

Cost: 100,000 steps (0.4 ns) in 4 min.

Note on what 'unbiased' means here: each committed segment is ordinary Langevin dynamics and is individually Boltzmann valid, so no trajectory is distorted. Selection still skews the *ensemble* toward opening, so this family is not a source of equilibrium statistics -- it is a search whose artifacts differ in kind from a restraint's, not one that has none.
