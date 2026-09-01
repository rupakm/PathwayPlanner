# Executable mechanistic hypotheses for molecular simulation

Draft framing for the first paper, written in the register of an
Introduction and Methods section. Supersedes the Δ_comp-centred framing in
`NOTES.md` and `PLAN.md`, for reasons given in §1.4.

---

## 1. Introduction

### 1.1 Mechanism is stated informally and cannot be checked

A conformational transition is conventionally reported as a claim about
ordered structural events: a lid opens before a second domain follows, an
interface weakens before a hinge rotates, a ligand clears a constriction
before it reaches the vestibule. Such claims are the scientific content of
the work. They are also, almost without exception, stated in prose and
supported by a projection of a free-energy surface onto two manually chosen
coordinates.

There is no standard formalism for expressing them. The quantitative objects
the field does possess describe transitions in other terms. The committor
(1, 2) is the reference reaction coordinate and defines the transition state
ensemble, but it is a scalar field and therefore cannot by itself express an
ordering of two events. Transition path theory with Markov state models (3)
decomposes reactive flux into weighted pathways through metastable states,
which is the closest existing formalism for "A then B", but its states are
data-derived clusters rather than named structural operations, and the
decomposition is inferred from an equilibrium model rather than authored and
executed. Path collective variables (4) parameterise progress along a
reference path without decomposing it into events. The gap is acknowledged
within the field: reviewing simulations of a fast-folding protein, Berezovska
et al. observe that "having at hand the atomistic details of the process did
not lead to a straightforward interpretation of the mechanism" (5).

### 1.2 Guidance, not the sampler, determines what is found

Conformational transitions occur on timescales that unbiased simulation
cannot reach, so every practical method supplies guidance: a biasing
coordinate, a target structure, a selection rule. A systematic comparison of
targeted, steered and biased molecular dynamics found that the choice of
progress variable dominates outcomes more than the choice of method (6). Our
own measurements reproduce this from two directions, reported in §4.

Machine-learned collective variables (7–10) improve the guidance but relocate
rather than remove the interpretive problem: the resulting coordinate is a
neural function of atomic coordinates, and its content is recovered, when at
all, by post-hoc attribution (11). The authoritative recent survey treats
interpretability as one term in a design trade-off rather than a
requirement, and judges collective variables by sampling efficiency and
committor quality (12). Symbolic regression can distil a learned mechanism
into a human-readable expression (13), and this is the closest existing work
to an interpretable mechanistic statement; where the trade-off has been
quantified, however, simple symbolic forms were found insufficient — a
committor for a peptide isomerisation required "a nonlinear coupling of all
four dihedrals" (14).

Two observations follow. First, guidance is the scientific content and is
currently not written down in a reusable form. Second, every symbolic object
in this literature is a *formula over observables*: a scalar-valued
expression. None is a *procedure*.

### 1.3 Contribution

We introduce a typed, executable formalism in which a mechanistic hypothesis
is a short program over named structural operations, each realised as a
physically grounded biased search that returns a typed outcome. The
formalism makes three things possible that prose does not:

1. **A mechanistic claim becomes falsifiable by execution.** Competing
   hypotheses about event ordering are competing programs, run under
   identical machinery with identical budgets.
2. **The value of domain knowledge becomes measurable.** Each program is
   compared against an unguided control at equal compute, which quantifies
   what a piece of expert knowledge is worth rather than assuming it.
3. **The type system doubles as an evaluation cascade.** Because operations
   return typed outcomes and a failure aborts the remainder of a program,
   the cost of evaluating a candidate hypothesis is naturally staged. This
   is the property that makes automated search over hypotheses affordable,
   and it is developed in §3.5.

The nearest precedent is not in molecular simulation but in synthetic
chemistry, where Cronin and co-workers represent a synthesis as a program in
a chemical description language executed by a robotic platform (15–17). That
line also supplies the argument against the objection that a sufficiently
capable generative model makes the formalism unnecessary: when a language
model is used to translate literature procedures into executable form, the
language acts as a *safety envelope*, because a proposed step that is not
expressible in the language cannot be executed (18). A generator emitting an
unconstrained bias potential has no such envelope, and — as we show in §4 —
no means of determining whether its proposal achieved the intended
structural event.

