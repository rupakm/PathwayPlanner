# Design and Implementation Plan: A Planning Language for Controlled Molecular Dynamics

## 1. Purpose and Overall Strategy

This document describes a concrete design and implementation plan for developing a **planning language for controlled molecular dynamics**.

The central idea is to provide a layer of abstraction between high-level mechanistic reasoning about conformational change and low-level molecular dynamics simulation.

Scientists naturally reason about structural events such as:

- opening a hinge;
- weakening an interface;
- separating two domains;
- rotating a domain;
- rearranging a loop;
- exposing a binding pocket.

Conventional MD and enhanced-sampling methods instead operate through lower-level mechanisms such as:

- collective variables;
- bias potentials;
- restraints;
- trajectory ensembles;
- adaptive sampling;
- trajectory selection and resampling.

The proposed system bridges these levels:

\[
\boxed{
\text{Structural hypothesis}
\rightarrow
\text{Molecular program}
\rightarrow
\text{Structural actions}
\rightarrow
\text{MD/enhanced-sampling searches}
\rightarrow
\text{Physically valid trajectories}.
}
\]

The implementation strategy is deliberately incremental. Rather than beginning with end-to-end reinforcement learning, we first establish:

1. a useful vocabulary of molecular actions;
2. physically grounded implementations of those actions;
3. useful abstractions of molecular outcomes;
4. composable molecular recipes;
5. predictive models of action and recipe behavior;
6. automated planning and search;
7. reinforcement learning as a later layer.

This bottom-up strategy reduces scientific and engineering risk. Each layer should be independently useful and experimentally testable before the next layer is introduced.

---

# 2. Overall System Architecture

The proposed system consists of the following layers:

\[
\boxed{
\begin{array}{c}
\textbf{Automated Planning / Reinforcement Learning}\\
\hline
\textbf{Recipe Library and Recipe Search}\\
\hline
\textbf{Outcome Models and State Abstraction}\\
\hline
\textbf{Action Compiler}\\
\hline
\textbf{Primitive Structural Actions}\\
\hline
\textbf{Enhanced Sampling / Short-Burst MD}\\
\hline
\textbf{Molecular Dynamics Backend}
\end{array}
}
\]

The important architectural principle is that the higher-level language should remain independent of the particular method used to select actions.

Programs may be:

- manually written by scientists;
- generated through heuristic search;
- optimized through evolutionary methods;
- synthesized automatically;
- selected by a model-based planner;
- selected by a reinforcement-learning policy.

Thus:

\[
\boxed{
\text{The language defines how molecular strategies are represented and executed.}
}
\]

Reinforcement learning is only one possible mechanism for selecting those strategies.

---

# 3. Core Software Components

## 3.1 Molecular State Abstraction

Let

\[
x\in\mathcal X
\]

denote a full molecular configuration.

The planning system should not necessarily operate directly over atomic coordinates. Instead, it uses an abstract state:

\[
s=\phi(x).
\]

Initially, \(\phi\) may consist of interpretable structural features such as:

- domain positions;
- relative domain orientations;
- hinge angles;
- inter-domain distances;
- contact patterns;
- interface contact counts;
- RMSD to reference structures;
- secondary-structure descriptors;
- known collective variables.

For example:

\[
\phi(x)=
\left(
\begin{array}{c}
d_{AB}(x)\\
\theta_H(x)\\
c_{AB}(x)\\
\operatorname{RMSD}(x,x_{\mathrm{open}})\\
\operatorname{RMSD}(x,x_{\mathrm{closed}})
\end{array}
\right).
\]

Later, the abstraction may include learned coordinates:

\[
\phi(x)
=
\left(
\phi_{\mathrm{struct}}(x),
\phi_{\mathrm{learned}}(x)
\right).
\]

A conceptual software representation is:

```text id="wwa2uc"
State:
    configuration: MDConfiguration
    features: FeatureVector
    labels: Set[AbstractState]
    metadata: Metadata
```

