"""Pure checks: schema conformance, compiled state bindings and declared policies."""

import time
from dataclasses import dataclass

from .jsonio import canonical, loads

ENVELOPE = {
    "type": "object", "required": ["action", "tool", "arguments", "missingFields", "reason"],
    "additionalProperties": False,
    "properties": {
        "action": {"enum": ["call_tool", "ask_clarification", "refuse"]},
        "tool": {"type": ["string", "null"]}, "arguments": {"type": "object"},
        "missingFields": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
        "reason": {"type": "string"},
    },
}


def envelope(action, tool=None, arguments=None, missing=None, reason=""):
    return {"action": action, "tool": tool, "arguments": arguments or {},
            "missingFields": missing or [], "reason": reason}


@dataclass(frozen=True)
class CompiledState:
    bindings: tuple

    @classmethod
    def compile(cls, state):
        # Canonical equality avoids Python True == 1 and snapshots mutable inputs.
        return cls(tuple((key, canonical(value)) for key, value in state.items()))

    def errors(self, arguments):
        errors = []
        for key, expected in self.bindings:
            if key not in arguments or canonical(arguments[key]) != expected:
                errors.append({"code": "STATE_MISMATCH", "field": key,
                               "expected": loads(expected), "actual": arguments.get(key)})
        return errors


def policy_errors(arguments, policy):
    errors = []
    for field, maximum in policy.get("max", {}).items():
        value = arguments.get(field)
        if type(value) not in {int, float} or value > maximum:
            errors.append({"code": "POLICY_LIMIT", "field": field, "maximum": maximum})
    for first, second in policy.get("ordered", []):
        a, b = arguments.get(first), arguments.get(second)
        if not isinstance(a, str) or not isinstance(b, str) or a >= b:
            errors.append({"code": "POLICY_ORDER", "fields": [first, second]})
    return errors


def evaluate(raw, engine, reference_schema, candidate_schema, expected, state=None, policy=None):
    """Ground truth is passed only to this evaluator, never a model/provider."""
    started = time.perf_counter_ns()
    errors, parsed, json_valid = [], None, False
    try:
        parsed = loads(raw) if isinstance(raw, str) else loads(canonical(raw))
        json_valid = True
    except (ValueError, TypeError) as exc:
        errors.append({"code": "JSON_INVALID", "message": str(exc)})
    envelope_errors = engine.errors(ENVELOPE, parsed) if json_valid else []
    errors.extend(envelope_errors)
    action_correct = bool(json_valid and not envelope_errors and parsed["action"] == expected["action"])
    candidate_valid = reference_valid = semantic_valid = policy_valid = False
    if json_valid and not envelope_errors:
        args = parsed["arguments"]
        if parsed["action"] == "call_tool":
            candidate_errors = engine.errors(candidate_schema, args)
            reference_errors = engine.errors(reference_schema, args)
            candidate_valid, reference_valid = not candidate_errors, not reference_errors
            errors.extend(reference_errors)
            if candidate_errors:
                errors.append({"code": "CANDIDATE_SCHEMA_INVALID", "details": candidate_errors})
            bindings = state if state is not None else expected.get("arguments", {})
            mismatch = CompiledState.compile(bindings).errors(args)
            # Exact benchmark oracle also rejects extra fields. Runtime reference
            # schema controls extras; expected arguments supply its semantic oracle.
            if expected.get("arguments") is not None and canonical(args) != canonical(expected["arguments"]):
                mismatch.append({"code": "GROUND_TRUTH_MISMATCH"})
            if parsed["tool"] != expected.get("tool"):
                mismatch.append({"code": "WRONG_TOOL"})
            if parsed["missingFields"]:
                mismatch.append({"code": "UNEXPECTED_MISSING_FIELDS"})
            errors.extend(mismatch)
            semantic_valid = action_correct and not mismatch
            p_errors = policy_errors(args, policy or {})
            errors.extend(p_errors)
            policy_valid = not p_errors
        else:
            control_ok = parsed["tool"] is None and args == {}
            if parsed["action"] == "ask_clarification":
                control_ok &= set(parsed["missingFields"]) == set(expected.get("missingFields", []))
            else:
                control_ok &= parsed["missingFields"] == []
            semantic_valid = action_correct and control_ok
            reference_valid = candidate_valid = control_ok
            policy_valid = control_ok
        if not action_correct:
            errors.append({"code": "WRONG_ACTION", "expected": expected["action"], "actual": parsed["action"]})
    success = bool(reference_valid and semantic_valid and policy_valid)
    return {"result": "PASS" if success else "FAIL", "jsonValid": json_valid,
            "actionCorrect": action_correct, "candidateSchemaValid": candidate_valid,
            "referenceSchemaValid": reference_valid, "semanticValid": semantic_valid,
            "policyValid": policy_valid, "success": success,
            "executionAuthorized": False, "errors": errors,
            "validationMs": (time.perf_counter_ns() - started) / 1e6,
            "parsed": parsed}