### 1.4 Relation to a previous framing

An earlier version of this programme was organised around Δ_comp, the
discrepancy between the measured success of a composed program and the
success predicted from an abstract summary of the first stage's output. That
quantity is well defined and we continue to measure it, but it is a
prerequisite for automated planning rather than a finding about proteins,
and it is not the contribution. It is reported in §3.6 as a property of the
formalism.

---

## 2. Related work and what is claimed as new

**Adaptive sampling and reinforcement learning over restart points.**
Selecting where to restart short simulations is a mature area (19–22),
including a reinforcement-learning formulation that adaptively weights
pre-specified reaction coordinates (19) and a bandit formulation with
asymptotic guarantees (21). In all of this work the action space is a
restart-state index or a coordinate weighting. We claim no contribution
here; we adopt it.

**Reinforcement learning and optimal control for transition paths.** Rare
trajectory sampling, committor estimation as a control problem, and
machine-guided path sampling constitute an active field. We position our
committor estimation as an instance of this work rather than as an
advance on it.

**Symbolic mechanism representations.** Symbolic regression over observables
(13, 14) yields formulas; likelihood maximisation (23) and spectral-gap
optimisation (24) yield sparse coordinates over named order parameters.
These are scalar-valued objects. We are not aware of prior work representing
a transition mechanism as a compositional program of named operations with
executable semantics; searches for program synthesis, domain-specific
languages, and grammars applied to molecular simulation returned no
occupants.

**Programs as executable scientific procedures.** Outside molecular
simulation the idea is established: chemical description languages for
robotic synthesis (15–17), formal semantics for biological protocols
supporting verification and synthesis (25), retrosynthetic planning by
search over reaction procedures (26), and grammar-guided evolutionary search
over an intervention language for epidemiological simulators (27). Our
contribution is the transfer of this stance to conformational transitions,
where the executed operation is a biased search rather than a laboratory
action, and where the outcome is a typed physical verdict rather than a
product yield.

**Language-model agents for simulation.** A number of systems translate
natural language into simulation workflows. Two recent benchmarks scope
enhanced sampling out of consideration by name, and their measured success
rates on difficult tasks are low (28, 29). We therefore treat automated
generation of guidance as an open application enabled by, and gated by, the
formalism — not as an assumed capability.

---

## 3. Methods

### 3.1 States and collective-variable spaces

A state pairs an opaque configuration handle with the abstract description
over which planning occurs, and retains the full configuration so that any
visited state may serve as a restart point:

    State = (configuration, features, labels, metadata)

A collective variable is represented not as a function but as a space: a
projection bundled with its metric, exposing `project`, `displacement` and
`distance`, with the invariant that distance is the norm of the
displacement. Periodicity is therefore a property of the coordinate rather
than of each consumer, which removes a recurring source of error in
dihedral-valued coordinates.

### 3.2 Structural actions

An action is a stochastic search procedure for realising a structural event,
exposing four operations:

    precondition(state)                    -> bool
    propose(state)                         -> [Implementation]
    execute(state, implementation, budget) -> [Trajectory]
    evaluate(initial_state, trajectories)  -> ActionResult

An implementation is the tuple (ξ, V, T, N, ρ): a collective-variable space,
an intervention, a duration, a replica count, and a selection policy. The
separation between the event an action specifies and the coordinate an
implementation biases is deliberate and load-bearing: in the experiments of
§4 the biased coordinate is an inter-domain distance while the event is
defined on a hinge angle, so success is not tautological.

### 3.3 Outcomes

Execution returns one of six outcomes, three of which are terminal failures
that abort a program:

    SUCCESS | PARTIAL | FAILURE | ALTERNATIVE | UNSTABLE | BUDGET_EXCEEDED

