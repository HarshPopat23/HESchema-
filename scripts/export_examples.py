"""Snapshot generated public demo artifacts; never export model keys/state DBs."""

import argparse
import sys
import tempfile
from pathlib import Path

from heschema.api import create_app
from heschema.jsonio import read_json, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", help="An already generated MOCK report.json")
    parser.add_argument("--out", default="examples")
    args = parser.parse_args()
    report = read_json(args.report)
    if report["config"]["provider"] != "mock" or report["empiricalLLMEvidence"]:
        sys.exit("Only explicitly non-empirical mock reports may be exported")
    target = Path(args.out)
    write_json(target / "offline-report.json", report)
    from heschema.benchmark import markdown_report
    (target / "offline-report.md").write_text(markdown_report(report), encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="heschema-openapi-") as folder:
        app = create_app(Path(folder) / "state.sqlite")
        write_json(target / "openapi.json", app.openapi())


if __name__ == "__main__":
    main()
