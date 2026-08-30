"""AdK domain partition and the geometry behind its collective variables.

The residue sets and the pure-geometry kernels (centroid distance, centroid
angle, superposition RMSD) are checkable without any structure file, so they
are tested here unconditionally. Everything that needs a built structure
lives in test_adk_system.py behind a file-existence skip.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "adk"))

import domains


def test_domains_partition_all_214_residues():
    union = domains.CORE | domains.NMP | domains.LID
    assert union == set(range(1, 215))
    assert not (domains.CORE & domains.NMP)
    assert not (domains.CORE & domains.LID)
    assert not (domains.NMP & domains.LID)


def test_domain_sizes_match_the_beckstein_partition():
    assert len(domains.NMP) == 30  # 30-59
    assert len(domains.LID) == 38  # 122-159
    assert len(domains.CORE) == 214 - 30 - 38


def test_hinges_lie_between_the_domains_they_join():
    for lo, hi in domains.NMP_HINGES.values():
        span = set(range(lo, hi + 1))
        assert span & (domains.NMP | domains.CORE) == span
    for lo, hi in domains.LID_HINGES.values():
        span = set(range(lo, hi + 1))
        assert span & (domains.LID | domains.CORE) == span


def test_centroid_distance_of_two_atom_groups():
    coords = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 3.0, 4.0]])
    assert domains.centroid_distance(coords, [0, 1], [2]) == pytest.approx(
        np.linalg.norm([1.0, -3.0, -4.0])
    )


def test_centroid_angle_is_measured_at_the_vertex_group_in_degrees():
    coords = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    assert domains.centroid_angle(coords, [0], [1], [2]) == pytest.approx(90.0)
    straight = np.array([[-1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    assert domains.centroid_angle(straight, [0], [1], [2]) == pytest.approx(180.0)


def test_kabsch_rmsd_is_zero_under_rotation_and_translation():
    rng = np.random.default_rng(0)
    reference = rng.normal(size=(20, 3))
    angle = 0.7
    rotation = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    mobile = reference @ rotation.T + np.array([5.0, -2.0, 1.0])
    # The closed-form residual is a difference of large sums, so an exact match
    # cancels to ~sqrt(eps) rather than to eps -- still nine orders of magnitude
    # below the sub-Angstrom differences the CV has to resolve.
    assert domains.kabsch_rmsd(mobile, reference) == pytest.approx(0.0, abs=1e-6)


def test_kabsch_rmsd_matches_the_analytic_value_for_a_pure_displacement():
    # One atom displaced by d in an otherwise identical pair: the optimal
    # superposition of a two-point set leaves rmsd = d/2.
    reference = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    mobile = np.array([[0.0, 0.0, 0.0], [12.0, 0.0, 0.0]])
    assert domains.kabsch_rmsd(mobile, reference) == pytest.approx(1.0)


def test_kabsch_rmsd_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        domains.kabsch_rmsd(np.zeros((3, 3)), np.zeros((4, 3)))
