"""Grid-exact reference committor for 2D toy potentials.

Discretizes overdamped Langevin dynamics as a nearest-neighbor Markov
chain on a regular grid (Metropolis-style rates) and solves the discrete
Dirichlet problem q = Pq with q = 0 on A and q = 1 on B directly. Ground
truth for validating action "success" labels on toy landscapes.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

Potential = Callable[[np.ndarray], float]
Region = Callable[[np.ndarray], bool]


def reference_committor(
    potential: Potential,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    in_a: Region,
    in_b: Region,
    kT: float,
) -> Callable[[np.ndarray], float]:
    """Solve for the forward committor on a regular grid.

    Returns a function evaluating q at an arbitrary point via
    nearest-grid-node lookup.
    """
    nx, ny = len(grid_x), len(grid_y)
    n = nx * ny
    values = np.array(
        [[potential(np.array([x, y])) for y in grid_y] for x in grid_x]
    )

    def idx(i: int, j: int) -> int:
        return i * ny + j

    is_a = np.zeros((nx, ny), dtype=bool)
    is_b = np.zeros((nx, ny), dtype=bool)
    for i, x in enumerate(grid_x):
        for j, y in enumerate(grid_y):
            point = np.array([x, y])
            is_a[i, j] = in_a(point)
            is_b[i, j] = in_b(point)

    # Metropolis rates to the 4 neighbors; the chain's committor converges
    # to the diffusion's as the grid refines.
    system = np.zeros((n, n))
    rhs = np.zeros(n)
    for i in range(nx):
        for j in range(ny):
            k = idx(i, j)
            if is_a[i, j]:
                system[k, k] = 1.0
                rhs[k] = 0.0
                continue
            if is_b[i, j]:
                system[k, k] = 1.0
                rhs[k] = 1.0
                continue
            neighbors = [
                (i + di, j + dj)
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if 0 <= i + di < nx and 0 <= j + dj < ny
            ]
            rates = np.array(
                [
                    min(1.0, np.exp(-(values[ni, nj] - values[i, j]) / kT))
                    for ni, nj in neighbors
                ]
            )
            total = rates.sum()
            system[k, k] = total
            for (ni, nj), rate in zip(neighbors, rates):
                system[k, idx(ni, nj)] = -rate
    q_flat = np.linalg.solve(system, rhs)
    q_grid = q_flat.reshape(nx, ny)

    def q(point: np.ndarray) -> float:
        i = int(np.clip(np.searchsorted(grid_x, point[0]), 0, nx - 1))
        j = int(np.clip(np.searchsorted(grid_y, point[1]), 0, ny - 1))
        return float(q_grid[i, j])

    return q
