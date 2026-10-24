"""Known controls for the offline latency report; no provider requests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import analyze_segmented_latency as report  # noqa: E402
import continue_latency_study as continuation  # noqa: E402


def test_nearest_rank_p95_and_median():
    result = report.describe(list(range(1, 21)))
    assert result == {'n': 20, 'median': 10.5, 'p95': 19, 'mean': 10.5}


def test_schedule_identity_distinguishes_arms_and_repeats():
    row = dict(caseId='case', model='model', repeat=0, arm='A')
    assert continuation.identity(row) != continuation.identity(dict(row, arm='B'))
    assert continuation.identity(row) != continuation.identity(dict(row, repeat=1))
    assert report.group(row) == report.group(dict(row, arm='B'))


def test_metrics_count_wrong_acceptance_without_discarding_failed_answers():
    rows = [dict(firstCorrect=False, finalCorrect=False, accepted=True, totalTokens=100,
                 timing=dict.fromkeys(report.METRICS, 10)),
            dict(firstCorrect=True, finalCorrect=True, accepted=True, totalTokens=50,
                 timing=dict.fromkeys(report.METRICS, 20))]
    result = report.metrics(rows)
    assert result['n'] == 2
    assert result['firstCorrect'] == result['finalCorrect'] == result['wrongAccepted'] == 1
    assert result['totalTokens'] == 150
    assert result['serviceTotalMs']['median'] == 15
