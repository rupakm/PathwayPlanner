# open_hinge(LID): selection-driven search (PathGennie)

Same event as the biased run: theta_LID advances by >= 25.0 deg. Every execution spends 50,000 steps, cost-matched to one biased execution (4 replicas x 12500 steps), allocated three ways between swarm breadth and segment length. 10 repeats from each of 3 start states.

Start states: theta_LID = 117.7, 110.6, 107.9 deg.

| allocation | cycles | success | per start state | median advance (deg) | outcomes |
| --- | --- | --- | --- | --- | --- |
| broad swarm, 5 ps segments | 8 | **0.00** | 0.00, 0.00, 0.00 | 5.7 | {'budget_exceeded': 30} |
| narrow swarm, 10 ps segments | 6 | **0.00** | 0.00, 0.00, 0.00 | 3.0 | {'budget_exceeded': 30} |
| wide swarm, 5 ps segments | 4 | **0.00** | 0.00, 0.00, 0.00 | 4.8 | {'budget_exceeded': 30} |

## Comparison with the other families, at equal cost

| family | mechanism | success |
| --- | --- | --- |
| biased k>=1000 | restraint on the Hamiltonian | 1.00 |
| biased k=250 | restraint on the Hamiltonian | 0.87 |
| selection-driven | unbiased segments, biased ensemble | 0.00 |
| unbiased null | none | 0.00 |

Final theta_LID advance over all 90 executions: median 5.7 deg, best
18.0 deg, against the 25.0 deg the event requires. No execution of any
allocation came within 7.0 deg of the threshold.

Cost: 4,500,000 steps (18.0 ns) across 90 executions in 183 min.
(An earlier draft of this line reported 1.5M, counting one allocation
rather than all three; the script is corrected.)

Note on what 'unbiased' means here: each committed segment is ordinary Langevin dynamics and is individually Boltzmann valid, so no trajectory is distorted. Selection still skews the *ensemble* toward opening, so this family is not a source of equilibrium statistics -- it is a search whose artifacts differ in kind from a restraint's, not one that has none.

## Reading

0 successes in 90 executions is a 95% Clopper-Pearson interval of
[0.000, 0.040]: at this budget the selection-driven family opens the LID
in under 4% of attempts, against 1.00 for a restraint of k >= 1000 and
0.87 at k = 250, spending identical steps.

The allocation sweep is what licenses that statement. Cost was fixed and
split three ways between swarm breadth and segment length, and all three
returned zero, so the failure is a property of the method at this budget
rather than of one badly chosen configuration. Nor is it a near miss:
the best single execution advanced 18.0 deg of the 25 required, and the
median advanced 5.7.

The mechanism is straightforward, and worth stating because it predicts
where the boundary lies. Selection can only amplify fluctuations that
actually occur: the driver picks the most-advanced of `max_trial` short
trials, so it needs the hinge to open by chance within a segment before
it has anything to select. A restraint does not wait for chance -- it
supplies the free energy directly. On a 50 ps budget the LID does not
spontaneously sample a 25 deg opening (the unbiased null found the same,
0/30), so selection has nothing to work with and inherits the null's
failure while paying the same cost.

This does not show that selection-driven search cannot open this hinge.
It shows the two families are not interchangeable at a fixed small
budget, which is the WP2 implementation-selection question answered in
its first real instance on a protein: an action compiler choosing
between these implementations at 50 ps should choose the restraint, and
the interesting follow-up is the budget at which that preference
reverses.

## Caveats

* Only the budget was matched, not the wall-clock cost: this run is
  in-process on one OpenMM context while the biased run spawned a
  subprocess per replica, so the two families' minutes are not
  comparable even though their integrator steps are.
* Segment lengths of 5-10 ps were chosen to fit 4-8 selection cycles
  into the matched budget. A larger budget would allow both longer
  segments and more cycles, and the two effects are not separated here.
* `theta_LID` scores the trials, so this tests selection on the event
  coordinate itself -- the most favourable case for the method. A
  learned or less well-aligned progress coordinate would do no better.
