"""Extract and build the 60-task prospective confirmation dataset pack from markdown."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "HESchema_60_Real_Record_Tasks.md"
TARGET_DIR = ROOT / "research" / "confirmation-60-v1"


def parse_60_tasks():
    content = MD_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    sections = re.split(r"\n### (H60-\d{2})\s+[—\-]\s+", content)
    
    tasks = []
    for i in range(1, len(sections), 2):
        tid = sections[i].strip()
        body = sections[i + 1]
        title_line = body.split("\n")[0].strip()

        # Project and family
        meta_m = re.search(r"Project:\s*\*\*(.*?)\*\*.*?Family:\s*\*\*(.*?)\*\*", body)
        project = meta_m.group(1).strip() if meta_m else ""
        family = meta_m.group(2).strip() if meta_m else ""

        # Prompt
        prompt_m = re.search(r"\*\*Exact task prompt\*\*\s*\n\n(.*?)\n\n\*\*Authentic source", body, re.S)
        prompt = prompt_m.group(1).strip() if prompt_m else ""

        # Trusted facts
        facts_m = re.search(r"\*\*Trusted facts sent to every arm\*\*\s*\n\n```json\n(.*?)\n```", body, re.S)
        facts = json.loads(facts_m.group(1)) if facts_m else None

        # Contract
        contract_m = re.search(r"\*\*FULL/base contract.*?\*\*\s*\n\n```json\n(.*?)\n```", body, re.S)
        contract = json.loads(contract_m.group(1)) if contract_m else None

        # Expected valid answer example
        expected_m = re.search(r"\*\*One computed valid answer.*?\*\*\s*\n\n```json\n(.*?)\n```", body, re.S)
        expected = json.loads(expected_m.group(1)) if expected_m else None

        # D calculation declarations if any
        d_decl_m = re.search(r"\*\*D: selective calculation declarations\*\*\s*.*?\n\n```json\n(.*?)\n```", body, re.S)
        d_calc = json.loads(d_decl_m.group(1)) if d_decl_m else None

        approved = set(['/' + k for k in (facts or {})])
        if contract and 'bindings' in contract:
            for b in contract['bindings']:
                if 'contextLocation' in b:
                    approved.add(b['contextLocation'])

        tasks.append({
            "id": tid,
            "title": title_line,
            "project": project,
            "family": family,
            "prompt": prompt,
            "snapshot": {
                "id": f"{tid}-snapshot",
                "version": 1,
                "confirmed": True,
                "approvedPointers": sorted(approved),
                "data": facts or {},
                "facts": []
            },
            "contract": contract,
            "expected": expected,
            "d_calc": d_calc
        })

    return tasks


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    tasks = parse_60_tasks()
    print(f"Extracted {len(tasks)} tasks.")
    
    missing_c = [t["id"] for t in tasks if not t["contract"]]
    missing_f = [t["id"] for t in tasks if not t["snapshot"]["data"]]
    missing_e = [t["id"] for t in tasks if not t["expected"]]
    missing_p = [t["id"] for t in tasks if not t["prompt"]]
    
    assert not missing_c, f"Missing contract: {missing_c}"
    assert not missing_f, f"Missing facts: {missing_f}"
    assert not missing_e, f"Missing expected: {missing_e}"
    assert not missing_p, f"Missing prompt: {missing_p}"
    
    out_file = TARGET_DIR / "cases.json"
    out_file.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Successfully saved 60 tasks to {out_file} ({out_file.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
