import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('latency', ROOT / 'scripts/latency_study.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_disjoint_partition():
    fields = module.partition(100, {'pacingWaitMs': 10, 'retryWaitMs': 20,
                                   'providerRoundTripMs': 40, 'localValidationMs': 4,
                                   'applicationCalculationMs': 1})
    assert fields['otherMs'] == 25
    module.verify_timing({**fields, 'serviceTotalMs': 100, 'queueWaitMs': 50, 'endToEndMs': 150})


def test_overlap_is_rejected():
    with pytest.raises(ValueError):
        module.partition(10, {'providerRoundTripMs': 11})


@pytest.mark.parametrize('bad', [-1, float('nan'), float('inf')])
def test_bad_measurement_rejected(bad):
    values = dict.fromkeys(module.PARTS, 0)
    values.update(serviceTotalMs=0, queueWaitMs=0, endToEndMs=bad)
    with pytest.raises(AssertionError):
        module.verify_timing(values)