`PARTIAL` denotes measurable progress short of the event and carries the
state from which a program may retry or branch. `ALTERNATIVE` denotes that a
different transition occurred, with the channel identified; this is how
competing routes are reported rather than discarded, and it is the
mechanism by which a program can be informative when its hypothesis is
wrong. `UNSTABLE` denotes an event achieved but not surviving removal of the
intervention.

### 3.4 Event specification

Progress is defined relative to a target point in a collective-variable
space as d(start, target) − d(x, target), which is well defined in any
dimension and under periodicity, and which is signed, so motion opposed to
the intended direction cannot be recorded as partial progress. Three
classifiers share this definition: a threshold on a single coordinate; a
region-based classifier that reports the first region entered and thereby
detects alternatives; and a conjunctive classifier over several criteria
that scores a frame by its *worst* component, min_i(progress_i / delta_i),
requiring all criteria to be met in the same frame.

The conjunctive form is necessary and not merely convenient. In §4 we report
a case in which a single angular criterion was satisfied by configurations
that had left the initial state without reaching the intended one; the
conjunctive criterion, by requiring a structural measure to advance in the
same frame, selected different and better configurations from the same
trajectories.

### 3.5 Programs, and the type system as an evaluation cascade

Programs are built from combinators over steps, where a step maps a state to
an outcome. Sequential composition threads each step's successor state into
the next and aborts at the first terminal failure; conditional composition
branches on the outcome of a guard.

This abort semantics has a consequence beyond program structure. Searching
over candidate hypotheses requires evaluating each one, and here an
evaluation is a molecular dynamics simulation. In the regime relevant to
this work — of order one GPU-hour per action, five actions per program, and
replicates required because the fitness is stochastic — an evaluation costs
of order fifteen GPU-hours. Classical evolutionary search with a population
of hundreds over tens of generations is therefore not affordable. Search
schemes designed for costly evaluation address this with a manually
constructed *evaluation cascade*, in which a candidate proceeds to a more
expensive stage only after passing cheaper ones (30). Our type system
supplies such a cascade by construction: a terminal failure in an early
action terminates the program before later actions are executed, so the
expected cost of an unpromising hypothesis is a fraction of a full
evaluation, and — of equal practical importance — the variance in evaluation
cost is reduced. We are not aware of a systematic treatment of
evaluation-cascade design for expensive stochastic simulators, and we
develop this as a methodological contribution.

### 3.6 Contracts and composition

A program carries a contract: the abstract labels it accepts, those it may
produce, its accumulated outcome statistics, and its budget. The outcome
model is empirical, being what repeated execution measures. Δ_comp, the
discrepancy between measured composed success and success predicted from
class-conditional statistics of the first stage's output, is zero exactly
when the abstraction is a sufficient statistic for the subsequent action's
outcome distribution. Its practical significance is that it determines
whether candidate programs can be scored from stored statistics rather than
executed.

### 3.7 The simulator boundary

A single protocol separates the formalism from any engine:

    run_bursts(start_states, implementation, budget) -> [Trajectory]

Two adapter modules are the only components permitted to import a simulation
package. Identical action and classifier code has consequently been executed
without modification on analytic test landscapes, on a peptide, and on a
3,341-atom protein, against two independent simulation engines.

### 3.8 Recovering unbiased statistics

Biased trajectories are used as a proposal over starting configurations,
not as a statistical sample. Two properties make this rigorous. Transition
probabilities between discrete states are conditional, so estimates obtained
from trajectories initiated in a given state are unaffected by how that
configuration was found, with equilibrium populations recovered from the
resulting transition matrix. The committor is likewise a property of a
configuration under unbiased dynamics and is independent of the search that
produced it. Kinetics are therefore obtained by seeding unbiased sampling
from the discovered route, for which weighted ensemble (31) is the natural
instrument since it enhances rare events by managing trajectory weights
rather than by adding force.

We do not reweight biased trajectories directly. The correction is a product
accumulated per timestep whose variance grows exponentially with trajectory
length; in the best-documented implementation the weights are reported to
underflow in practice (32, 33), and no published application of that method
reports a rate for a protein.

