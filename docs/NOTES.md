# Project Notes: Planning Language for Controlled Molecular Dynamics

Living document. Tracks strategy, decisions, and open questions as the project evolves.
Companion to the two design docs at repo root:

- `A Planning Language for Controlled Molecular Dynamics.md` (vision)
- `Design and Implementation Plan_ A Planning Language for Controlled Molecular Dynamics.md` (WP1–WP7 plan)

---

## 2026-08-29 — Initial evaluation and publication strategy

### Assessment

**Core strengths**

- Real abstraction gap, correctly identified: nobody has given structural interventions
  stochastic, failure-aware semantics.
- "Formal ≠ physical compositionality" is a crisp, falsifiable, novel scientific question —
  science, not just engineering.
- Recipes as executable mechanistic hypotheses is the part biologists will care about.
- The substrate exists: Trails-MD supplies the short-burst runtime and committor validation
  machinery; PathGennie supplies target-directed search, SPIB learned CVs, OPES, and a
  proto-compiler (`RuleBasedController`).

**Main risks, ranked**

1. *Nature publishes discoveries, not languages.* A planning language per se lands at
   JCTC/PNAS/NeurIPS. Nature-family needs (a) a biological result the method found and
   experiments confirmed, or (b) a broadly enabling tool with multi-system validation
   (Nature Methods lane).
2. *Physics validity.* Biased interventions can produce non-Boltzmann artifacts. Reviewers'
   first attack: "scripted steered MD with extra vocabulary." Defense: every action outcome
   validated by relaxation plus committor/hitting statistics on unbiased dynamics. The
   Trails-MD `TabularCommittor` + `calibrate`/`heldout_bellman_residual` stack is the rigor
   anchor. Non-negotiable design principle.
3. *Compositionality may fail.* Δ_comp could be irreducibly large — a real but non-Nature
   finding. Mitigation: action-predictive abstraction refinement (WP3) turns failure into
   method.
4. *Cost.* Explicit-solvent proteins × swarms of bursts × recipes × repeat statistics.
   A naive GPCR benchmark is likely 10⁶+ GPU-hours. Budget honesty required.
5. *Competition timing.* (a) Generative transition-path samplers (diffusion/flow models)
   could leapfrog "find the path" value. (b) LLM agents driving simulations are arriving
   fast — but (b) is a friend, see below.

**The timely hook (not stated in the design docs):** this language is the natural action
space for an LLM scientist-agent. LLMs are bad at emitting bias potentials, good at emitting
"weaken interface, then open hinge, else explore." A runtime with physically grounded,
failure-aware semantics is the missing execution layer for autonomous molecular-mechanism
discovery. This framing elevates the work from "nice DSL" to "new way of doing computational
structural biology."

### Publication path: three staged papers, one killer app

**Paper 1 (now → ~9 mo): action semantics + compiler, adenylate kinase.** WP1+WP2.
~7 actions, two implementations each, outcome classifiers, repeated-execution outcome
distributions, committor-validated. One non-trivial result: two recipe orderings
(weaken-then-open vs open-then-weaken) produce measurably different pathway ensembles
matching/contradicting known AdK literature. Venue: JCTC or NeurIPS. Purpose: stake the
semantics claim, de-risk downstream.

**Paper 2 (~9–18 mo): physical compositionality.** WP3+WP4 on T4 lysozyme + calmodulin.
Measure Δ_comp systematically; show abstraction refinement shrinks it. If refinement works,
this carries a genuinely new scientific concept — Nature Computational Science plausible.
**Decision gate:** if Δ_comp is irreducibly large, pivot flagship ambition to Nature Methods
(tool paper) and stop investing in the compositionality theory.

**Paper 3 (18–36 mo): flagship — the method must find something.** Requirements: disputed
mechanism, checkable prediction, experimental collaborator. Underrated existing card:
`PathGennie/we/examples/1opj/` — Abl kinase–imatinib, WT vs N368S resistance mutant, with
an existing collaboration (the wepath manuscript group). Flagship shape:

