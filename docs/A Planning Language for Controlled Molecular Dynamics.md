# A Planning Language for Controlled Molecular Dynamics

## 1. Vision

Molecular simulations provide a physically grounded way to study conformational change, but there is a substantial gap between how scientists think about molecular mechanisms and how they control molecular dynamics simulations.

A scientist may describe a transition in terms such as:

- a hinge opens;
- an interface weakens;
- two domains separate;
- a domain rotates;
- a loop rearranges;
- a binding pocket becomes exposed.

An MD engine, however, does not directly understand these operations. To investigate such a mechanism, the scientist must translate the structural idea into low-level choices involving collective variables, restraints, bias potentials, enhanced-sampling methods, trajectory lengths, replica counts, and selection criteria.

We propose to introduce an intermediate abstraction:

> **a planning language for controlled molecular dynamics in which programs describe high-level structural interventions, while an underlying runtime realizes those interventions through stochastic, physically grounded MD and enhanced-sampling searches.**

For example, a program might say:

```text id="9dzapq"
weaken_interface(LID, CORE)
open_hinge(LID)
relax()
```

This program should not be interpreted as directly manipulating molecular coordinates. It does not mean "set the hinge angle to a particular value."

Instead, each action specifies a structural event that the simulation should attempt to realize. The runtime translates that event into one or more physically grounded simulation procedures, executes those procedures, and returns the observed outcome.

The resulting architecture is:

\[
\boxed{
\text{Structural hypothesis}
\longrightarrow
\text{Molecular program}
\longrightarrow
\text{MD-based intervention/search}
\longrightarrow
\text{Physical outcome}.
}
\]

The central idea is therefore not to replace molecular dynamics with symbolic planning. Rather, it is to make MD programmable at the level at which scientists naturally reason about conformational mechanisms.

---

# 2. The Programming Model

The proposed language is best understood as a **planning language with stochastic actions**.

A program consists of:

1. **structural actions**, such as opening a hinge or weakening an interface;
2. **recipes**, which compose actions into larger strategies;
3. **control structures**, such as sequencing, conditionals, and bounded repetition.

A simple example is:

```text id="3v2q1e"
recipe open_gate:

    weaken_interface(GATE, CORE)

    result = open_hinge(GATE)

    if result.success:
        rotate_domain(GATE)

    else:
        explore_gate_region()

    relax()
```

The key feature is that actions are not deterministic.

Executing

```text id="8pl61n"
open_hinge(GATE)
```

does not guarantee that the hinge will open. Instead, it launches a physically grounded search for trajectories that realize the desired structural event.

Possible outcomes include:

- success;
- partial success;
- failure;
- an alternative conformational transition;
- structural instability;
- exhaustion of the computational budget.

Thus the appropriate conceptual model is:

\[
\boxed{
\text{action}
=
\text{a stochastic search procedure for realizing a structural event}.
}
\]

This gives the language a natural interpretation as a system for **adaptive planning over molecular simulations**.

---

# 3. Molecular Actions

Let \(x\in\mathcal X\) denote a full molecular configuration. In practice, programs need not reason directly about every atomic coordinate. Instead, they may operate over an abstract structural state

\[
s=\phi(x),
\]

where \(\phi\) extracts information relevant to planning, such as:

- domain positions and orientations;
- contact patterns;
- collective variables;
- secondary structure;
- learned slow coordinates;
- metastable-state labels.

A molecular action has the form

\[
a=(\text{verb},\text{object},\text{parameters}).
\]

Examples include:

\[
\operatorname{OpenHinge}(H,\delta),
\]

\[
\operatorname{SeparateDomains}(A,B,\delta),
\]

\[
\operatorname{BreakInterface}(A,B),
\]

\[
\operatorname{RotateDomain}(D,\theta),
\]

or

\[
\operatorname{RearrangeLoop}(L).
\]

The important point is that these actions describe **intent**, not a fixed simulation protocol.

For example,

```text id="svw0qi"
open_hinge(H)
```

may be realized by several different physical strategies:

- biasing a hinge angle;
- biasing an inter-domain distance;
- weakening a network of contacts that constrains the hinge;
- exploring a local slow mode;
- launching many short trajectories and selecting promising outcomes;
- using OPES or another enhanced-sampling procedure over an appropriate representation.

Thus:

