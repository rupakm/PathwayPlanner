"""The reproducibility statistic must be judged against its own null.

Stage 1 reported JS = 0.044 against a gate of 0.1 and called it a pass.
Simulating the null shows two batches of 30 drawn from the *same*
distribution have median JS 0.019 and a 90th percentile of 0.061, so
0.044 is an unremarkable draw and the gate could only have caught a gross
discrepancy. The fix is to report how surprising the observed divergence
is under the hypothesis that both batches came from one distribution.
"""

import pytest

from pathwayplanner import Outcome
from pathwayplanner.evaluation import OutcomeModel


def model(successes, failures):
    return OutcomeModel.from_outcomes(
        [Outcome.SUCCESS] * successes + [Outcome.FAILURE] * failures
    )


def test_same_distribution_is_not_surprising():
    p = model(24, 6).js_pvalue(model(26, 4), n_resamples=2000, seed=0)
    assert p > 0.2


def test_clearly_different_distributions_are_surprising():
    p = model(29, 1).js_pvalue(model(3, 27), n_resamples=2000, seed=0)
    assert p < 0.01


def test_identical_batches_are_maximally_unsurprising():
    assert model(20, 10).js_pvalue(model(20, 10), n_resamples=500, seed=0) > 0.5


def test_pvalue_is_a_probability():
    p = model(18, 12).js_pvalue(model(22, 8), n_resamples=500, seed=1)
    assert 0.0 <= p <= 1.0


def test_degenerate_batches_are_reported_not_silently_passed():
    """Two all-success batches give JS = 0 and a p-value of 1, which is the
    honest answer: the statistic cannot distinguish anything there. Stage 2
    hit exactly this case."""
    a, b = model(30, 0), model(30, 0)
    assert a.js_divergence(b) == pytest.approx(0.0)
    assert a.js_pvalue(b, n_resamples=200, seed=0) == pytest.approx(1.0)
