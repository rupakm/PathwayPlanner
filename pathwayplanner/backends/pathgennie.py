"""PathGennie adapter: selection-based event search as an action implementation.

The ONLY module allowed to import pathgennie.

Placement rationale: the PathGennie driver is a sequential adaptive search
(a swarm of tau1 trials, softmax selection on a progress metric, a tau2
commit, iterated to convergence), not an independent-replica swarm. It
therefore does not implement the `Backend.run_bursts` protocol; it
constitutes a complete physical implementation of an action, realizing
the selection policy rho internally. Actions use it by overriding
`Action.execute`/`evaluate` around `run_driver_search`, giving the
unbiased, selection-driven implementation family — the counterpart to
bias-based burst implementations served by the Trails-MD backend.

Mapping to the driver API (pathgennie.core.driver.PathGennieDriver):

- The event specification is the driver's `convergence_fn`, which the
  driver evaluates on the committed anchor's full coordinates once per
  cycle. Consequently a post-hoc evaluation of the event on the final
  saved frame decides convergence exactly: every committed anchor was
  tested during the run, so the final frame satisfies the event if and
  only if the driver stopped by convergence rather than budget.
- The CV enters twice: as the projection scoring swarm trials (through
  TargetMetric, or EscapeMetric when no target is given) and as the
  feature map applied to saved frames for the returned Trajectory.
- The budget caps the cycle count: one cycle costs
  max_trial*tau1 + tau2 integrator steps, and max_cycle is reduced so
  the total cannot exceed Budget.max_steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from pathwayplanner.actions.base import ActionResult, Outcome
from pathwayplanner.backends.base import Budget, Trajectory
from pathwayplanner.cv import CVSpace
from pathwayplanner.states import State

try:
    from pathgennie.core.driver import PathGennieDriver
    from pathgennie.core.progress import EscapeMetric, TargetMetric

    HAVE_PATHGENNIE = True
except ImportError:
    HAVE_PATHGENNIE = False


@dataclass
class DriverSearchSpec:
    """Specification of one driver-based event search.

    Attributes:
        space: The CV space (projection from (n_atoms, 3) coordinates plus
            metric); scores swarm trials and builds the returned
            Trajectory's frames. A PeriodicCV's `periods` are passed
            through to the driver's metric so periodic components use
            minimum-image differences.
        event: Predicate on full coordinates defining the structural event;
            becomes the driver's convergence_fn.
        target_cv: CV-space target. When given, trials are scored by
            TargetMetric (negated distance to the target); when None, by
            EscapeMetric (distance from the starting CV).
        tau1: Steps per swarm trial (fresh velocities).
        tau2: Steps for the committed extension (continued velocities).
        max_trial: Swarm size per cycle.
        max_cycle: Cycle cap before budget reduction.
        sigma: Softmax selection temperature.
    """

    space: "CVSpace"
    event: Callable[[np.ndarray], bool]
    target_cv: np.ndarray | None
    tau1: int
    tau2: int
    max_trial: int
    max_cycle: int
    sigma: float = 0.1


@dataclass
class DriverSearchResult:
    """Outcome of one driver search.

    `trajectory.frames` holds the full coordinates of each saved anchor
    frame (configuration features; consumers project them through a
    CVSpace); `trajectory.configurations` holds the same arrays, each a
    valid restart point via Engine.create_handle.
    """

    trajectory: Trajectory
    converged: bool
    n_cycles: int
    cost: float


def run_driver_search(
    engine: Any,
    start_position: np.ndarray,
    spec: DriverSearchSpec,
    *,
    seed: int | None,
    budget: Budget,
    executor: Any = None,
) -> DriverSearchResult:
    """Execute one event search with the PathGennie driver.

    `engine` is any pathgennie Engine; `start_position` is passed to the
    engine's state constructor (`create_state` when present, otherwise
    `create_handle`).
    """
    if not HAVE_PATHGENNIE:
        raise ImportError(
            "pathgennie is not installed; install with pathwayplanner[pathgennie]"
        )

    steps_per_cycle = spec.max_trial * spec.tau1 + spec.tau2
    max_cycle = max(1, min(spec.max_cycle, int(budget.max_steps // steps_per_cycle)))

    projection_fn = lambda coords, **kwargs: spec.space.project(coords)  # noqa: E731
    periodic = getattr(spec.space, "periods", None)
    if spec.target_cv is not None:
        progress = TargetMetric(
            projection_fn, np.asarray(spec.target_cv, dtype=float),
            periodic=periodic,
        )
    else:
        if hasattr(engine, "create_state"):
            probe = engine.create_state(np.asarray(start_position, dtype=float))
        else:
            probe = engine.create_handle(np.asarray(start_position, dtype=float))
        start_cv = spec.space.project(engine.get_coords(probe))
        engine.release(probe)
        progress = EscapeMetric(projection_fn, start_cv, periodic=periodic)

    driver = PathGennieDriver(
        engine,
        progress,
        convergence_fn=spec.event,
        executor=executor,
        sigma=spec.sigma,
        seed=seed,
        verbosity=0,
    )
    if hasattr(engine, "create_state"):
        initial = engine.create_state(np.asarray(start_position, dtype=float))
    else:
        initial = engine.create_handle(np.asarray(start_position, dtype=float))

    coords_trajectory, metrics = driver.run(
        initial,
        tau1=spec.tau1,
        tau2=spec.tau2,
        max_trial=spec.max_trial,
        max_cycle=max_cycle,
        save_freq=1,
    )

    n_cycles = int(len(metrics))
    configurations = [np.asarray(c) for c in coords_trajectory]
    # Frames hold configuration features (coordinates); consumers project
    # them through the CVSpace when needed.
    frames = np.asarray(coords_trajectory, dtype=float)
    # Every committed anchor was tested against the event during the run,
    # so the final frame satisfies it iff the driver stopped by convergence.
    converged = bool(configurations) and bool(spec.event(configurations[-1]))
    cost = float(n_cycles * steps_per_cycle)
    return DriverSearchResult(
        trajectory=Trajectory(frames=frames, configurations=configurations, cost=cost),
        converged=converged,
        n_cycles=n_cycles,
        cost=cost,
    )


def search_to_action_result(result: DriverSearchResult) -> ActionResult:
    """Translate a driver search into the language's outcome semantics.

    Convergence maps to SUCCESS with the converged frame as the successor
    state; a non-converged search maps to BUDGET_EXCEEDED (the driver has
    no other termination mode) with the final anchor as the successor so
    recipes can continue or retry from where the search stopped.
    """
    frames = result.trajectory.frames
    configurations = result.trajectory.configurations
    if len(frames) == 0:
        return ActionResult(
            outcome=Outcome.FAILURE,
            successor_states=[],
            trajectories=[result.trajectory],
            cost=result.cost,
            metadata={"reason": "empty_search_trajectory"},
        )
    final = State(configuration=configurations[-1], features=np.asarray(frames[-1]))
    outcome = Outcome.SUCCESS if result.converged else Outcome.BUDGET_EXCEEDED
    return ActionResult(
        outcome=outcome,
        successor_states=[final],
        trajectories=[result.trajectory],
        event_scores={"n_cycles": float(result.n_cycles)},
        cost=result.cost,
        metadata={"implementation_family": "pathgennie_driver"},
    )


def make_backend(*args, **kwargs):
    """The PathGennie integration is not a burst Backend; see the module
    docstring. Use run_driver_search inside an action's execute instead."""
    raise NotImplementedError(
        "PathGennie integrates as an action implementation (run_driver_search), "
        "not as a run_bursts Backend"
    )