The limitation that survives is one of coverage rather than correctness: a
search that locates one channel supports faithful statistics for that
channel and is silent about others. This is why alternative outcomes are
first-class, and why configurations for committor estimation are drawn from
several independent directions of guidance.

---

## 4. Design of the action vocabulary

The formalism is only as useful as the operations it provides. We state the
criteria explicitly because they determine whether the approach generalises
beyond systems whose answer is already known.

### 4.1 Criteria

**(C1) Specifiable without the answer.** An action's event must be definable
from information available before the transition is known. This is the
criterion that decides whether the formalism is a research instrument or a
post-hoc description.

**(C2) Protein-independent schema, system-specific grounding.** `open_hinge(H, δ)`
must be meaningful for any hinge, with H bound to residue sets per system.

**(C3) Implementable as an intervention.** The event must be reachable by
an intervention the simulation engine can express — presently restraints on
interatomic and centroid distances and on torsions.

**(C4) Composable.** Outcomes must supply states admissible as inputs to
subsequent actions.

### 4.2 The tension in (C1), and its resolution

Two of our actions currently violate (C1). `open_hinge` is specified as a
relative advance of a hinge angle, which requires no knowledge of the
destination; but a purely angular event proved satisfiable by configurations
that were not the intended state, and the correction we adopted — requiring
approach in root-mean-square deviation to a reference structure — reintroduces
a dependence on knowing the target.

We propose a target-free alternative that addresses the same failure. The
observed failure was not that the angle moved too little but that it moved
without the domain moving: the coordinate was satisfied by local distortion.
This is detectable without any reference structure by requiring the event to
be accompanied by **rigid-body coherence** — that the internal geometry of
the moving body be preserved while its position or orientation relative to
the reference body changes. Concretely, an action may require that the
root-mean-square deviation of the domain to itself, after optimal
superposition, remain small while the relative displacement is large. This
criterion is intrinsic, requires no endpoint, and would have rejected the
configurations that the angular criterion accepted.

We regard the general principle as the more important result: an event
specification should constrain *the character of the motion*, not only the
value of a coordinate. Under (C1) this is the difference between an
instrument and a description.

### 4.3 Proposed atomic actions

Actions requiring no knowledge of the destination:

| Action | Event | Intervention |
| --- | --- | --- |
| `relax()` | the current state persists | none, by definition |
| `explore(region, τ)` | any displacement in the named region | none, or a weak repulsion from the start |
| `separate(A, B, δ)` | centroid distance increases by δ | centroid-distance restraint |
| `approach(A, B, δ)` | centroid distance decreases by δ | centroid-distance restraint |
| `open_hinge(H, δ)` | hinge angle advances by δ, with rigid-body coherence | centroid distance or torsion |
| `close_hinge(H, δ)` | hinge angle retreats by δ, with coherence | as above |
| `rotate_domain(D, θ)` | relative orientation changes by θ, with coherence | orientation restraint |
| `weaken_interface(A, B, n)` | native contacts between A and B fall by n | contact-count restraint (§4.4) |
| `strengthen_interface(A, B, n)` | contacts rise by n | as above |
| `expose(P)` | solvent accessibility of region P increases | distance restraints on occluding groups |
| `crack(S)` | local secondary structure of segment S is disrupted | restraint on internal hydrogen bonds |
| `rearrange_loop(L)` | the loop adopts a distinct conformation | local exploration, no target |

Actions requiring a reference state, admissible when endpoints are known —
the standard situation, since these problems typically arrive with two
experimental structures and an unknown mechanism:

| Action | Event |
| --- | --- |
| `reach(X, ε)` | RMSD to reference X falls below ε |
| `depart(X, ε)` | RMSD to reference X exceeds ε |

`crack` deserves particular mention: local unfolding at hinge residues is
reported as a mechanistic feature of adenylate kinase (34), so an action
vocabulary that cannot express it cannot express the mechanism under debate.

### 4.4 Required extensions to the intervention layer

`weaken_interface` and `strengthen_interface` require a contact-count
collective variable, which the present engine interface does not provide;
this is the principal missing capability. `rotate_domain` requires an
orientation-based restraint. Both are standard in enhanced-sampling
software and their absence is an implementation gap rather than a
conceptual one.

