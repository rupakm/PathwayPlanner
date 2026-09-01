# Stage 3 committor experiment: the isocommittor surface of adenylate kinase

Status: designed, not yet run. Supersedes nothing; this is new work that
should precede the remaining action vocabulary.

## Why this experiment, and why now

Two findings from the 2026-09-01 audit and the motion-planning literature
review put this ahead of the rest of Stage 3.

**The rigor anchor exists only on paper.** `docs/NOTES.md` records committor
validation on unbiased dynamics as a non-negotiable design principle, and
`docs/PLAN.md` names Trails-MD's `TabularCommittor` as the instrument. A grep
of the repository finds that estimator used in **zero lines of code**. The
committor work to date is a grid-exact solve on toy landscapes and a
rollout-counting profile on alanine dipeptide. On adenylate kinase — the
system the anchor was meant to protect — no committor has ever been computed,
and every claim rests on relaxation persistence.

**Competing recipes cannot settle a mechanism.** The plan proposes
discriminating LID-first from NMP-first ordering by running recipes in both
orders and comparing success rates. That measures which *biasing strategy*
works, which is a fact about our restraints rather than about the protein. It
is also exactly the confound Huang, Ozkirimli and Post (*JCTC* 5:1301, 2009)
identified when they found the progress-variable choice dominates outcomes
more than the method choice. A success-rate comparison cannot separate
mechanism from methodology.

The committor can. It is a property of a configuration under unbiased
dynamics, independent of how the configuration was produced or which
restraint drove the system there.

## The question, stated so it can be answered

Estimate q(theta_LID, theta_NMP) = P(reach open before closed) across the
plane spanned by the two hinge angles, and read the mechanism off the shape
of the q = 0.5 curve:

* A curve running **parallel to the theta_NMP axis at low theta_LID** means
  NMP motion barely changes commitment until the LID has opened. That is
  LID-first, quantitatively rather than by inspection of trajectories.
* A **diagonal** curve means the two domains are coupled and neither goes
  first.
* A curve **parallel to theta_LID** means NMP-first.

### What the literature says to expect

Jana, Adkar, Biswas and Bagchi (*J. Chem. Phys.* 134:035101, 2011) report
that the LID must open by some amount before NMP can begin, with an elliptic
two-dimensional free-energy contour indicating strong LID-NMP correlation.
Beckstein, Denning, Perilla and Woolf (*JMB* 394:160, 2009) place the barrier
on NMP with the LID barrierless. These are **compatible**, not competing: an
easy LID opening followed by a barrier-carrying NMP opening. An earlier note
in this repository described them as disagreeing; that was wrong.

The genuine disagreement is broader. Kerns et al. (*NSMB* 22:124, 2015) found
lid opening and catalysis decoupled, and single-molecule FRET (Aviram et al.,
*PNAS* 115:3243, 2018) puts opening at ~45 us against a much slower NMR
value. So "lid opening is rate-limiting" should be presented as the canonical
claim together with its challenge, not as settled.

**Prediction registered in advance:** if Jana and Beckstein are both right,
the q = 0.5 curve should run closer to parallel with the theta_NMP axis in
the low-theta_LID region, and turn diagonal once the LID is open. A curve
that is diagonal everywhere would contradict the LID-first picture.

## Design

### Sampling: avoid the confound that broke the alanine dipeptide analysis

The alanine dipeptide committor analysis produced configurations solely from
phi-biased trajectories, along which phi and psi were correlated at r = -0.855.
That dataset could not attribute the committor to either coordinate, and the
result had to be retracted. The same failure is available here and must be
designed out.

Configurations must therefore come from **several independent sources**, not
from one biased pull:

1. Restrained pulls on LID-CORE centroid distance (the existing `open_hinge`
   and `close_hinge` implementations).
2. Restrained pulls on NMP-CORE centroid distance, which move the plane in a
   different direction.
3. Unbiased bursts from both equilibrated endpoints, which populate the
   basins without any restraint.
4. Configurations restrained at *fixed* theta_LID while theta_NMP is sampled,
   and vice versa. These deliberately break the correlation, and are the
   points that make coordinate attribution possible at all.

The Pearson correlation between theta_LID and theta_NMP across the pooled
configurations is a **gate, not a diagnostic**: if it exceeds about 0.7 in
magnitude, the sampling has failed and the estimate must not be interpreted
as a function of two coordinates.

