# Does a wider swarm reach further into the tail?

Start theta_LID = 110.6 deg, event threshold 135.6 deg (advance 25.0). Every execution spends 50,000 steps with tau1 = tau2 = 5 ps and the ratchet on, so swarm width is bought with cycles. 3 repeats per width.

| trials m | cycles | mean best-trial reach | max reach | mean peak advance | max peak | successes | predicted reach |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 8 | +1.5 deg | +6.7 | +10.8 deg | +11.4 | 0/3 | +1.5 deg |
| 8 | 4 | +2.8 deg | +5.7 | +9.5 deg | +15.0 | 0/3 | +1.8 deg |
| 16 | 2 | +3.9 deg | +5.6 | +6.0 deg | +9.6 | 0/3 | +2.1 deg |
| 32 | 1 | +5.6 deg | +6.4 | +5.2 deg | +6.4 | 0/3 | +2.3 deg |

`Predicted reach` scales the m=4 measurement by sqrt(ln m / ln 4), the growth of the expected maximum of m Gaussian draws. Agreement supports the regression-to-the-mean account of the stall; a flat or slower curve means the trials are not independent draws -- 5 ps segments starting from the same anchor are correlated, which would cap the benefit of widening the swarm.

Cost: 536,250 steps in 21 min.

## The prediction failed; the pre-registered alternative holds

**Max best-trial reach is flat in m**: +6.7, +5.7, +5.6, +6.4 deg for
m = 4, 8, 16, 32. Widening the swarm eightfold did not extend the tail at
all, against a predicted 1.58x. The alternative stated before the run is
what happened: the m trials all start from the *same* anchor
configuration and 5 ps is too short to decorrelate from it, so they are
not independent draws and sampling more of them reaches no further.

The comparison is fair on trial count. m=4 over 8 cycles and m=32 over 1
cycle both spend 32 trials per run, and both top out near +6 deg.

**Ignore the mean-reach column.** It rises (+1.5 -> +5.6) only as an
artifact of how it is measured: reach is taken from the anchor each cycle
started from, so the m=4 mean is diluted by seven later cycles whose
anchor had already ratcheted up, while m=32 contributes a single
measurement from the original start. Max reach is the statistic that
compares like with like, and it is flat.

## What does compound: cycles, slowly

Peak advance *falls* as the swarm widens -- +10.8, +9.5, +6.0, +5.2 deg --
because at fixed budget trials are bought with cycles, and it is the
cycles that accumulate. Iteration compounds where swarm width does not:
one wide selection round reaches +5.2 deg, while eight narrow rounds
reach +10.8 from the same total trials.

The compounding is logarithmic. Fitting peak advance against log2(cycles)
over the four widths gives 4.8 + 2.03 deg per doubling (R^2 = 0.94).
Extrapolated, the 25 deg event needs of order 10^3 cycles, i.e. roughly
100x the current per-execution budget -- about 25 ns of dynamics per
execution, against the 0.2 ns at which the restraint already succeeds in
every attempt.

Treat that number as an order of magnitude: it extrapolates two decades
beyond four points with three repeats each, and the fit assumes the
logarithmic law continues rather than flattening further as the anchor
climbs into a steeper part of the free-energy surface, which would make
it an underestimate.

## Practical conclusion

Widening the swarm is counterproductive at fixed budget, and the lever
that does work -- more cycles -- buys progress only logarithmically. For
this action, on this system, the selection-driven family is the wrong
implementation by roughly two orders of magnitude in cost, and no
allocation of a fixed budget rescues it. That is a stronger and better
supported version of the original 0/90 result: not "it did not happen to
work", but "here is the scaling that says it cannot at this cost, and
here is the measurement that rules out the obvious fix".
