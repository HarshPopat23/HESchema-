import pytest

from heschema.metrics import custom_fitness, paired_effect, rate, wilson


def rows_for(before, after, repeats=1):
    return [{"caseId": str(i), "cluster": str(i), "repeat": rep,
             "arm": arm, "firstPassSuccess": score}
            for i, (a, b) in enumerate(zip(before, after, strict=True))
            for rep in range(repeats) for arm, score in (("a", a), ("b", b))]


def test_uplift_percentage_points_relative_and_error_reduction():
    result = paired_effect(rows_for([1] * 6 + [0] * 4, [1] * 8 + [0] * 2), "a", "b")
    assert result["absoluteUpliftPoints"] == pytest.approx(20)
    assert result["relativeImprovementPercent"] == pytest.approx(100 / 3)
    assert result["errorReductionPercent"] == pytest.approx(50)
    assert result["pairedRuns"] == 10 and result["discordantWins"] == 2


def test_zero_and_perfect_baseline_guards():
    zero = paired_effect(rows_for([0, 0], [1, 1]), "a", "b")
    assert zero["relativeImprovementPercent"] is None
    perfect = paired_effect(rows_for([1, 1], [0, 1]), "a", "b")
    assert perfect["errorReductionPercent"] is None
    assert perfect["absoluteUpliftPoints"] == -50
    assert rate(0, 0) is None and wilson(0, 0) is None


def test_repeats_clustered_and_mcnemar_suppressed():
    result = paired_effect(rows_for([0, 1], [1, 1], 3), "a", "b")
    assert result["pairedRuns"] == 6 and result["independentClusters"] == 2
    assert result["mcnemarExactP"] is None
    assert result["absoluteUpliftPoints"] == 50


def test_unpaired_rows_do_not_invent_comparison():
    result = paired_effect([{"caseId": "1", "repeat": 0, "arm": "a", "firstPassSuccess": True}], "a", "b")
    assert result["pairedRuns"] == 0 and result["absoluteUpliftPoints"] is None


def test_custom_score_is_optional_not_fake_model_stability():
    summary = {"semanticPrecisionAmongValidCallsPercent": 100, "firstPassSuccessPercent": 100, "retryRatePercent": 0}
    assert custom_fitness(summary, {"invalidRejectionPercent": 100}) is None
    assert custom_fitness(summary, {"invalidRejectionPercent": 100}, 100) == 100


@pytest.mark.parametrize("k,n", [(0, 10), (5, 10), (10, 10), (480, 480)])
def test_wilson_bounds(k, n):
    low, high = wilson(k, n)
    assert 0 <= low <= k / n * 100 <= high <= 100
