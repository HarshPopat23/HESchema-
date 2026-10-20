"""Pure checks: schema conformance, compiled state bindings and declared policies."""

import time
from dataclasses import dataclass
from datetime import datetime, timezone

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
    timing_before = engine.timing_snapshot()
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
            bindings = state if state is not None else (expected.get("arguments") or {})
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
            "validationTimingsMs": engine.timing_delta(timing_before),
            "parsed": parsed}


def validate_contract(raw, engine, contract, snapshot=None, *, generation=None):
    """Runtime checks with no scoring oracle. Success covers only declared approved intent."""
    from .context_schema import effective_schema
    from .contracts import generation_envelope
    from .diagnostics import diagnostic, json_parse_diagnostic
    from .rules import evaluate_rules
    started = time.perf_counter_ns()
    timing_before = engine.timing_snapshot()
    effective, context = effective_schema(contract, snapshot)
    stages = dict.fromkeys(('json', 'originalSchema', 'effectiveSchema', 'context', 'relationships'), 'not_evaluated')
    errors, parsed, action = [], None, None
    output_present = raw is not None and raw != ''
    if output_present:
        try:
            parsed = loads(raw) if isinstance(raw, str) else loads(canonical(raw))
            stages['json'] = 'valid'
        except (ValueError, TypeError) as exc:
            stages['json'] = 'invalid'
            errors.append(json_parse_diagnostic(exc))
    original_valid = effective_valid = None
    relationships = {'status': 'not_evaluated', 'rules': [], 'errors': [], 'implementation': 'application_rules'}
    if stages['json'] == 'valid':
        shape_errors = engine.errors(generation_envelope(contract, contract.schema), parsed)
        original_valid = not shape_errors
        stages['originalSchema'] = 'valid' if original_valid else 'invalid'
        errors.extend(shape_errors)
        doc = parsed
        if contract.outputKind == 'tool_envelope' and isinstance(parsed, dict):
            action = parsed.get('action')
            doc = parsed.get('arguments')
        if original_valid and action in {'refuse', 'ask_clarification'}:
            stages['context'] = 'not_evaluated'
        elif original_valid:
            effective_errors = engine.errors(effective, doc)
            effective_valid = not effective_errors
            stages['effectiveSchema'] = 'valid' if effective_valid else 'invalid'
            for e in effective_errors:
                errors.append({**e, 'code': 'CONTEXT_MISMATCH', 'stage': 'context'})
            stages['context'] = 'invalid' if effective_errors else 'needs_context' if context['missingBindings'] else 'valid' if context['activeBindings'] else 'not_evaluated'
            # Source constraints precede relations. Arithmetic cannot validate wrong source inputs.
            if effective_valid and not context['missingBindings']:
                trusted = snapshot['data'] if snapshot else None
                trusted_locations = set(snapshot.get('approvedPointers', [])) | {f['contextLocation'] for f in snapshot.get('facts', [])} if snapshot else set()
                relationships = evaluate_rules(doc, contract.relationships, trusted, trusted_locations)
                for error in relationships['errors']:
                    error['protectedInputs'] = [binding['instanceLocation'] for binding in context['activeBindings']]
                stages['relationships'] = relationships['status']
                errors.extend(relationships['errors'])
            for missing in context['missingBindings']:
                errors.append(diagnostic('CONTEXT_REQUIRED', 'context', missing, 'Confirm the declared input before generation or repair', repair='needs_context'))
    completed = generation.completion if generation else None
    acceptable_completion = completed not in {'truncated', 'empty'}
    if completed == 'truncated':
        errors.append(diagnostic('OUTPUT_TRUNCATED', 'generation', message='Output reached its token limit', repair='stop'))
    controls = original_valid and action in {'refuse', 'ask_clarification'}
    accepted = bool(original_valid and acceptable_completion and (controls or
                    (effective_valid and not context['missingBindings'] and relationships['status'] in {'valid', 'not_evaluated'})))
    intent_checked = bool(context['activeBindings']) and not context['missingBindings'] and not controls
    success = accepted and intent_checked
    result = 'FAIL' if output_present and not acceptable_completion else 'REFUSED' if controls and action == 'refuse' else 'NEEDS_CONTEXT' if controls or 'needs_context' in stages.values() else 'PASS' if success else 'NOT_CHECKED' if accepted else 'FAIL' if output_present else 'NOT_EVALUATED'
    return {'protocolVersion': 2, 'evaluatedAt': datetime.now(timezone.utc).isoformat(), 'result': result, 'success': bool(success), 'accepted': accepted,
            'executionAuthorized': False, 'outputPresent': output_present, 'stages': stages,
            'jsonValid': True if stages['json'] == 'valid' else False if stages['json'] == 'invalid' else None,
            'referenceSchemaValid': original_valid, 'effectiveSchemaValid': effective_valid,
            'semanticValid': bool(success) if intent_checked else None,
            'intentScope': 'declared_approved_bindings' if intent_checked else 'not_checked',
            'contract': contract.identity, 'context': context, 'relationships': relationships,
            'generation': generation.diagnostic() if generation else None, 'errors': errors,
            'parsed': parsed, 'validationMs': (time.perf_counter_ns() - started) / 1e6,
            'validationTimingsMs': engine.timing_delta(timing_before),
            'validationComponents': ['python_draft202012', 'python_formats'] + (['blaze_boolean_crosscheck_ipc'] if engine.backend == 'blaze' else [])}


def generation_gate(result, generated):
    """Legacy evaluator adapter: absence and known truncation never become success."""
    result['generation'] = generated.diagnostic()
    if not generated.text or generated.completion == 'truncated':
        result['success'] = False
        result['result'] = 'FAIL' if generated.text else 'NOT_EVALUATED'
        if not generated.text:
            result['stages'] = dict.fromkeys(('json', 'originalSchema', 'context', 'relationships'), 'not_evaluated')
        else:
            result['errors'].append({'code': 'OUTPUT_TRUNCATED', 'stage': 'generation', 'message': 'Token limit reached', 'repair': 'stop'})
    return result