### Estimation: two routes, cheap and expensive

**Route A, the surface (Trails-MD `TabularCommittor`).** Pool the short
bursts, discretize the (theta_LID, theta_NMP) plane by k-means, count
transitions at a lag with mid-burst absorption at the two basins, and solve
the discrete Dirichlet problem directly. This is what the estimator was built
for and it needs no dedicated rollouts — it reuses trajectory data we are
generating anyway. It also carries its own uncertainty via Dirichlet-posterior
resolves, and reports NaN rather than a number for unvisited cells.

**Route B, validation at selected points (direct rollouts).** At a handful of
cells spanning q from near 0 to near 1, launch independent unbiased rollouts
with fresh Maxwell-Boltzmann velocities and count the fraction reaching open
before closed. This is the definition of the committor, and it is the
independent check on Route A.

Trails-MD supplies the machinery for exactly this comparison:
`heldout_bellman_residual` for out-of-sample consistency and `calibrate` for
the empirical hitting fraction against the learned q. Using them is the point
of the experiment as much as the mechanism is.

### The self-test that matters most

Before reading any mechanism off the surface, test whether the committor
**is a function of these two coordinates at all**. Within each populated
cell, take several configurations and estimate q̂ for each by direct rollout.
If the within-cell spread exceeds binomial sampling noise, then (theta_LID,
theta_NMP) does not determine the committor, and no shape of the q = 0.5
curve can be interpreted as a mechanism.

That outcome would be **more valuable than the ordering answer**. It would
say the standard two-angle description of adenylate kinase — used across the
literature reviewed here — is not a reaction coordinate, which is a
publishable negative result and a direct instance of this project's thesis
that event specifications, not sampling machinery, carry the leverage.

## Cost

Route A rides on trajectory data the action work already produces; the
estimator itself is a sparse linear solve and is free by comparison.

Route B is the expense. Distinguishing q = 0.5 from q = 0.3 needs of order 20
to 30 rollouts per configuration, and the within-cell test needs several
configurations per cell. A budget of roughly 3 configurations x 20 rollouts x
50 ps at a dozen validation cells is about 36 ns of unbiased dynamics, which
at the measured ~1.6 ps per second of wall clock is on the order of 6 hours
on one device — comparable to a single action sweep, and far below the ~25
hours a full rollout-only surface would cost.

The staging follows from that: run Route A first on existing data, use it to
choose the dozen cells where Route B is informative, and spend the rollouts
there.

## What could go wrong

* **Sampling correlation** exceeds the gate, in which case the surface is
  uninterpretable and more decorrelating restraints are needed first.
* **Basin definitions dominate the answer.** The committor depends on how
  open and closed are defined; the definitions must be fixed in advance and
  their sensitivity reported, not tuned after seeing the surface.
* **Implicit solvent** (GBn2, no hydrodynamic friction) means relative
  statements hold but rates do not transfer to experiment. The committor is a
  ratio and is more robust than a rate, but this is not a prediction of the
  experimental mechanism.
* **The plane may be insufficient**, per the self-test above. This is a
  likely outcome and is treated as a result, not a failure.

## Relation to prior art

Apaydin, Brutlag, Guestrin, Hsu and Latombe (WAFR 2002; *JCB* 10:257, 2003)
built Stochastic Roadmap Simulation, the only roadmap construction with a
proved Boltzmann limit, and computed P_fold — the committor — by first-step
analysis on a linear system, reporting four orders of magnitude less compute
than Monte Carlo for the same quantity. Their stated weakness is uniform
sampling in high dimension; they sketched the fix (importance sampling with
sampling-density-corrected transition probabilities) and left it as work
underway that was never published.

Our Route A is the same idea with a different discretization and better
sampling, on a real protein rather than a 6-to-12-dimensional secondary
structure model. Saying so in a related-work section is both accurate and to
our advantage.

Separately, the DIMS master identity is literally a weighted finite-time
committor estimator: the weighted average of the state-B indicator over paths
launched from a configuration. Zuckerman and Woolf only ever read a rate off
its slope, and under soft-ratcheting their weights degenerate — CHARMM's own
documentation says the scores "almost always" underflow, and no DIMS paper
reports a rate for any protein. The estimator has existed since 1999; what
was never solved is the weight distribution. That is the gap a splitting or
committor-refinement scheme closes.
