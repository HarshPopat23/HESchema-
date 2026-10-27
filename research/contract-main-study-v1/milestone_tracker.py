"""Continuous milestone tracker for HESchema Main Study.
Auto-computes and logs cumulative statistical results every 50 counts.
"""

import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent
ATTEMPTS_FILE = ROOT / "runs" / "run-main-ab" / "attempts.jsonl"
MILESTONES_DIR = ROOT / "milestones"
MILESTONES_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_MD = MILESTONES_DIR / "milestones_summary.md"

reported_milestones = set()

def analyze_milestone(attempts, count):
    res = {"count": count, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "arms": {}}
    for arm in ["A", "B"]:
        atts = [a for a in attempts if a["arm"] == arm]
        n = len(atts)
        if n == 0:
            continue
        first_c = sum(1 for a in atts if a["first_pass"]["correct"])
        final_c = sum(1 for a in atts if a["final"]["correct"])
        fa = sum(1 for a in atts if a["final"]["accepted"] and not a["final"]["correct"])
        fr = sum(1 for a in atts if not a["first_pass"]["accepted"] and a["first_pass"]["correct"])
        in_tokens = [a["final"]["total_input_tokens"] for a in atts if a["final"]["total_input_tokens"] is not None]
        out_tokens = [a["final"]["total_output_tokens"] for a in atts if a["final"]["total_output_tokens"] is not None]
        mean_tokens = round(sum(in_tokens + out_tokens) / n, 1) if n else 0.0

        res["arms"][arm] = {
            "attempts": n,
            "first_pass_correct": first_c,
            "first_pass_pct": round(first_c / n * 100.0, 1),
            "final_correct": final_c,
            "final_pct": round(final_c / n * 100.0, 1),
            "false_acceptance": fa,
            "false_acceptance_pct": round(fa / n * 100.0, 1),
            "false_rejection": fr,
            "mean_tokens": mean_tokens
        }
    return res

def append_summary(res):
    arm_a = res["arms"].get("A", {})
    arm_b = res["arms"].get("B", {})
    row = (
        f"| **{res['count']}** | {res['timestamp']} | "
        f"{arm_a.get('first_pass_pct', 0)}% ({arm_a.get('first_pass_correct', 0)}/{arm_a.get('attempts', 0)}) | "
        f"{arm_b.get('first_pass_pct', 0)}% ({arm_b.get('first_pass_correct', 0)}/{arm_b.get('attempts', 0)}) | "
        f"{arm_a.get('final_pct', 0)}% | {arm_b.get('final_pct', 0)}% | "
        f"{arm_a.get('false_acceptance', 0)} ({arm_a.get('false_acceptance_pct', 0)}%) | "
        f"{arm_b.get('false_acceptance', 0)} ({arm_b.get('false_acceptance_pct', 0)}%) |\n"
    )
    if not SUMMARY_MD.exists():
        header = (
            "# Cumulative 50-Count Milestones Progress\n\n"
            "| Milestone | Timestamp | Arm A First-Pass | Arm B First-Pass | Arm A Final | Arm B Final | Arm A False Accept | Arm B False Accept |\n"
            "|---|---|---|---|---|---|---|---|\n"
        )
        SUMMARY_MD.write_text(header + row, encoding="utf-8")
    else:
        with open(SUMMARY_MD, "a", encoding="utf-8") as f:
            f.write(row)

def main():
    print("Milestone tracker initialized. Monitoring attempts.jsonl every 5s...")
    while True:
        if ATTEMPTS_FILE.exists():
            attempts = [json.loads(line) for line in open(ATTEMPTS_FILE, encoding="utf-8") if line.strip()]
            total = len(attempts)
            for milestone in range(450, total + 1, 50):
                if milestone not in reported_milestones and milestone <= total:
                    reported_milestones.add(milestone)
                    sub_attempts = attempts[:milestone]
                    m_res = analyze_milestone(sub_attempts, milestone)
                    m_file = MILESTONES_DIR / f"milestone_{milestone}.json"
                    m_file.write_text(json.dumps(m_res, indent=2), encoding="utf-8")
                    append_summary(m_res)
                    alt_dir = pathlib.Path(r"d:\20+pro\JHSchema\HESchema-\research\contract-main-study-v1\milestones")
                    if alt_dir.exists() and alt_dir != MILESTONES_DIR:
                        try:
                            (alt_dir / f"milestone_{milestone}.json").write_text(json.dumps(m_res, indent=2), encoding="utf-8")
                            (alt_dir / "milestones_summary.md").write_text(SUMMARY_MD.read_text(encoding="utf-8"), encoding="utf-8")
                        except Exception:
                            pass
                    print(f"[Milestone {milestone}] A: {m_res['arms'].get('A',{}).get('final_pct')}% (FA: {m_res['arms'].get('A',{}).get('false_acceptance')}) | B: {m_res['arms'].get('B',{}).get('final_pct')}% (FA: {m_res['arms'].get('B',{}).get('false_acceptance')})")
        time.sleep(5)

if __name__ == "__main__":
    main()