### 4.5 Required extensions to the control structure

The present combinators — sequence, conditional, retry, repetition — cannot
express *concurrency*, and this is a substantive omission rather than a
convenience. The mechanistic question at issue for adenylate kinase is
whether two domains move in a definite order or together. Sequential
composition expresses the first; expressing the second requires a parallel
form,

    Par(open_hinge(LID), open_hinge(NMP))

denoting simultaneous intervention on both, which is a physically distinct
hypothesis from either ordering. A formalism for mechanistic hypotheses that
cannot state "concertedly" cannot express one of the three candidate
mechanisms, and we regard the addition of a parallel combinator, together
with a `hold` form that maintains a restraint while another action executes,
as a requirement rather than an enhancement.

---

## 5. Validation strategy

Three tiers, in increasing strength.

**Tier 1: guided against unguided at equal cost.** Every action is measured
against an unguided control with identical compute. This quantifies what
each piece of domain knowledge is worth and is reported for every action.

**Tier 2: physical validity.** Structures produced by an action must survive
removal of the intervention, and configurations labelled successful must
have committor values consistent with that label, estimated from unbiased
trajectories.

**Tier 3: a transition that composition alone can traverse.** Our engineered
landscape demonstrates that a program changing direction mid-path succeeds
where every single linear coordinate provably fails. The corresponding
demonstration on a real system requires a transition whose productive
direction genuinely reverses; adenylate kinase, being two coupled hinges, is
adequately described by a two-dimensional coordinate and therefore cannot
provide it. A curved ligand-exit channel can. This is the decisive
experiment for the central claim and is not yet performed.

Path similarity analysis (35) provides an established instrument for
comparing generated paths against reference ensembles for adenylate kinase,
and no planner-generated or program-generated path has been evaluated with
it.

---

## References

