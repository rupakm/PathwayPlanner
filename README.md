# PathwayPlanner

A planning language for controlled molecular dynamics.

Programs describe high-level structural interventions — open a hinge, weaken an
interface, rotate a domain — and an underlying runtime realizes those
interventions through stochastic, physically grounded MD and enhanced-sampling
searches. Actions are stochastic search procedures whose failure modes are part
of the language semantics; recipes compose actions with outcome-aware
branching.

See `docs/` for the research design:

- [A Planning Language for Controlled Molecular Dynamics](docs/A%20Planning%20Language%20for%20Controlled%20Molecular%20Dynamics.md) — vision
- [Design and Implementation Plan](docs/Design%20and%20Implementation%20Plan_%20A%20Planning%20Language%20for%20Controlled%20Molecular%20Dynamics.md) — WP1–WP7 phased plan
- [NOTES.md](docs/NOTES.md) — living strategy notes and decision log

## Layout

```
pathwayplanner/
├── states.py          # State: abstract features + retained full configuration
├── actions/           # Action interface (precondition/propose/execute/evaluate),
│                      # Outcome enum, ActionResult, action registry
├── compiler/          # Implementation = (cv, bias, duration, replicas, policy);
│                      # rule-based compiler baseline
├── recipes/           # Combinators (Seq, Cond, Retry, Repeat) and recipe contracts
├── backends/          # Backend protocol; ToyBackend (2D Langevin, no MD engine);
│                      # Trails-MD and PathGennie adapter stubs
└── outcomes/          # Trajectory -> Outcome classifiers
```

Design rule: only `backends/trailsmd.py` and `backends/pathgennie.py` may
import their respective packages. Everything above the `Backend` protocol is
simulator-agnostic.

## Install

```bash
pip install -e ".[dev]"           # core + tests (numpy, pydantic, pytest)
pip install -e ".[trailsmd]"      # Trails-MD backend (when implemented)
pip install -e ".[pathgennie]"    # PathGennie backend (when implemented)
pytest
```

## Status

Pre-alpha scaffold. The toy backend and language semantics are exercised by the
test suite; concrete molecular actions (WP1) and the MD backend adapters come
next, targeting adenylate kinase first.
