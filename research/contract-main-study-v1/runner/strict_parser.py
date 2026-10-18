"""Strict output parsing engine for experiment responses.

Rules:
- Exactly one complete JSON object.
- No Markdown fences or surrounding prose.
- No repeated object keys.
- No NaN or Infinity.
- Object-key order ignored.
- Array order preserved.
- Booleans distinct from numbers.
- Numerically equivalent JSON numbers allowed.
"""

import json
import re


class StrictParseError(ValueError):
    def __init__(self, message, code="formatting_or_json_parse"):
        super().__init__(message)
        self.code = code


def _check_duplicate_keys(pairs):
    res = {}
    for k, v in pairs:
        if k in res:
            raise StrictParseError(f"Duplicate object key encountered: {k!r}")
        res[k] = v
    return res


def parse_strict_json(raw_text: str):
    """Parses raw text strictly according to protocol rules."""
    if not isinstance(raw_text, str):
        raise StrictParseError("Output is not a string", code="formatting_or_json_parse")

    stripped = raw_text.strip()
    if not stripped:
        raise StrictParseError("Empty response", code="formatting_or_json_parse")

    # Reject Markdown fences
    if "```" in raw_text or "`" in stripped:
        raise StrictParseError("Response contains Markdown fences or backticks", code="formatting_or_json_parse")

    # Reject leading or trailing prose outside the root JSON object
    if not (stripped.startswith("{") and stripped.endswith("}")):
        raise StrictParseError("Response is not bounded by a single JSON object", code="formatting_or_json_parse")

    # Parse with custom object_pairs_hook to reject duplicate keys and reject NaN/Infinity
    try:
        parsed = json.loads(
            stripped,
            object_pairs_hook=_check_duplicate_keys,
            parse_constant=lambda c: (_ for _ in ()).throw(StrictParseError(f"Invalid constant: {c}")),
        )
    except json.JSONDecodeError as exc:
        raise StrictParseError(f"JSON syntax error: {exc.msg} at line {exc.lineno} col {exc.colno}", code="formatting_or_json_parse")
    except StrictParseError:
        raise
    except Exception as exc:
        raise StrictParseError(f"JSON parsing error: {exc}", code="formatting_or_json_parse")

    if not isinstance(parsed, dict):
        raise StrictParseError("Root element is not a JSON object", code="formatting_or_json_parse")

    return parsed


def json_semantic_equal(actual, expected) -> bool:
    """Strict JSON value equality:
    - Booleans distinct from numbers (True != 1, False != 0).
    - Float/int numeric equivalence allowed (10.0 == 10).
    - Arrays preserve exact order.
    - Objects ignore key order.
    - None (null) distinct from missing keys.
    """
    if type(actual) is bool or type(expected) is bool:
        return type(actual) is type(expected) and actual == expected

    if type(actual) in (int, float) and type(expected) in (int, float):
        return actual == expected

    if type(actual) is not type(expected):
        return False

    if isinstance(actual, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(json_semantic_equal(actual[k], expected[k]) for k in actual)

    if isinstance(actual, list):
        if len(actual) != len(expected):
            return False
        return all(json_semantic_equal(a, b) for a, b in zip(actual, expected))

    return actual == expected