1. R. B. Best, G. Hummer, *Proc. Natl. Acad. Sci. U.S.A.* **102**, 6732 (2005). doi:10.1073/pnas.0408098102
2. J. D. Chodera, V. S. Pande, *Phys. Rev. Lett.* **107**, 098102 (2011). doi:10.1103/PhysRevLett.107.098102
3. F. Noé, C. Schütte, E. Vanden-Eijnden, L. Reich, T. R. Weikl, *Proc. Natl. Acad. Sci. U.S.A.* **106**, 19011 (2009). doi:10.1073/pnas.0905466106
4. D. Branduardi, F. L. Gervasio, M. Parrinello, *J. Chem. Phys.* **126**, 054103 (2007). doi:10.1063/1.2432340
5. G. Berezovska, D. Prada-Gracia, F. Rao, arXiv:1304.5903 (2013).
6. Y.-M. Huang, E. Özkirimli, C. B. Post, *J. Chem. Theory Comput.* **5**, 1301 (2009). doi:10.1021/ct9000153
7. A. Mardt, L. Pasquali, H. Wu, F. Noé, *Nat. Commun.* **9**, 5 (2018). doi:10.1038/s41467-017-02388-1
8. Y. Wang, P. Tiwary, *J. Chem. Phys.* **154**, 134111 (2021). doi:10.1063/5.0038198
9. L. Bonati, V. Rizzi, M. Parrinello, *J. Phys. Chem. Lett.* **11**, 2998 (2020). doi:10.1021/acs.jpclett.0c00535
10. P. Kang, E. Trizio, M. Parrinello, *Nat. Comput. Sci.* **4**, 451 (2024). doi:10.1038/s43588-024-00645-0
11. T. Kikutsuji, Y. Mori, K. Okazaki, T. Mori, K. Kim, N. Matubayasi, *J. Chem. Phys.* **156**, 154108 (2022). doi:10.1063/5.0087310
12. J. Zhu, E. Trizio, L. Zhang, X. Hu, H. Jiang, T. Hou, L. Bonati, *Chem. Rev.* (2025). doi:10.1021/acs.chemrev.5c00700
13. H. Jung, R. Covino, A. Arjun, C. Leitold, C. Dellago, P. G. Bolhuis, G. Hummer, *Nat. Comput. Sci.* **3**, 334 (2023). doi:10.1038/s43588-023-00428-z
14. J. Töpfer, G. Lazzeri, R. Ossanna, A. Renner, G. Lattanzi, R. Covino, B. Keller, arXiv:2604.24245.
15. S. Steiner, J. Wolf, S. Glatzel, et al., L. Cronin, *Science* **363**, eaav2211 (2019). doi:10.1126/science.aav2211
16. S. H. M. Mehr, M. Craven, A. I. Leonov, G. Keenan, L. Cronin, *Science* **370**, 101 (2020). doi:10.1126/science.abc2986
17. R. Rauschen, M. Guy, J. E. Hein, L. Cronin, *Nat. Synth.* **3**, 488 (2024). doi:10.1038/s44160-023-00473-6
18. N. Pagel, M. Jirasek, L. Cronin, arXiv:2410.06384 (2024).
19. Z. Shamsi, K. J. Cheng, D. Shukla, *J. Phys. Chem. B* **122**, 8386 (2018). doi:10.1021/acs.jpcb.8b06521
20. D. Kleiman, D. Shukla, *J. Chem. Theory Comput.* **18**, 5422 (2022). doi:10.1021/acs.jctc.2c00683
21. A. Pérez, P. Herrera-Nieto, S. Doerr, G. De Fabritiis, *J. Chem. Theory Comput.* **16**, 4685 (2020). doi:10.1021/acs.jctc.0c00205
22. M. I. Zimmerman, G. R. Bowman, *J. Chem. Theory Comput.* **11**, 5747 (2015). doi:10.1021/acs.jctc.5b00737
23. B. Peters, B. L. Trout, *J. Chem. Phys.* **125**, 054108 (2006). doi:10.1063/1.2234477
24. P. Tiwary, B. J. Berne, *Proc. Natl. Acad. Sci. U.S.A.* **113**, 2839 (2016). doi:10.1073/pnas.1600917113
25. A. Abate, L. Cardelli, M. Kwiatkowska, L. Laurenti, B. Yordanov, arXiv:1710.08016 (2017).
26. M. H. S. Segler, M. Preuss, M. P. Waller, *Nature* **555**, 604 (2018). doi:10.1038/nature25978
27. C. Wolpers, J. Ponge, A. M. Uhrmacher, arXiv:2604.02016.
28. Kumar, Rajput, Mausam, Krishnan, arXiv:2605.08941 (MDGym).
29. Mouroug Anand, Hsu, Vaccaro, et al., Biggin, arXiv:2608.02642 (MDArena).
30. A. Novikov, N. Vũ, M. Eisenberger, et al., arXiv:2506.13131 (AlphaEvolve). See also B. Romera-Paredes, M. Barekatain, A. Novikov, et al., *Nature* **625**, 468 (2024). doi:10.1038/s41586-023-06924-6
31. G. A. Huber, S. Kim, *Biophys. J.* **70**, 97 (1996). doi:10.1016/S0006-3495(96)79552-8
32. D. M. Zuckerman, T. B. Woolf, *J. Chem. Phys.* **111**, 9475 (1999). doi:10.1063/1.480278
33. J. R. Perilla, O. Beckstein, E. J. Denning, T. B. Woolf, *J. Comput. Chem.* **32**, 196 (2011). doi:10.1002/jcc.21564
34. O. Beckstein, E. J. Denning, J. R. Perilla, T. B. Woolf, *J. Mol. Biol.* **394**, 160 (2009). doi:10.1016/j.jmb.2009.09.009
35. S. L. Seyler, A. Kumar, M. F. Thorpe, O. Beckstein, *PLoS Comput. Biol.* **11**, e1004568 (2015). doi:10.1371/journal.pcbi.1004568

*Citations 28 and 29 are preprints whose author lists and identifiers were
verified but whose full texts were read only in part; citation 6's DOI
should be confirmed against the published record before submission.*
