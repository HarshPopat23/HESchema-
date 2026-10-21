import json
from collections import defaultdict
from pathlib import Path

p = Path('research/confirmation-60-v1/runs/runs.jsonl')
s = Path('research/confirmation-60-v1/runs/summary.json')

rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
summary = json.loads(s.read_text(encoding='utf-8'))

print(f"Total Completed: {len(rows)} / {summary['totalPlanned']} ({summary['completionPct']}%)")
print(f"Remaining slots: {summary['totalPlanned'] - len(rows)}")

print("\n=== Performance by Arm ===")
for arm, d in summary['byArm'].items():
    print(f"Arm {arm}: {d['finalCorrect']}/{d['slots']} ({d['finalCorrectPct']}%) | False Acceptance: {d['falseAcceptance']} ({d['falseAcceptancePct']}%) | Mean Tokens: {d['meanInputTokens']} in / {d['meanOutputTokens']} out")

by_model = defaultdict(lambda: {'total': 0, 'correct': 0, 'fa': 0})
by_fam = defaultdict(lambda: {'total': 0, 'correct': 0, 'fa': 0})

for r in rows:
    m = r['model'].split('/')[-1]
    by_model[m]['total'] += 1
    if r['finalCorrect']:
        by_model[m]['correct'] += 1
    if r['falseAcceptance']:
        by_model[m]['fa'] += 1
    
    f = r['family']
    by_fam[f]['total'] += 1
    if r['finalCorrect']:
        by_fam[f]['correct'] += 1
    if r['falseAcceptance']:
        by_fam[f]['fa'] += 1

print("\n=== Performance by Model ===")
for m, d in sorted(by_model.items()):
    acc = d['correct'] / d['total'] * 100
    fa = d['fa'] / d['total'] * 100
    print(f"{m:18} | Accuracy: {d['correct']:3d}/{d['total']:3d} ({acc:5.1f}%) | False Acceptance: {d['fa']:2d} ({fa:4.1f}%)")

print("\n=== Performance by Relationship Family ===")
for f, d in sorted(by_fam.items()):
    acc = d['correct'] / d['total'] * 100
    fa = d['fa'] / d['total'] * 100
    print(f"{f:22} | Accuracy: {d['correct']:3d}/{d['total']:3d} ({acc:5.1f}%) | False Acceptance: {d['fa']:2d} ({fa:4.1f}%)")
