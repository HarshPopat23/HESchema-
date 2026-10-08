"""Serialize explicitly staged source files for a Git data API commit."""

import json
import subprocess
from pathlib import Path


def main():
    paths = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    entries = []
    for path in filter(None, paths):
        if path == ".env" or path.startswith((".venv/", "results/", "data/", "native/node_modules/")):
            raise SystemExit(f"Refusing to export private/generated runtime path: {path}")
        if path.endswith((".sqlite", ".sqlite3", ".pyc")):
            raise SystemExit(f"Refusing to export runtime file: {path}")
        content = Path(path).read_text(encoding="utf-8")
        entries.append({"path": path, "mode": "100644", "type": "blob", "content": content})
    print(json.dumps(entries, ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
