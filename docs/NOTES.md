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
  start state 0, 0.60) has interval [0.26, 0.88] and is a hint at the WP3
  state-dependence question, not evidence; and 50 ps of persistence does not
  demonstrate the open basin. Method note carried forward: the next sweep
  should extend downward in k, and repeats should return to the protocol's
  20 once the working range is known.
