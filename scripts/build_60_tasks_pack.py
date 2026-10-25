"""Extract and build the 60-task prospective confirmation dataset pack from markdown."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "docs" / "reports" / "HESchema_60_Real_Record_Tasks.md"
SOURCE_SHA256 = "060e80615cf0d739208eba646d82a9f69a5fa77a5d527414b02aa60dc58c6957"
FROZEN_CASES_SHA256 = "545846f456d88072d3059b793f5b15f4a40aeb9cc6db87985a4028c1bfb49c1c"
TARGET_DIR = ROOT / "research" / "confirmation-60-v1"


def parse_60_tasks(source=None):
    source = Path(source) if source is not None else MD_PATH
    raw = source.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != SOURCE_SHA256:
        raise ValueError(f"Pinned H60 source hash changed: expected {SOURCE_SHA256}, got {actual}. "
                         "Review source changes and version the dataset explicitly; do not overwrite historical evidence.")
    content = raw.decode("utf-8").replace("\r\n", "\n")
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


def validate_tasks(tasks):
    expected_ids = [f"H60-{i:02}" for i in range(1, 61)]
    if [t["id"] for t in tasks] != expected_ids:
        raise ValueError("Expected exactly 60 unique ordered H60 task IDs")
    for task in tasks:
        for key in ("contract", "expected", "prompt", "project", "family"):
            if not task.get(key):
                raise ValueError(f"Missing {key}: {task['id']}")
        if not task["snapshot"]["data"]:
            raise ValueError(f"Missing facts: {task['id']}")


def rebuild(output_dir=TARGET_DIR, check=False):
    tasks = parse_60_tasks()
    validate_tasks(tasks)
    raw = (json.dumps(tasks, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    rebuilt_hash = hashlib.sha256(raw).hexdigest()
    if rebuilt_hash != FROZEN_CASES_SHA256:
        raise ValueError("Parser output differs from pinned H60 cases; review semantic and serialization changes")
    out_file = Path(output_dir) / "cases.json"
    previous = out_file.read_bytes() if out_file.exists() else None
    report = {
        "source": str(MD_PATH.relative_to(ROOT)), "sourceSha256": SOURCE_SHA256,
        "caseCount": len(tasks), "rebuiltSha256": rebuilt_hash,
        "existingSha256": hashlib.sha256(previous).hexdigest() if previous is not None else None,
        "byteIdentical": previous == raw,
        "semanticEqual": json.loads(previous) == tasks if previous is not None else None,
    }
    if check:
        print(json.dumps(report, indent=2))
        if not report["byteIdentical"]:
            raise ValueError("H60 byte hash differs; semanticEqual distinguishes formatting from content changes. "
                             "Check mode does not rewrite historical files.")
    else:
        if previous is not None and previous != raw:
            raise ValueError("Refusing to replace different existing cases; use --check or a new --output-dir")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(raw)
        print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=TARGET_DIR)
    parser.add_argument("--check", action="store_true", help="Compare existing cases without writing")
    args = parser.parse_args()
    rebuild(args.output_dir, args.check)


if __name__ == "__main__":
    main()
