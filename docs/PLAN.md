# Implementation and Evaluation Plan

Concrete staged plan for the PathwayPlanner package, mapped to the scaffold
(commit `81cdb83`) and the publication strategy in [NOTES.md](NOTES.md).
Work packages WP1–WP7 refer to the
[Design and Implementation Plan](Design%20and%20Implementation%20Plan_%20A%20Planning%20Language%20for%20Controlled%20Molecular%20Dynamics.md).

Dates below are offsets from project start (2026-09).

---

## Stage 0 — Scaffold (done, 2026-08-29)

Language core (states, actions, outcomes, compiler, recipe combinators,
contracts), Backend protocol, 2D Langevin toy backend, import-guarded
Trails-MD/PathGennie adapter stubs. 14 tests green with no MD engine.

---

## Stage 1 (weeks 1–4): Semantics validation on toy systems

No proteins. Prove the language semantics are coherent where ground truth
exists.

**Implement**

- `relax()` action: unbiased bursts plus a stability check.
- Alternative-outcome detection: channel classification on Wolfe–Quapp and
  three-hole potentials (multiple saddle channels give a natural
  Success-vs-Alternative testbed).
- Outcome-distribution estimator: run an action/recipe N times, build the
  empirical P(o, s' | s, a); wire into `RecipeContract`.
- Δ_comp harness: compare predicted ∫ P(C | s, P2) dP_P1(s | A) against
  empirical P(C | A, P1;P2) for two-step toy recipes.
- Ground truth via the Trails-MD toy stack: grid-exact reference committor
  validates "success" labels physically.

**Evaluate**

- Outcome-distribution reproducibility: JS divergence between independent
  seed batches below threshold.
- Contract calibration: recorded success rate predicts held-out runs.
- Δ_comp measured with deliberately coarse vs fine abstractions — first
  (cheap) data on the compositionality question.

**Gate:** semantics coherent and reproducible on toys; otherwise fix the
language before touching MD.

---

## Stage 2 (weeks 3–8, overlapping): Trails-MD burst API and backend adapter

- In Trails-MD (on a branch): a programmatic
  `run_bursts(start_frames, bias_spec, n_steps, n_replicas) -> trajectories`
  API extracted from the `WalkerTask`/execution machinery, bypassing
  YAML/CLI. Independently useful to Trails-MD.
- `backends/trailsmd.py` adapter implementing the `Backend` protocol;
  configuration handles are frame references (lineage machinery in
  `trails_md/paths.py`).
- Bias support: an OpenMM `CustomCVForce`-based restraint/pull spec as the
  first intervention type.
- **PathGennie adapter (done 2026-08-29, commit `e298f29`):** integrated at the
  driver level, not behind the `Backend.run_bursts` protocol. The PathGennie
  driver (swarm of tau1 trials, softmax selection, tau2 commit, iterated to
  convergence) produces one sequentially correlated anchor path rather than an
  independent-replica ensemble, so it constitutes a complete physical
  implementation of an action — it realizes the selection policy rho
  internally. `backends/pathgennie.py` exposes `DriverSearchSpec` (projection,
  event predicate on coordinates, optional CV target selecting
  TargetMetric/EscapeMetric, driver parameters), `run_driver_search` (budget
  caps the cycle count via the per-cycle step cost), and
  `search_to_action_result` (convergence -> SUCCESS; non-convergence ->
  BUDGET_EXCEEDED with the final anchor as successor). No upstream PathGennie
  change was required: its programmatic driver API is sufficient, with the
  event predicate serving as `convergence_fn`.

**Evaluate:** alanine dipeptide — `explore` and `cross` actions over phi/psi.
Same metrics as Stage 1, plus committor validation via `TabularCommittor` +
`calibrate` on unbiased dynamics. The semantics must transfer from toy to
real MD unchanged.

---

## Stage 3 (weeks 6–16): WP1 action vocabulary on adenylate kinase

- Actions: `open_hinge`/`close_hinge` (LID, NMP), `weaken_interface(LID, CORE)`,
  `rotate_domain(LID)`, `explore`, `relax`.
- Event specs: LID–CORE pseudo-dihedral / hinge angle, interface contact
  counts, RMSD to 1AKE (closed) / 4AKE (open).
- Two implementations per action (design-doc requirement):
  (a) biased-CV bursts via the Trails-MD backend (`CustomCVForce`);
  (b) unbiased selection-driven search via the PathGennie driver adapter
  (`run_driver_search`) — the two families differ in mechanism (bias force
  vs trial selection), which is exactly the comparison the action compiler
  must learn to make.
- Outcome classifiers including `Unstable` (relaxation reverts the event)
  and `Alternative` (a different transition detected).

**Evaluate, per action:** at least 20 repeats from at least 3 start states.

- Success probability with bootstrap confidence intervals.
- Outcome-distribution stability across seeds.
- Physical validity: post-relaxation persistence plus committor/hitting
  calibration on unbiased dynamics — the rigor anchor, non-negotiable.
- Cost in GPU-hours.
- Implementation comparison (a) vs (b).

**Baselines:** plain steered MD on the same CV (pre-empts the "scripted SMD
with extra vocabulary" critique with data); the Trails-MD committor spawner;
the PathGennie driver targeting the open state.

**Gate:** at least 4 actions reproducible and physically valid on AdK. If
only biased implementations work, that is Paper 1 content too, reframed.

---

## Stage 4 (weeks 14–24): Recipes and the Paper 1 experiment

- The `open_LID` recipe in both orderings: weaken-then-open vs
  open-then-weaken. Compare pathway ensembles against the AdK literature
  debate (rigid-body vs cracking; NMP-first vs LID-first ordering).
- Δ_comp for two-step AdK recipes — first real-protein compositionality
  numbers (seeds Paper 2).
- Deliverable: Paper 1 draft (JCTC or NeurIPS) — stochastic action semantics
  plus the AdK demonstration.

---

## Cross-cutting

- Budget estimate due at the end of Stage 2 (per-action GPU-hours × repeats);
  feeds the NOTES.md decision list.
- In parallel, zero compute: open the Abl-collaborator conversation for the
  flagship experiment (experimental lead time dominates the critical path).
- Every stage ends with a NOTES.md decision-log entry.

## Metric definitions (shared across stages)

| Metric | Definition |
| --- | --- |
| Success probability | Fraction of executions with Outcome = Success, bootstrap CI |
| Reproducibility | JS divergence between outcome distributions of independent seed batches |
| Physical validity | Event persists after `relax()`; committor/hitting calibration on unbiased dynamics |
| Δ_comp | \|p_actual − p_pred\| for composed recipes (full-distribution variant: JS divergence) |
| Cost | GPU-hours (toy: integrator steps) per execution |
| Pathway diversity | Distinct channels/mechanisms found across repeats |