- Competing mechanistic programs for kinase activation / drug unbinding
  (αC-helix vs P-loop routes).
- Runtime executes them; outcome statistics discriminate mechanisms; programs predict which
  mutations confer resistance by rerouting the mechanism.
- Experiments (kinase panel, DEER/NMR/HDX-MS) confirm predicted resistance mutations.

Claim: "Programmable mechanistic hypotheses predict drug-resistance mutations,
experimentally confirmed" — Nature/Nature Chemistry grade. Fallback killer apps: cryptic
pocket exposure for an undruggable target; GPCR biased-signaling mechanism. Either way the
wet-lab partner must be secured **by end of Paper 1** — experimental lead time dominates
the critical path.

**Optional amplifier:** LLM agent writes recipes autonomously, runtime executes, agent
revises from failure outcomes — closed loop discovering a mechanism no human recipe encoded.
Include only if it works cleanly.

### Decisions to make this month

1. ✅/☐ Commit to the rigor anchor (unbiased-dynamics validation for every action).
2. ☐ Start WP1 on AdK.
3. ☐ Open flagship-experiment conversation with the Abl collaborators.
4. Accept realistic odds: Nature Methods plausible; flagship Nature ~1-in-5 even if all
   works. Papers 1–2 solid regardless — bounded downside.

### Realistic distribution of outcomes

- Best case: flagship Nature via experimentally confirmed mechanistic prediction.
- Likely good case: Nature Methods tool paper + Nature Comp Sci compositionality paper.
- Floor: JCTC/NeurIPS papers on action semantics and planning — still respectable.

---

## Open questions

- Which AdK force field / starting structures (1AKE closed, 4AKE open)?
- Budget estimate for Paper 1 (GPU-hours per action × repeats).
- Who owns the outcome-classifier definitions — per-action code or declarative spec?

## Decision log

- **2026-08-29 — Repo layout:** the planning language lives in its own repo
  (PathwayPlanner), with Trails-MD and PathGennie as external backends behind
  adapter modules — the only code allowed to import them. Rationale: enforces
  the backend-agnostic claim, keeps paper artifacts separable, and PathGennie
  is a third-party repo anyway.
- **2026-08-29 — Stage 1 gate: PASS.** Wolfe-Quapp evaluation
  (`experiments/stage1/results.md`): outcome distributions reproducible across
  independent seed batches (JS divergence 0.044, gate 0.1); contract success
  rates calibrated on held-out runs (error 0.10, gate 0.2); success labels
  validated against the grid-exact reference committor (all successors at
  q = 1.0). First compositionality datum: a fine, channel-aware abstraction
  gives delta_comp 0.072 vs 0.277 for a coarse one-class abstraction —
  abstraction granularity measurably controls composition predictivity, as
  hypothesized. Proceed to Stage 2 (Trails-MD burst API + adapter).
- **2026-08-29 — PathGennie integrates as an action implementation, not a
  backend.** Examination of the PathGennie driver API showed no new library
  interface is needed upstream: `PathGennieDriver(engine, progress,
  convergence_fn).run(...)` already accepts a CV projection (ProgressVariable),
  an event predicate (convergence_fn, evaluated on full coordinates each
  cycle), a budget (max_cycle), and returns restartable successor
  configurations. Because the driver's output is one sequentially correlated
  anchor path (swarm -> softmax select -> commit, iterated), forcing it behind
  `Backend.run_bursts` would misrepresent it as an independent-replica
  ensemble. It is therefore exposed as a complete physical implementation of
  an action (`backends/pathgennie.py`: `run_driver_search` +
  `search_to_action_result`), supplying the unbiased selection-driven
  implementation family for WP1's two-implementations-per-action requirement;
  bias-based implementations come from the Trails-MD burst API. Consequence
  for the architecture: `Backend.run_bursts` covers primitive replica
  ensembles, while whole-search procedures enter through `Action.execute`
  overrides — the Implementation's selection policy rho is where the two
  families are distinguished.
