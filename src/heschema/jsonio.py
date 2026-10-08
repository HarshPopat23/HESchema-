"""Strict JSON: reject non-finite numbers and duplicate keys, never repair silently."""

import hashlib
import json
import math
from pathlib import Path


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def loads(text):
    def invalid(value):
        raise ValueError(f"Non-finite JSON value: {value}")

    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(f"Non-finite JSON number: {value}")
        return parsed

    return json.loads(text, object_pairs_hook=_pairs, parse_constant=invalid, parse_float=finite_float)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    return loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
