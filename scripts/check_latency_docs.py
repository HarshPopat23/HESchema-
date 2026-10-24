"""Check public latency aggregates, local links and the reviewed publication boundary."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((ROOT/'research/latency-20261024/FINISHED_SUMMARY.json').read_text())
    assert data['allCompletedSlots']==2160 and data['remainingSlots']==0
    assert data['primarySlots']==2128 and data['primaryMatchedGroups']==532
    arms = data['primaryByArm']
    assert all(v['n']==532 for v in arms.values())
    reduction = 100*(1-arms['C']['totalTokens']/arms['B']['totalTokens'])
    report = (ROOT/'docs/reports/HESchema_Latency_Report.md').read_text()
    assert f'{reduction:.2f}%' in report
    assert [arms[a]['finalCorrect'] for a in 'ABCD']==[485,481,475,479]
    assert [arms[a]['wrongAccepted'] for a in 'ABCD']==[42,0,0,0]
    for arm in 'ABCD':
        assert f"{arms[arm]['providerRoundTripMs']['median']/1000:.3f}s" in report
    for relative in ('docs/reports/HESchema_Latency_Report.md','docs/latency-measurements.md'):
        path=ROOT/relative
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if not link.startswith(('http:','https:','#','mailto:')):
                assert (path.parent/link.split('#')[0]).resolve().exists(), link
    assert 'raw' in (ROOT/'research/latency-20261024/PUBLICATION_STATUS.md').read_text().lower()
    assert '17.42%' in (ROOT/'README.md').read_text()
    print('LATENCY_PUBLICATION_VERIFIED')


if __name__=='__main__':
    main()