- **2026-08-29 — Stage 2 gate: PASS.** Alanine dipeptide (vacuum Amber14,
  OpenMM CPU) through the Trails-MD burst API and TrailsMDBackend adapter
  (`experiments/stage2/results.md`). Equilibration settled at C7eq
  (-80, 81) deg; the biased `cross` action reached C7ax in 24/24 executions;
  all six tested successors gave rollout q_hat = 1.0 and persisted in B for a
  further 20 ps unbiased. The language layer ran unchanged from Stage 1 —
  only the backend and CV definitions differ. Cost datum for the Paper 1
  budget: 0.080 ns per cross execution; 1.58M integrator steps in 493 s
  wall-clock on CPU (per-walker process overhead dominates at this system
  size). Recorded limitations: the outcome distribution was degenerate
  (all successes), so reproducibility/calibration gates passed trivially;
  q_hat on first-entry frames is 1 partly by definition — a sharper
  committor validation on pre-entry transition-region frames is deferred to
  Stage 3, as is running the PathGennie implementation family on real MD.
  Supporting fixes from this stage: Trails-MD branch `burst-api` (burst API
  + OpenMM declarative bias) and branch `fix-committor-refinement`
  (pre-existing test failure root-caused to a torch-import BLAS/OpenMP
  runtime sensitivity on tie-broken k-means lattice data plus an
  over-strong all-cells gate; test-only fix, 325/325 green).
- **2026-08-30 — Z-channel result: composition is necessary, not only
  sufficient.** New toy landscape (`z_channel_potential`): a hairpin channel
  A=(0,0) -> (2,0) -> (2,1) -> B=(0,1) whose legs run +x, +y, -x, with the
  direct shortcut sealed by a ~40 kT wall. Because leg 1 and leg 3 have
  opposite x direction, any single linear CV has non-positive progress on one
  of them — single-CV failure holds by construction, not by tuning. Measured
  (`experiments/z_channel/results.md`, N=30 per strategy, equal budgets):
  single-CV actions 0/30 and 0/30 (net-direction bias pins against the wall;
  leg-1 bias stalls at the first corner as PARTIAL); the three-leg recipe
  with a separate CV per leg and a direction reversal succeeds 30/30. First
  demonstration that a high-level plan that changes direction mid-path is
  required and sufficient — the language's composition claim in its sharpest
  toy form. Candidate headline figure for Paper 1.
- **2026-08-30 — Ligand-unbinding benchmark selected: acetylcholinesterase /
  huperzine A.** The protein-scale instance of the Z-channel claim. The ~20
  Angstrom AChE gorge is curved and constricted, so the productive direction
  changes between the deep-gorge leg (breaking Trp86 stacking), the
  Tyr121/Phe330 constriction, and the exit past the peripheral anionic site —
  a single distance-to-exit CV fails at the constriction. Chosen over
  P450cam/camphor (richest pathway taxonomy, but protein-gated egress
  entangles the ligand-path question with a conformational one) and T4L
  L99A/benzene (cheapest and already Benchmark 2 here, but a compact cavity
  rather than a long curved tunnel). Decisive advantage: Rydzewski et al.,
  JCTC 2018, 14, 2843 supplies a published reference mechanism (front door
  plus an Omega-loop side door), a rate, and independent evidence that linear
  coordinates were inadequate — so the benchmark tests a real claim against
  external ground truth, including whether the side door is discovered as an
  `Alternative` outcome rather than scripted. Placed at Stage 3-4 on cost
  grounds (~530 residues, ~100k atoms solvated). Details in PLAN.md.
