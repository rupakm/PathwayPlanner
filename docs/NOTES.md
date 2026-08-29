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