The full molecular configuration should always be retained, even when planning takes place over a coarse abstraction.

---

## 3.2 Molecular Action Interface

Every structural action should implement a common interface.

Conceptually:

```text id="c2uhf9"
Action:

    precondition(state) -> Validity

    propose(state) -> List[Implementation]

    execute(state, implementation, budget)
        -> ActionResult

    evaluate(initial_state, trajectories)
        -> Outcome
```

Mathematically, an action can be represented as:

\[
a=
(
\operatorname{Pre}_a,
\mathcal I_a,
\operatorname{Exec}_a,
\operatorname{Eval}_a
).
\]

### Preconditions

\[
\operatorname{Pre}_a(s)
\]

determines whether an action is meaningful in the current state.

### Candidate implementations

\[
\mathcal I_a(s)
\]

returns possible physical implementations of the action.

### Execution

\[
\operatorname{Exec}_a(s,I,B)
\]

runs the MD or enhanced-sampling procedure associated with implementation \(I\) under budget \(B\).

### Evaluation

\[
\operatorname{Eval}_a(s,\mathcal T)
\]

evaluates the resulting trajectory ensemble \(\mathcal T\).

The action therefore induces a distribution:

\[
P(o,s'\mid s,a,I),
\]

where:

- \(o\) is the outcome;
- \(s'\) is the resulting abstract state;
- \(I\) is the physical implementation.

---

## 3.3 Action Results

An action result should contain substantially more information than a Boolean success value.

A conceptual representation is:

```text id="m2b1zv"
ActionResult:
    outcome
    successor_states
    trajectories
    event_scores
    physical_validity
    cost
    implementation
    metadata
```

Possible outcome categories include:

\[
\operatorname{Outcome}
=
\begin{cases}
\operatorname{Success},\\
\operatorname{Partial},\\
\operatorname{Failure},\\
\operatorname{Alternative},\\
\operatorname{Unstable},\\
\operatorname{BudgetExceeded}.
\end{cases}
\]

This is important because molecular actions may:

- partially realize their intended event;
- discover an alternative transition;
- generate several useful successor configurations;
- produce progress that disappears during relaxation;
- fail because the available simulation budget is insufficient.

Failure and alternative outcomes should therefore be first-class elements of the language semantics.

---

# 4. Phase I: Minimal Molecular Action Language

The first prototype should intentionally use a small action vocabulary.

The objective is not initially to support arbitrary structural descriptions. Instead, we should identify approximately five to eight reusable action families.

## 4.1 Hinge Motion

```text id="e8k9pj"
open_hinge(H, amount)
close_hinge(H, amount)
```

Possible implementation:

- identify hinge residues;
- define a relative orientation or angular coordinate;
- launch multiple short MD trajectories;
- optionally apply weak biasing;
- select trajectories exhibiting progress;
- validate the resulting state through relaxation.

---

## 4.2 Domain Separation

```text id="8f4q1s"
separate(A, B, amount)
approach(A, B, amount)
```

A simple structural coordinate may be:

\[
d_{AB}(x)
=
\|
c_A(x)-c_B(x)
\|,
\]

where \(c_A(x)\) and \(c_B(x)\) are representative domain positions.

---

## 4.3 Interface Disruption

```text id="k6spt0"
weaken_interface(A, B)
```

Possible implementations include:

- contact-based collective variables;
- adaptive short-burst exploration;
- selective weakening of key contacts;
- enhanced sampling over interface coordinates.

---

## 4.4 Domain Rotation

```text id="s0n5cm"
rotate(D, axis, amount)
```

This action operates over relative orientations rather than direct coordinate manipulation.

Possible implementations may use:

- orientation-based collective variables;
- adaptive exploration around candidate rotational modes;
- learned local slow coordinates.

---

## 4.5 Local Rearrangement

```text id="s9vdm7"
rearrange_loop(L)
```

Initially, this action may be implemented through local adaptive sampling rather than requiring a predefined collective variable.

This provides a useful test of whether actions can remain meaningful even when the relevant coordinate is not obvious.

---

## 4.6 Relaxation

```text id="y8cq6l"
relax()
```

Relaxation should be a first-class action.

It removes temporary interventions and tests whether the resulting structure remains in a physically meaningful region of conformational space.

Relaxation is particularly important for distinguishing:

\[
\text{bias-induced displacement}
\]

from

\[
\text{entry into a physically stable conformational region}.
\]

---

## 4.7 Phase I Deliverables

For every primitive action:

1. define the structural event mathematically;
2. define one or more physical implementations;
3. define success and failure criteria;
4. implement trajectory-based outcome classification;
5. perform repeated executions from representative states;
6. estimate empirical outcome distributions.

The resulting data provides an empirical model:

\[
P(o,s'\mid s,a,I).
\]

### Milestone A

> Can a high-level structural action be implemented as a reproducible, physically grounded stochastic search procedure?

---

# 5. Phase II: Action Compilation

The next component is the **action compiler**.

The compiler translates:

\[
(s,a)
\]

into a concrete physical implementation:

\[
\mathcal C(s,a)\rightarrow I.
\]

An implementation may specify:

\[
I=
(
\xi,
V,
T,
N,
\rho
),
\]

where:

- \(\xi\) is a collective variable or representation;
- \(V\) specifies biasing or intervention;
- \(T\) is simulation duration;
- \(N\) is the number of trajectories or replicas;
- \(\rho\) specifies trajectory selection or resampling.

---

## 5.1 Initial Rule-Based Compiler

The first version should use explicit rules.

For example:

```text id="t4ptxm"
if action == open_hinge:

    if known_hinge_geometry:
        use orientation-based coordinate

    elif informative interface contacts exist:
        use contact-based intervention

    else:
        use adaptive local exploration
```

This provides a transparent baseline and allows individual implementations to be evaluated systematically.

---

## 5.2 Adaptive Implementation Selection

Suppose an action has candidate implementations:

\[
\mathcal I(a,s)
=
\{
I_1,\ldots,I_k
\}.
\]

We can estimate:

\[
Q(s,a,I)
=
\mathbb E
\left[
R(o,s')
-
\lambda\operatorname{Cost}(I)
-
\mu\operatorname{Instability}(I)
\right].
\]

The compiler then selects:

\[
I^\star
=
\arg\max_I Q(s,a,I).
\]

Initially, this can be formulated as a contextual bandit problem.

This is an important intermediate learning problem because it has much better credit assignment than end-to-end reinforcement learning.

### Milestone B

> Can the system learn which physical implementation is most effective for a structural action in a given molecular context?

---

# 6. Phase III: Molecular State Abstraction

A central challenge is determining what information should be passed between actions.

Atomic configurations are too detailed for direct symbolic composition, while overly coarse labels may hide important differences.

We initially define interpretable abstract states such as:

```text id="1ykn9r"
gate_closed
gate_partially_open
gate_open

interface_intact
interface_weakened
interface_broken

unstable
```

For example:

\[
\texttt{gate\_open}(x)
\iff
\theta_H(x)
>
\theta_0+\delta.
\]

However, manually specified abstractions may not be sufficient.

Two configurations may both be classified as `gate_open` while having very different responses to subsequent actions.

---

## 6.1 Action-Predictive Abstractions

A useful criterion for an abstract state representation is:

\[
x_1\sim x_2
\Rightarrow
P(o,s'\mid x_1,a)
\approx
P(o,s'\mid x_2,a)
\]

for relevant actions \(a\).

In other words, configurations should be considered equivalent when future action behavior is approximately equivalent.

This connects the project to:

- predictive state representations;
- state aggregation;
- bisimulation;
- model reduction;
- representation learning for control.

---

## 6.2 Abstraction Refinement

The system should begin with a coarse state representation and refine it when action behavior differs substantially.

For example:

1. group configurations into an abstract state \(S\);
2. execute actions from multiple configurations in \(S\);
3. compare their outcome distributions;
4. split \(S\) when the distributions differ significantly.

This produces an adaptive abstraction driven by the needs of planning.

### Milestone C

> Can we construct abstract molecular states that preserve the information necessary to predict future action behavior?

---

# 7. Phase IV: Recipes and Compositionality

Once primitive actions and abstract states exist, we can implement the recipe language.

A minimal language should support:

```text id="j0fx2j"
sequence
if / else
retry
bounded repetition
failure handling
subrecipes
```

For example:

```text id="fjgptf"
result = open_hinge(H)

if result.success:
    rotate_domain(D)

elif result.partial:
    retry(smaller_step)

else:
    weaken_interface(A, B)
```

Recipes are stochastic programs.

Their execution produces a distribution over outcomes and successor states.

---

## 7.1 Recipe Contracts

Each recipe should have a contract:

\[
\mathcal C(P)
=
(
\operatorname{Pre}_P,
\operatorname{Post}_P,
K_P,
B_P
),
\]

where:

- \(\operatorname{Pre}_P\) describes valid input states;
- \(\operatorname{Post}_P\) describes possible output states;
- \(K_P\) describes stochastic behavior;
- \(B_P\) specifies computational budget.

This makes recipes reusable and composable.

---

## 7.2 Measuring Physical Compositionality

Suppose:

\[
P_1:A\leadsto B
\]

and:

\[
P_2:B\leadsto C.
\]

The predicted success probability is:

\[
p_{\mathrm{pred}}
=
\int
P(C\mid s,P_2)
dP_{P_1}(s\mid A).
\]

The empirical success probability is:

\[
p_{\mathrm{actual}}
=
P(C\mid A,P_1;P_2).
\]

We define a compositionality error:

\[
\Delta_{\mathrm{comp}}
=
\left|
p_{\mathrm{actual}}
-
p_{\mathrm{pred}}
\right|.
\]

More generally, we can compare full outcome distributions rather than only success probabilities.

### Milestone D

> Do independently useful molecular actions and recipes remain predictively useful when composed?

This is one of the most distinctive scientific questions in the project.

---

# 8. Phase V: Recipe Libraries and Molecular Skills

Once recipes can be executed, we introduce reusable molecular skills.

The hierarchy is:

\[
\boxed{
\text{Primitive Actions}
\rightarrow
\text{Basic Skills}
\rightarrow
\text{Domain-Specific Skills}
\rightarrow
\text{High-Level Recipes}.
}
\]

For example:

```text id="fxt4sz"
Primitive:
    weaken_interface
    open_hinge
    rotate_domain
    relax
```

```text id="qzj0lr"
Basic Skill:
    open_gate
```

```text id="2m5abq"
High-Level Recipe:
    activate_protein
```

Each recipe should accumulate empirical metadata:

\[
\mathcal M(P)
=
(
\operatorname{Pre},
\operatorname{Post},
P_{\mathrm{success}},
\operatorname{Cost},
\operatorname{OutcomeModel}
).
\]

Thus the recipe library becomes a repository of experimentally characterized molecular strategies.

### Milestone E

> Can molecular skills be represented as reusable computational artifacts with measurable behavioral contracts?

---

# 9. Phase VI: Learning Action and Recipe Models

Repeated execution generates a dataset:

\[
\mathcal D
=
\{
(s_i,a_i,o_i,s'_i,c_i)
\}_{i=1}^{N}.
\]

This enables several learning problems.

## 9.1 Action Feasibility

Estimate:

\[
p_\theta(o\mid s,a).
\]

---

## 9.2 Success Prediction

Estimate:

\[
p_\theta(
\operatorname{Success}
\mid
s,a
).
\]

---

## 9.3 Successor-State Prediction

Estimate:

\[
p_\theta(
s'
\mid
s,a
).
\]

---

## 9.4 Cost Prediction

Estimate:

\[
c_\theta(s,a).
\]

---

## 9.5 Recipe Value

For a recipe \(P\), estimate:

\[
V_P(s)
=
\Pr(
\operatorname{Goal}
\mid
s,P
).
\]

These models can support intelligent action selection without yet requiring reinforcement learning.

For example:

\[
a^\star
=
\arg\max_a
\frac{
P(
\operatorname{Success}
\mid
s,a
)
}{
\operatorname{Cost}(s,a)
}.
\]

---

# 10. Phase VII: Automated Planning and Search

Before introducing model-free reinforcement learning, we should investigate planning over learned action models.

Given:

\[
\hat P(s'\mid s,a),
\]

we seek action sequences:

\[
a_1,\ldots,a_T
\]

such that:

\[
s_0
\xrightarrow{a_1}
s_1
\xrightarrow{a_2}
\cdots
\xrightarrow{a_T}
s_T\in G.
\]

Candidate methods include:

- best-first search;
- beam search;
- Monte Carlo tree search;
- stochastic shortest-path planning;
- model predictive control;
- program synthesis over recipes.

The objective may include:

\[
J
=
P(\operatorname{Goal})
-
\lambda\operatorname{Cost}
-
\mu\operatorname{Instability}.
\]

This provides an important baseline for evaluating reinforcement learning.

### Milestone F

> Can useful conformational strategies be discovered through planning over empirically learned molecular action models?

---

# 11. Phase VIII: Reinforcement Learning

Reinforcement learning should be introduced after the lower layers have been validated.

The environment is:

\[
s_t
\xrightarrow{a_t}
(o_t,s_{t+1}).
\]

The action space may consist of:

- primitive actions;
- parameterized actions;
- reusable recipes.

The policy is:

\[
\pi(a\mid s).
\]

At a higher level:

\[
\pi(P\mid s),
\]

where \(P\) is an entire recipe.

This naturally leads to hierarchical reinforcement learning.

---

## 11.1 Role of RL

The role of RL is not merely to reach a known target configuration once.

It can learn:

- which actions work in different structural contexts;
- when to retry;
- when to change action parameters;
- when to switch physical implementations;
- when to invoke relaxation;
- when to abandon a pathway;
- how to recover from partial failure;
- how to compose molecular skills under uncertainty.

---

## 11.2 Reward Design

The reward need not be purely:

\[
r=
\mathbb 1[
s\in G
].
\]

Possible components include:

\[
r_t
=
\alpha
\operatorname{GoalProgress}
+
\beta
\operatorname{Novelty}
+
\gamma
\operatorname{PhysicalValidity}
-
\lambda
\operatorname{Cost}
-
\mu
\operatorname{Instability}.
\]

However, dense rewards should be treated carefully to avoid encoding an incorrect mechanistic assumption.

A major alternative is to learn values from:

- empirical action success;
- reachability models;
- successor-state predictions;
- goal-conditioned value functions.

The learned policy may therefore exploit the molecular action and recipe abstractions without requiring a predefined committor.

### Milestone G

> Does RL provide an advantage over model-based planning once reusable molecular actions and recipes exist?

---

# 12. Benchmark Strategy

The benchmark suite should progress from interpretable conformational systems toward more complex biological targets.

## Benchmark 1: Adenylate Kinase

### Purpose

Adenylate kinase provides an interpretable system with large-scale domain motion involving the CORE, LID, and NMP-binding domains.

### Candidate actions

```text id="us12lh"
open_hinge(LID)
open_hinge(NMP)
rotate_domain(LID)
weaken_interface(LID, CORE)
relax()
```

### Research questions

- Can the action language represent known motions?
- Can actions be implemented reliably?
- Can alternative recipes produce different pathways?

### Primary use

Initial validation of the action language and action compiler.

---

## Benchmark 2: T4 Lysozyme

### Purpose

T4 lysozyme provides a useful system for studying alternative conformational transitions and pathway diversity.

### Research questions

- Can different recipes produce distinct transition mechanisms?
- Can the framework distinguish competing mechanistic strategies?
- Can action outcome models predict pathway success?

### Primary use

Testing pathway diversity and mechanistic programming.

---

## Benchmark 3: Calmodulin

### Purpose

Calmodulin provides larger-scale domain rearrangements and orientation changes.

### Research questions

- Can domain-level actions compose predictably?
- Can abstractions support sequential molecular planning?
- How robust are recipes to heterogeneous intermediate states?

### Primary use

Testing physical compositionality.

---

## Benchmark 4: GPCR Conformational Transitions

### Purpose

A GPCR provides a more complex and biologically relevant system involving multiple coupled structural changes and allosteric transitions.

### Research questions

- Can reusable molecular skills scale to more complex proteins?
- Can automated planning discover useful action sequences?
- Does hierarchical RL provide an advantage?

### Primary use

Testing scalability and adaptive planning.

---

# 13. Work Packages

## WP1 — Molecular Action Semantics

### Goal

Define a minimal vocabulary of high-level structural actions.

### Tasks

1. Select five to eight primitive actions.
2. Define structural event specifications.
3. Define action preconditions.
4. Define success, partial success, failure, and alternative outcomes.
5. Implement trajectory-based outcome classifiers.
6. Evaluate repeated executions.

### Deliverable

A formal action specification and reference implementation.

### Potential research contribution

**A Stochastic Action Model for High-Level Control of Molecular Dynamics**

---

## WP2 — Action Compilation and Physically Grounded Execution

### Goal

Translate structural actions into concrete MD and enhanced-sampling procedures.

### Tasks

1. Implement multiple physical realizations of each action.
2. Develop a transparent rule-based compiler.
3. Measure action success probability and computational cost.
4. Learn implementation-selection models.
5. Compare adaptive implementation selection against fixed implementations.

### Deliverable

An adaptive action compiler.

### Potential research contribution

**Compiling Structural Interventions into Enhanced-Sampling Molecular Dynamics**

---

## WP3 — Molecular State Abstraction

### Goal

Construct state representations suitable for action prediction and planning.

### Tasks

1. Begin with interpretable structural features.
2. Measure variation in action outcomes within abstract states.
3. Identify abstraction failures.
4. Develop learned predictive representations.
5. Refine abstractions based on action-outcome differences.

### Deliverable

An action-predictive molecular state abstraction.

### Potential research contribution

**Action-Predictive State Abstractions for Molecular Simulation Planning**

---

## WP4 — Recipes and Physical Compositionality

### Goal

Determine whether molecular actions and recipes can be composed predictably.

### Tasks

1. Implement the recipe language.
2. Define recipe contracts.
3. Execute primitive and composite recipes repeatedly.
4. Compare predicted and empirical composite behavior.
5. Identify failure modes of composition.
6. Develop abstraction refinement and recipe repair mechanisms.

### Deliverable

A library of empirically characterized molecular recipes.

### Potential research contribution

**Physical Compositionality of Molecular Intervention Programs**

---

## WP5 — Automated Recipe Search

### Goal

Discover useful molecular programs without requiring end-to-end reinforcement learning.

### Tasks

1. Construct action transition models.
2. Search over action sequences.
3. Search over recipe compositions.
4. Compare best-first search, MCTS, and stochastic planning.
5. Compare discovered programs with expert-designed mechanistic hypotheses.

### Deliverable

An automated molecular program search system.

### Potential research contribution

**Searching for Molecular Intervention Programs for Conformational Change**

---

## WP6 — Reinforcement Learning for Adaptive Molecular Control

### Goal

Learn adaptive policies for selecting actions and recipes.

### Tasks

1. Develop goal-conditioned action policies.
2. Investigate learned value functions.
3. Implement retry and recovery strategies.
4. Learn when to switch physical implementations.
5. Develop hierarchical policies over recipes.
6. Compare RL against model-based planning.

### Deliverable

An adaptive molecular control policy.

### Potential research contribution

**Hierarchical Reinforcement Learning for Adaptive Conformational Pathway Discovery**

---

## WP7 — Transfer and Recipe Reuse

### Goal

Determine whether structural recipes transfer across proteins.

This work package addresses an important distinction:

A low-level trajectory policy learned for one protein is unlikely to transfer directly to another.

However, a structural recipe such as:

```text id="rc4zdp"
weaken_interface()
open_hinge()
relax()
```

may transfer after grounding its abstract structural objects in a new protein.

### Tasks

1. Define protein-independent action schemas.
2. Ground schemas in protein-specific structures.
3. Transfer recipes across homologous proteins.
4. Measure zero-shot transfer.
5. Fine-tune action implementations when transfer fails.

### Deliverable

A framework for transferable molecular skills.

### Potential research contribution

**Transferable Molecular Skills Through Structural Program Abstractions**

---

# 14. Recommended Development Order

The recommended progression is:

\[
\boxed{
\begin{array}{ccccccc}
\text{WP1}
&\rightarrow&
\text{WP2}
&\rightarrow&
\text{WP3}
&\rightarrow&
\text{WP4}
\\
&&&&\downarrow\\
&&&&
\text{WP5}
\rightarrow
\text{WP6}
\rightarrow
\text{WP7}
\end{array}
}
\]

The key milestones are:

### Milestone A: Action Realization

Can a structural action be implemented as a reproducible, physically grounded stochastic search?

### Milestone B: Adaptive Compilation

Can the system select an effective physical implementation for an action?

### Milestone C: Predictive Abstraction

Can abstract molecular states predict future action behavior?

### Milestone D: Physical Compositionality

Can independently useful molecular skills remain effective when combined?

### Milestone E: Reusable Recipes

Can empirically characterized molecular strategies be stored and reused?

### Milestone F: Automated Planning

Can search algorithms discover useful molecular programs?

### Milestone G: Reinforcement Learning

Does RL provide benefits beyond planning over learned action models?

---

# 15. Initial Prototype Recommendation

The first implementation should combine WP1 and WP2.

A recommended initial target is **adenylate kinase**, potentially followed quickly by a second benchmark such as T4 lysozyme.

The initial prototype should implement:

```text id="g5wwri"
open_hinge(H)
close_hinge(H)

separate(A, B)

weaken_interface(A, B)

rotate(D)

rearrange_loop(L)

relax()
```

For each action, the system should initially support at least:

1. one interpretable structural specification;
2. one enhanced-sampling implementation;
3. one adaptive short-burst MD implementation;
4. an outcome classifier;
5. repeated-execution statistics.

The resulting software pipeline is:

\[
\boxed{
\text{Program}
\rightarrow
\text{Action}
\rightarrow
\text{Action Compiler}
\rightarrow
\text{PathGennie / Trails-MD}
\rightarrow
\text{MD trajectories}
\rightarrow
\text{Outcome Classification}
\rightarrow
\text{Abstract Molecular State}.
}
\]

The immediate engineering objective is therefore not to build a complete RL system.

It is to answer the foundational question:

> **Can high-level structural interventions be turned into executable stochastic molecular operations with sufficiently predictable behavior that they can be composed into larger conformational strategies?**

If the answer is yes, the subsequent planning and RL components have a meaningful action space on which to operate.

---

# 16. Expected Research Outcome

The overall project aims to establish a new abstraction layer for molecular simulation:

\[
\boxed{
\text{Scientists specify structural strategies rather than individual bias potentials.}
}
\]

A molecular program does not prescribe an exact trajectory.

Instead, it specifies:

\[
\boxed{
\text{a structured strategy for searching for physically valid trajectories.}
}
\]

The resulting research program combines:

- molecular dynamics;
- enhanced sampling;
- adaptive sampling;
- structural biology;
- program composition;
- probabilistic semantics;
- state abstraction;
- automated planning;
- reinforcement learning.

The central scientific contribution is not simply the application of RL to molecular dynamics.

It is the creation of a new representation in which **high-level structural interventions become reusable, stochastic, physically grounded computational actions**.

The long-term objective is to make it possible to write, execute, learn, compare, compose, and eventually automatically discover programs for molecular conformational change.