- **2026-08-30 — Trails-MD `burst-api` is a long-lived branch, not a merge
  candidate (user decision).** PathwayPlanner's Trails-MD backend depends on
  `trails_md.bursts` (the programmatic burst API plus the OpenMM declarative
  bias), which lives on that branch and is not being merged into Trails-MD's
  own line for now. Consequences to respect: every PathwayPlanner run and test
  that touches real MD must put the branch worktree first on `PYTHONPATH`
  (`/Users/rupak/Code/Trails-MD/.claude/worktrees/agent-a7e63d067fb172146`),
  and an editable-install path shadow means such commands must not run with
  `/Users/rupak/Code/Trails-MD` as the working directory, or the main
  checkout's `trails_md` (which has no `bursts.py`) wins. The adapter's lazy
  resolution of `run_bursts` keeps the unit tests independent of all this.
- **2026-08-30 — Stage 3 groundwork merged.** AdK system, Beckstein domain
  partition, hinges and all five CV spaces are on `main` (`361260f`),
  verified against published values (theta_LID 106->147 deg, theta_NMP
  44->73 deg, 7.13 A endpoint RMSD) with no PDB-to-literature numbering
  offset. Cost characterised at ~1.5-2 device-days for the six-action
  vocabulary, which closes the Paper 1 budget question. Two findings that
  constrain the action definitions: the open state breathes (LID-CORE spans
  24.3-32.5 A unbiased, a fifth of the endpoint range), so LID event specs
  should use theta_LID or RMSD rather than the centroid distance and no
  distance-based basin radius below ~4 A is safe; and committor validation
  must draw configurations from decorrelated sampling, not from biased
  trajectories alone, per the alanine dipeptide collinearity result.
- **2026-08-31 — First Stage 3 action complete: `open_hinge(LID)` on AdK.**
  Results in `experiments/adk/open_hinge_results.md`. Event: theta_LID
  advances >= 25 deg (chosen to clear the 8-11 deg thermal fluctuation).
  Four implementation conditions, 3 decorrelated closed start states, 10
  repeats each, 50 ps bursts of 4 replicas, equal cost per condition.
  Headline: **90/90 biased executions succeeded, 0/30 unbiased**
  (Clopper-Pearson intervals [0.94, 1.00] and [0.00, 0.12], disjoint). The
  null model is the load-bearing comparison, since apo AdK's closed state is
  off-equilibrium and the LID might have opened unaided; on this timescale
  it does not, so the intervention is doing the work rather than relabelling
  spontaneous motion. 14/15 tested openings survived 50 ps unbiased, so they
  are physical rather than bias artifacts. PARTIAL outcomes appear (4/30 at
  k=250, 1/30 in the null), so the outcome vocabulary is exercised rather
  than decorative. Cost: 6M steps = 24 ns for the matrix, 0.200 ns per
  execution, 343 min wall on one M3 Pro via OpenCL.
  What it does *not* establish, recorded to prevent over-claiming later: the
  sweep does not give a dose-response curve (k=1000 and k=2000 both saturate
  at 1.00, so the working range is bounded only from below, and resolving
  the turnover needs points *under* 250); the one heterogeneous cell (k=250,
  start state 0, 0.60) is explained by the relative event specification
  rather than by state dependence -- a >= 25 deg *advance* gives each start
  state a different absolute goal (142.7 / 135.6 / 132.9 deg), and success
  rate tracks that difficulty exactly, so the WP3 state-dependence question
  is untouched and needs an absolute event spec to test; and 50 ps of
  persistence does not demonstrate the open basin. Method note carried forward: the next sweep
  should extend downward in k, and repeats should return to the protocol's
  20 once the working range is known.
