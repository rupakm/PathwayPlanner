"""Trails-MD backend adapter: the burst API behind the Backend protocol.

The ONLY module allowed to import trails_md.

Maps the language's (start states, Implementation, Budget) onto
trails_md.bursts.run_bursts (branch `burst-api`):

- `State.configuration` is a coordinate file Path or a trails_md
  FrameRef; both are valid start frames for the burst API, and the
  FrameRefs returned in results make every visited frame a restart
  point.
- `Implementation.bias` must be a trails_md.bursts.BiasSpec or None.
  BiasSpec is OpenMM-native (nm, kJ/mol, radians); returned coordinates
  are in Angstrom (MDAnalysis convention) — the CVSpace projection is
  responsible for consuming Angstrom (n_atoms, 3) frames.
- `Implementation.n_replicas` is interpreted per start state
  (n_replicas_per_frame).
- The Budget caps n_steps per burst. The burst counter is derived from
  the workdir's contents, so reproducing a run requires an empty
  workdir, and concurrent calls need distinct workdirs.

Failed replicas (BurstResult.success False) are dropped from the
returned ensemble — a smaller swarm, not an exception — matching the
burst API's own contract. A successful result without loadable
coordinates is an environment error (missing MDAnalysis) and raises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from pathwayplanner.backends.base import Budget, Trajectory
from pathwayplanner.compiler.base import Implementation
from pathwayplanner.cv import CVSpace
from pathwayplanner.states import State

try:
    import trails_md  # noqa: F401

    HAVE_TRAILS_MD = True
except ImportError:
    HAVE_TRAILS_MD = False


@dataclass
class TrailsMDBackend:
    """Backend protocol implementation over trails_md.bursts.run_bursts.

    Attributes:
        system: A trails_md.bursts.BurstSystem describing engine and
            topology; built once and reused (enables warm engine reuse).
        space: CVSpace used to featurize returned frames and states.
        workdir: Directory for burst outputs; owns the burst counter.
        stride: Frame save stride in integrator steps.
        execution: Execution backend name or instance ("local", "slurm",
            "pbs", or an ExecutionBackend).
        base_seed: Base seed for the per-walker seed derivation.
        run_bursts_fn: Injection point for tests; defaults to the real
            trails_md.bursts.run_bursts, resolved lazily so this module
            imports without trails-md installed.
    """

    system: Any
    space: CVSpace
    workdir: Path
    stride: int = 10
    execution: Any = "local"
    base_seed: int = 0
    run_bursts_fn: Callable[..., list] | None = field(default=None, repr=False)

    def _resolve_run_bursts(self) -> Callable[..., list]:
        if self.run_bursts_fn is not None:
            return self.run_bursts_fn
        if not HAVE_TRAILS_MD:
            raise ImportError(
                "trails-md is not installed; install with pathwayplanner[trailsmd]"
            )
        from trails_md.bursts import run_bursts as real_run_bursts

        return real_run_bursts

    def make_state(
        self, configuration: Any, coordinates: np.ndarray | None = None
    ) -> State:
        """Wrap a coordinate file Path or FrameRef into a planner State.

        When the (n_atoms, 3) coordinates are provided, features are their
        CV projection; otherwise features are empty until first projection.
        """
        if coordinates is not None:
            features = self.space.project(np.asarray(coordinates, dtype=float))
        else:
            features = np.empty(0)
        return State(configuration=configuration, features=features)

    def run_bursts(
        self,
        start_states: Sequence[State],
        implementation: Implementation,
        budget: Budget,
    ) -> list[Trajectory]:
        run = self._resolve_run_bursts()
        n_steps = int(min(implementation.n_steps, budget.max_steps))
        results = run(
            self.system,
            [state.configuration for state in start_states],
            n_steps=n_steps,
            stride=self.stride,
            n_replicas_per_frame=implementation.n_replicas,
            bias=implementation.bias,
            execution=self.execution,
            base_seed=self.base_seed,
            workdir=self.workdir,
        )

        trajectories: list[Trajectory] = []
        for result in results:
            if not result.success:
                continue
            if result.coordinates is None:
                raise RuntimeError(
                    f"burst {result.trajectory_path} succeeded but returned no "
                    "coordinates; trajectory loading requires MDAnalysis in the "
                    "trails-md environment"
                )
            # Frames hold configuration features (Angstrom coordinates);
            # consumers project them through a CVSpace when needed.
            frames = np.asarray(result.coordinates, dtype=float)
            trajectories.append(
                Trajectory(
                    frames=frames,
                    configurations=list(result.frame_refs),
                    cost=float(result.steps_run),
                )
            )
        return trajectories


def make_backend(**kwargs) -> TrailsMDBackend:
    """Construct a TrailsMDBackend; requires trails-md at call time."""
    if not HAVE_TRAILS_MD:
        raise ImportError(
            "trails-md is not installed; install with pathwayplanner[trailsmd]"
        )
    return TrailsMDBackend(**kwargs)