\[
\boxed{
\text{structural action}
\neq
\text{collective variable}.
}
\]

A collective variable is one possible means of implementing an action.

The action itself specifies the event we want to attempt.

---

# 4. Actions as Stochastic Physical Searches

Each action should have three conceptual components.

First, it has an **event specification** describing what counts as progress or success.

For example, for an action

\[
a=\operatorname{OpenHinge}(H,\delta),
\]

we may define a hinge-opening coordinate

\[
\xi_H(x)
\]

and regard the action as successful when

\[
\xi_H(x')-\xi_H(x)\geq\delta.
\]

Second, the action has a set of possible **physical implementations**:

\[
\mathcal I(a,x).
\]

An implementation may specify:

\[
I=(\xi,V,T,N,\rho),
\]

where:

- \(\xi\) is a collective variable or learned representation;
- \(V\) specifies the bias or intervention;
- \(T\) is the simulation duration;
- \(N\) is the number of replicas or short trajectories;
- \(\rho\) is a policy for selecting, resampling, or continuing trajectories.

Third, the action returns an **outcome**.

A useful outcome type might be:

\[
\operatorname{Outcome}
=
\begin{cases}
\operatorname{Success}(s',m),\\
\operatorname{Partial}(s',m),\\
\operatorname{Failure}(s',m),\\
\operatorname{Alternative}(s',m),\\
\operatorname{Unstable}(s',m),\\
\operatorname{BudgetExceeded}(s',m),
\end{cases}
\]

where \(m\) contains metadata such as:

- event score;
- physical stability;
- simulation cost;
- implementation used;
- uncertainty.

Mathematically, an action induces a distribution over outcomes and successor states:

\[
\llbracket a\rrbracket:
S
\rightarrow
\mathcal D(\operatorname{Outcome}\times S).
\]

Equivalently,

\[
P(o,s'\mid s,a)
\]

describes the probability that action \(a\), when started in state \(s\), produces outcome \(o\) and reaches state \(s'\).

This formulation captures an important feature of molecular simulation: **failure is not an exceptional implementation detail. It is part of the semantics of the action.**

---

# 5. Action Compilation: Connecting Structural Intent to MD

The central systems problem is to translate a high-level action into a concrete simulation experiment.

We call this process **action compilation**.

Formally, an action compiler is a function

\[
\mathcal C(a,x)\rightarrow I,
\]

where \(I\) is a concrete implementation.

For example:

```text id="s1rgp2"
open_hinge(LID)
```

might compile to:

\[
\begin{aligned}
\text{CV} &:= \text{LID hinge angle},\\
\text{method} &:= \text{adaptive short-burst MD},\\
\text{intervention} &:= \text{weak directional bias},\\
\text{replicas} &:= N,\\
\text{budget} &:= T.
\end{aligned}
\]

In another molecular context, the same action might instead compile to a contact-based intervention or a learned local slow coordinate.

The compiler therefore separates:

\[
\boxed{
\text{What structural event should be attempted?}
}
\]

from

\[
\boxed{
\text{How should the simulation attempt it?}
}
\]

Initially, the compiler can be rule-based. For example:

- use an angular CV when a clear hinge axis is available;
- use contact weakening when motion is constrained by a small interface;
- use short-burst exploration when the relevant coordinate is uncertain.

Later, the compiler itself can become adaptive or learned.

Given candidate implementations \(I\in\mathcal I(a,x)\), we may estimate:

\[
P(\operatorname{Success}\mid s,a,I)
\]

and choose

\[
I^\star
=
\arg\max_I
\left[
\operatorname{ExpectedSuccess}(I)
-
\lambda\operatorname{Cost}(I)
-
\mu\operatorname{Instability}(I)
\right].
\]

This makes the action compiler a potential learning problem in its own right.

---

# 6. Recipes: Building Large Strategies from Molecular Skills

The most important advantage of introducing a language rather than simply defining an action library is **composition**.

Individual molecular actions can be combined into reusable recipes.

For example:

```text id="hkr04c"
recipe weaken_gate:

    weaken_interface(GATE, CORE)
    relax()
```

This can then be used as part of a larger recipe:

```text id="nqg4e9"
recipe open_gate:

    weaken_gate()

    result = open_hinge(GATE)

    if result.success:
        rotate_domain(GATE)

    elif result.partial:
        explore_gate_region()

    else:
        fail
```

A still larger recipe might be:

```text id="sngp8w"
recipe activate_protein:

    result = open_gate()

    if result.success:
        rearrange_active_site_loop()
        stabilize_active_state()
        relax()

    else:
        explore_alternative_pathway()
```

Thus we obtain a hierarchy:

\[
\boxed{
\text{primitive actions}
\rightarrow
\text{molecular skills}
\rightarrow
\text{recipes}
\rightarrow
\text{large mechanistic strategies}.
}
\]

This is closely related to the attraction of FoldIt recipes: useful strategies can be assembled from smaller reusable strategies.

The important difference is that molecular recipes operate over a stochastic physical system.

A recipe cannot assume that its subrecipes deterministically achieve their goals.

Instead, composition must be **outcome-aware**.

---

# 7. Compositionality

Compositionality is one of the central scientific questions of the proposed language.

There are three different notions that should be kept separate.

## 7.1 Formal compositionality

At the level of language semantics, composition is straightforward.

Suppose actions \(a_1\) and \(a_2\) induce stochastic transition kernels

\[
P_{a_1}(s,ds')
\]

and

\[
P_{a_2}(s',ds'').
\]

Then sequential composition has the natural meaning:

\[
P_{a_1;a_2}(s,ds'')
=
\int
P_{a_2}(s',ds'')
P_{a_1}(s,ds').
\]

Thus stochasticity does not prevent formal composition.

A composite recipe simply denotes the stochastic process obtained by executing its components in sequence.

Similarly, conditional composition can branch on action outcomes:

```text id="03q5i7"
result = open_hinge(H)

if result.success:
    rotate_domain(D)

elif result.partial:
    explore()

else:
    weaken_interface(A, B)
```

The semantics of the composite program is determined by the semantics of its components and the control structure connecting them.

In this sense, the language is formally compositional by construction.

---

## 7.2 Interface compositionality

The more interesting issue is what one recipe communicates to the next.

At the atomic level, two successful executions of the same recipe will generally produce different configurations.

Therefore, recipes should not expose only a binary result such as:

```text id="pdxsyb"
success
```

Instead, they should expose an abstract description of the resulting state.

For example:

```text id="65pk2l"
open_gate()
```

may produce one of:

\[
\{
\texttt{closed},
\texttt{partially\_open},
\texttt{open},
\texttt{alternative},
\texttt{unstable}
\}.
\]

A subsequent recipe may specify which of these states it can accept.

For example:

\[
\operatorname{Pre}_{\texttt{rotate\_gate}}
=
\{
\texttt{partially\_open},
\texttt{open}
\}.
\]

Thus composition occurs through **abstract molecular interfaces**.

A recipe may have a contract:

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
- \(\operatorname{Post}_P\) describes possible abstract output states;
- \(K_P\) describes the stochastic outcome model;
- \(B_P\) describes the computational or physical resource budget.

Compatibility between two recipes is therefore not simply a yes-or-no property.

Suppose recipe \(P_1\) is followed by \(P_2\). A useful quantity is:

\[
\Pr[
S'\in\operatorname{Pre}_{P_2}
\mid
S=s,P_1
].
\]

This measures how likely \(P_1\) is to produce a state from which \(P_2\) can meaningfully proceed.

---

## 7.3 Physical compositionality

The deepest question is whether independently useful molecular recipes remain useful when combined.

Suppose:

\[
P_1:
A\leadsto B
\]

and

\[
P_2:
B\leadsto C.
\]

At the language level, the composite program

\[
P_1;P_2
\]

is perfectly well-defined.

Physically, however, its success is not guaranteed.

The first recipe may produce a heterogeneous ensemble of states within \(B\). Some of these states may be excellent starting points for \(P_2\), while others may not.

The true composition is:

\[
\Pr(C\mid A,P_1;P_2)
=
\int
\Pr(C\mid s,P_2)
\,dP_{P_1}(s\mid A).
\]

This equation highlights the central challenge.

Knowing that \(P_1\) "succeeded" may not provide enough information. The distribution of states produced by \(P_1\) matters.

Therefore:

\[
\boxed{
\text{Good physical compositionality requires useful abstractions of recipe outputs.}
}
\]

This leads to a central research question:

> **Under what conditions can independently developed molecular intervention recipes be composed to reliably produce larger conformational transitions?**

This question is scientifically interesting even without reinforcement learning.

---

# 8. Molecular Programs as Executable Mechanistic Hypotheses

A useful consequence of the programming model is that recipes can represent mechanistic hypotheses.

For example:

```text id="c3h7kj"
recipe activate:

    weaken_interface(REGULATORY, CORE)

    result = open_hinge(REGULATORY)

    if result.success:
        rotate_domain(REGULATORY)
        form_contact(ACTIVE_SITE, STABILIZER)

    relax()
```

This represents the hypothesis:

\[
\text{interface weakening}
\rightarrow
\text{hinge opening}
\rightarrow
\text{domain rotation}
\rightarrow
\text{stabilization}.
\]

The simulation does not merely generate a trajectory. It executes the hypothesized mechanism.

The recipe can fail at specific points:

- the interface may not need to weaken first;
- the hinge may not open after the interface changes;
- rotation may occur before complete interface disruption;
- an alternative transition may be discovered.

Thus programs can be used to compare competing mechanistic hypotheses.

For example:

\[
P_1:
\text{break interface}
\rightarrow
\text{open hinge}
\]

can be compared with:

\[
P_2:
\text{open hinge}
\rightarrow
\text{break interface}.
\]

The output of the framework is then not merely a set of pathways, but evidence about which structured intervention strategies are physically effective.

---

# 9. Relation to FoldIt Recipes

FoldIt provides an important conceptual inspiration because it demonstrates the value of representing protein-manipulation strategies as compositions of reusable operations.

The proposed system shares this central idea:

\[
\boxed{
\text{small operations}
\rightarrow
\text{reusable recipes}
\rightarrow
\text{larger strategies}.
}
\]

However, the proposed language has a different semantic foundation.

A FoldIt recipe operates primarily over an optimization or structural manipulation system. At an abstract level, an operation can be viewed as producing a new structure:

\[
x'
=
f(x).
\]

A molecular intervention program operates over stochastic physical dynamics:

\[
x'
\sim
P_a(x,\cdot).
\]

The difference is important.

A molecular recipe must explicitly account for:

- stochastic outcomes;
- incomplete success;
- action failure;
- alternative transitions;
- relaxation;
- metastability;
- computational budgets.

Thus the analogy with FoldIt is strongest at the level of **programmable composition** rather than deterministic semantics.

The proposed system can be viewed as asking:

> Can the recipe abstraction be extended from protein optimization to the discovery and control of conformational transitions in a stochastic physical simulator?

---

# 10. System Architecture

The language should sit above existing simulation infrastructure.

The overall architecture is:

\[
\boxed{
\begin{array}{c}
\textbf{Planner or User}\\
\text{human-designed recipes / search / RL}\\
\downarrow\\
\textbf{Molecular Program}\\
\text{actions, recipes, control structures}\\
\downarrow\\
\textbf{Action Compiler and Runtime}\\
\text{implementation selection and execution}\\
\downarrow\\
\textbf{Simulation Backends}\\
\text{PathGennie / Trails-MD / enhanced sampling}\\
\downarrow\\
\textbf{MD Engine}\\
\text{physically grounded trajectories}\\
\downarrow\\
\textbf{Outcome Abstraction}\\
\text{events, states, failures, alternatives}
\end{array}
}
\]

The language should be independent of the mechanism used to choose programs.

A recipe may be:

- written manually by a domain expert;
- generated through heuristic search;
- selected by a planning algorithm;
- optimized through evolutionary search;
- synthesized automatically;
- selected by a reinforcement-learning policy.

This separation is deliberate.

The programming model is the **control interface**.

RL is only one possible mechanism for deciding which actions or recipes to execute.

---

# 11. Learning and Adaptation

Once actions and recipes have well-defined outcome semantics, repeated execution generates data:

\[
(s,a,o,s').
\]

This allows several distinct learning problems.

### Learning action feasibility

Estimate:

\[
P(o=\operatorname{Success}\mid s,a).
\]

This predicts when an action is likely to work.

### Learning implementation selection

For multiple possible implementations \(I\), estimate:

\[
P(\operatorname{Success}\mid s,a,I).
\]

The compiler can then choose an implementation appropriate for the current state.

### Learning recipe models

Estimate:

\[
P(o,s'\mid s,P).
\]

This summarizes the behavior of reusable recipes.

### Learning to plan

A planner or RL agent may then select actions or recipes based on the learned transition model.

The hierarchy is therefore:

\[
\boxed{
\text{first define actions}
\rightarrow
\text{then model their behavior}
\rightarrow
\text{then learn to compose or select them}.
}
\]

This ordering avoids requiring reinforcement learning to solve the entire problem from the beginning.

---

# 12. A Minimal Prototype

The first prototype should focus on whether the abstraction itself is useful.

A suitable initial benchmark is **adenylate kinase**, because its conformational change has an interpretable domain-level structure involving the CORE, LID, and NMP-binding domains.

The initial action vocabulary could be:

```text id="3cq8zh"
open_hinge(LID)
close_hinge(LID)

open_hinge(NMP)
close_hinge(NMP)

weaken_interface(LID, CORE)
strengthen_interface(LID, CORE)

rotate_domain(LID)

explore(region_or_coordinate)

relax()
```

A simple recipe might be:

```text id="jxy79q"
recipe open_LID:

    weaken_interface(LID, CORE)

    result = open_hinge(LID)

    if result.success:
        rotate_domain(LID)

    elif result.partial:
        explore(LID_motion)

    relax()
```

An alternative mechanistic hypothesis might reverse the order:

```text id="pugzh4"
recipe open_LID_alternative:

    result = open_hinge(LID)

    if result.success:
        weaken_interface(LID, CORE)

    relax()
```

These recipes can be evaluated for:

1. probability of producing the intended structural transition;
2. physical stability after relaxation;
3. simulation cost;
4. diversity of discovered pathways;
5. reproducibility of the outcome distributions;
6. compatibility with subsequent recipes.

The first goal is not to demonstrate that RL can outperform all existing pathway methods.

The first goal is to establish whether high-level molecular recipes are meaningful, executable, and composable abstractions.

---

# 13. Core Research Questions

The proposed programming model leads to a coherent set of research questions.

### 1. Action semantics

Can high-level structural events such as opening, separating, rotating, and interface disruption be given robust operational definitions?

### 2. Action compilation

Can structural actions be reliably translated into effective MD-based search procedures?

### 3. Outcome abstraction

What abstract representation of molecular states is sufficiently informative to support recipe composition?

### 4. Physical compositionality

When do independently validated molecular skills remain effective when combined into larger recipes?

### 5. Mechanistic programming

Can recipes represent and experimentally distinguish competing hypotheses about the order of events in a conformational transition?

### 6. Adaptive execution

Can the system learn which physical implementation of an action is appropriate in a given molecular context?

### 7. Automated planning

Once action and recipe models exist, can search or RL discover useful programs for reaching new conformational states?

These questions form a natural progression. The early questions can be investigated without solving the full automated planning problem.

---

# 14. Research Thesis

The core thesis of the project is:

> **Molecular dynamics should be programmable at a structural level. A useful abstraction can be built by treating high-level structural interventions as stochastic search procedures over physically valid molecular trajectories. These procedures can be composed into failure-aware recipes, allowing scientists and automated planners to express, execute, compare, and eventually learn strategies for conformational change.**

The central conceptual distinction is:

\[
\boxed{
\text{Formal compositionality}
\neq
\text{Physical compositionality}.
}
\]

Formal compositionality is provided by the language:

\[
\llbracket P_1;P_2\rrbracket
\]

is determined by the semantics of \(P_1\) and \(P_2\).

Physical compositionality is an empirical question:

> Does executing \(P_1\) actually produce an ensemble of states from which \(P_2\) remains effective?

Understanding and improving this relationship may itself become a central scientific contribution.

The resulting view of molecular simulation is therefore:

\[
\boxed{
\text{Programs do not prescribe trajectories.}
}
\]

Instead:

\[
\boxed{
\text{Programs prescribe structured, adaptive strategies for searching for trajectories.}
}
\]

Each execution may produce a different microscopic realization, but the program captures a common higher-level strategy.

This provides a bridge between structural intuition, enhanced sampling, molecular dynamics, planning, and eventually reinforcement learning.

The immediate next step is to determine whether a small set of molecular actions can be given robust stochastic semantics and whether those actions can be composed into recipes whose behavior remains interpretable and physically useful.