- **2026-08-31 — Implementation families are not interchangeable at a fixed
  budget (first WP2 datum on a protein).** `open_hinge(LID)` run by
  PathGennie's selection-driven driver, same event specification and same
  50,000 steps per execution as the biased family:
  **0 successes in 90 executions**, 95% CI [0.000, 0.040], against 1.00 for
  a restraint at k >= 1000 and 0.87 at k = 250. Cost was split three ways
  between swarm breadth and segment length and all three allocations
  returned zero, so this is a property of the method at this budget rather
  than of one configuration; nor is it a near miss (best advance 18.0 deg of
  the 25 required, median 5.7). Mechanism: selection can only amplify
  fluctuations that occur, so it needs the hinge to open by chance within a
  segment before it has anything to select, while a restraint supplies the
  free energy directly. On 50 ps the LID does not spontaneously sample a
  25 deg opening (the unbiased null agrees, 0/30), so selection inherits the
  null's failure at the same cost. This does *not* show selection cannot
  open the hinge; the open question is the budget at which the preference
  reverses, which is the natural follow-up experiment.
  Caveat of record: only integrator steps were matched, not wall clock --
  this family runs in-process on one OpenMM context while the biased family
  spawned a subprocess per replica.
  Adapter bug found while wiring the OpenMM engine and fixed before it could
  produce a wrong number: `run_driver_search` preferred `create_state`,
  which is unitless in PathGennie's toy engine but which the OpenMM engine
  forwards to `Context.setPositions`, where a bare array means nanometres --
  Angstrom coordinates would have been read as a tenfold expanded structure.
  It now uses `create_handle` throughout, with a test pinning the contract.
- **2026-08-31 — Why the selection-driven family fails, settled by two cheap
  probes (34 min total, against a 3 h experiment I nearly ran).**
  Probe 1 (`recon_ratchet_results.md`, `instrument_pathgennie.py`): the
  driver's `reject_worse_anchor` defaults to False, so the earlier 0/90 run
  had no ratchet. Enabling it did *not* rescue the search and in fact lowered
  peak advance (+8.6 vs +14.4 deg): with the anchor ratcheted into the tail
  of theta_LID's equilibrium distribution, 10 of 16 cycles had no trial
  exceed the anchor at all. This also refuted my stated mechanism -- I
  claimed excursions decay during the tau2 commit, but give-back averages
  +0.4 deg with a free anchor and commits often *improve* on the trial they
  extend. The mechanism is regression to the mean.
  Probe 2 (`recon_swarm_width_results.md`): tested that account's
  quantitative prediction, that best-of-m reach grows as sqrt(2 ln m).
  **It failed.** Max reach is flat in m (+6.7, +5.7, +5.6, +6.4 deg for
  m = 4..32) where 1.58x was predicted, and the pre-registered alternative
  holds instead: the m trials share a starting anchor and 5 ps does not
  decorrelate them, so they are not independent draws. What compounds is
  cycles, logarithmically -- peak advance fits 4.8 + 2.03 deg per doubling
  of cycles (R^2 0.94), extrapolating to ~10^3 cycles and ~100x budget
  (~25 ns per execution) to reach the 25 deg event, against 0.2 ns at which
  the restraint already succeeds every time.
  Conclusion for WP2: for this action on this system the selection-driven
  family is the wrong implementation by about two orders of magnitude in
  cost, and no allocation of a fixed budget rescues it. Method note: both
  probes were designed with a falsifiable prediction stated first; the
  second one failing is what produced the useful answer. Visualization of
  the per-cycle stall: https://claude.ai/code/artifact/1e7eb19b-091b-447e-866c-2ab05e5699d7

- **2026-09-01 — Audit of prior claims; one result superseded.** Reviewing
  decisions before further experiments turned up a material error and several
  overstatements. Corrections, most serious first:
  1. **`open_hinge(LID)`'s 90/90 result is superseded.** Re-measuring its saved
     trajectories showed the event frames at theta_LID 141.4 deg -- near the
     146.5 open crystal value -- while C-alpha RMSD to the open structure moved
     only 6.66 -> 5.06 A, roughly 40% of the way to the open basin at ~2.7 A.
     The one-coordinate event was satisfied by configurations that had left the
     closed state without arriving at the open one: exactly the defect later
     found in close_hinge, which I diagnosed there and then failed to check
     here. The action is being re-run with the conjunctive event.
  2. **The Stage 1 reproducibility gate was near-vacuous.** JS < 0.1 was
     compared against nothing; simulating the null shows two batches of 30 from
     the *same* distribution have median JS 0.019 and 90th percentile 0.061, so
     the reported 0.044 was an unremarkable draw. Replaced by a resampling
     p-value (`OutcomeModel.js_pvalue`). A p > 0.05 gate was then also wrong,
     failing 1 run in 20 by construction; the gate is p > 0.01, supported by a
     10-pair diagnostic (0/10 below 0.05, median p 0.30, batch success-rate
     sd 0.060 against a binomial 0.052). Reproducibility holds; the earlier
     evidence for it did not.
  3. **Z-channel wording.** The claim defeats every *linear* CV by
     construction, not every CV -- arc length along the polyline is a single
     nonlinear coordinate that would work. Code said "linear", prose summaries
     repeatedly dropped it. Scope note added to the results.
  4. **Relaxation tolerance** was DELTA_DEG (25 deg, ~2.5 sigma), under which a
     24 deg drift counted as stable. Tightened to 10 deg (~1 sigma).
  5. Narrowed, not corrected: delta_comp's coarse value is unstable across runs
     (0.277 and 0.540 for one configuration) because the estimator uses one
     representative per class; "conjunctive costs nothing in success rate" rests
     on 3/3 vs 3/3, which distinguishes almost nothing; "43% of the
     conformational change" used RMSD as a linear progress measure and the wrong
     denominator; and the PathGennie correlated-trials mechanism is inferred
     from flat max-reach, not measured directly.
  Method note: the audit was only possible because the burst API keeps
  trajectories on disk, which is the provenance argument for file-based
  transport paying off concretely.
- **2026-09-01 — The rigor anchor was never applied to AdK; Stage 3 committor
  experiment designed to fix that.** An audit prompted by the question "where
  are we using the committor machinery?" found: the grid-exact solver is used
  on toy landscapes, rollout counting on alanine dipeptide, and Trails-MD's
  `TabularCommittor` -- named in PLAN.md and NOTES.md as the non-negotiable
  rigor anchor -- in **zero lines of code**. On AdK the word appears twice, in
  comments about start-state decorrelation. Every AdK claim rests on
  relaxation persistence.
  Designed `docs/stage3-committor-experiment.md` to close this and to target
  a genuinely open question rather than a demonstration: estimate
  q(theta_LID, theta_NMP) and read the LID-first / NMP-first ordering off the
  shape of the q = 0.5 curve. Competing recipes cannot settle this -- they
  measure which restraint works, a fact about our biasing, which is the exact
  confound Huang, Ozkirimli & Post (JCTC 2009) identified when they found the
  progress-variable choice dominates outcomes more than method choice.
  Design points worth keeping: sampling must draw from several independent
  biasing directions, with the theta_LID/theta_NMP correlation as a *gate*
  (|r| < 0.7), because the alanine dipeptide analysis was retracted for
  exactly this confound at r = -0.855; estimation runs two routes, the cheap
  TabularCommittor surface on pooled bursts and expensive direct rollouts at
  a dozen cells, compared via `heldout_bellman_residual` and `calibrate`; and
  the decisive self-test is whether within-cell q-hat spread exceeds binomial
  noise, i.e. whether the committor is a function of these two coordinates at
  all. A negative there would be the more valuable result -- it would say the
  standard two-angle description of AdK is not a reaction coordinate.
  Correction recorded: I earlier described Jana et al. (JCP 2011, LID opens
  before NMP) and Beckstein et al. (JMB 2009, barrier on NMP, LID barrierless)
  as disagreeing. They are compatible -- easy LID opening, then a
  barrier-carrying NMP opening. The real disagreement is broader, e.g. Kerns
  et al. (NSMB 2015) decoupling lid opening from catalysis.
  Also recorded: PathGennie's ratcheting granularity is set by tau1/tau2, but
  matching DIMS needs a different architecture, not a retuning -- DIMS filters
  per step within one continuous trajectory (a rejection costs one step),
  while the swarm driver pays max_trial*tau1 + tau2 steps per rejected cycle.
