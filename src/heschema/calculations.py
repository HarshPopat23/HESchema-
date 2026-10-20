"""Opt-in deterministic calculations over validated model inputs, never arbitrary code."""

import copy
from time import perf_counter

from .context_schema import effective_schema
from .diagnostics import diagnostic, parts
from .jsonio import canonical, loads
from .repair_feedback import source_error
from .rules import calculation_value
from .schema import schema_children


def _overlap(left, right):
    a, b = parts(left), parts(right)
    return a[:len(b)] == b or b[:len(a)] == a


def calculation_plan(contract):
    """Reject ambiguous schema rewrites and dependencies instead of guessing semantics."""
    selected = [r for r in contract.relationships if r.get('compute') == 'application']
    if not selected:
        return []
    schema = contract.schema
    allowed = {'$schema', '$id', 'type', 'properties', 'required', 'additionalProperties',
               'title', 'description', '$comment', 'examples', 'default'}
    if (not isinstance(schema, dict) or schema.get('type') != 'object'
            or schema.get('additionalProperties') is not False or set(schema) - allowed):
        raise ValueError('Application calculations require a plain closed object schema')

    def check_references(node):
        if isinstance(node, dict):
            if {'$ref', '$dynamicRef'} & set(node):
                raise ValueError('Application calculations do not rewrite schemas with references')
            for _, child in schema_children(node):
                check_references(child)
    check_references(schema)
    targets = [rule['target'] for rule in selected]
    if len(set(targets)) != len(targets):
        raise ValueError('Application calculations require distinct targets')
    for rule in selected:
        tokens = parts(rule['target'])
        field = schema.get('properties', {}).get(tokens[0]) if len(tokens) == 1 else None
        if not isinstance(field, dict) or field.get('type') != 'integer':
            raise ValueError('Application calculation targets must be top-level integer properties')
        if any(_overlap(rule['target'], b['instanceLocation']) for b in contract.bindings):
            raise ValueError('Application calculation targets cannot overlap context bindings')
        inputs = rule.get('operands', [rule.get('arrayLocation')])
        if any(_overlap(source, target) for source in inputs for target in targets):
            raise ValueError('Dependent or self-referential application calculations are unsupported')
    return copy.deepcopy(selected)


def calculation_input_schema(schema, plan):
    """Remove only explicitly opted-in output fields, retaining all input constraints."""
    result = copy.deepcopy(schema)
    if plan:
        fields = {parts(rule['target'])[0] for rule in plan}
        result['properties'] = {key: value for key, value in result['properties'].items()
                                if key not in fields}
        if 'required' in result:
            result['required'] = [key for key in result['required'] if key not in fields]
    return result


def validate_with_calculations(raw, engine, contract, snapshot=None, *, generation=None):
    """Preserve raw output; assemble only after input/source checks, then fully validate."""
    from .contracts import generation_envelope
    from .validation import validate_contract

    plan = calculation_plan(contract)
    if not plan:
        return validate_contract(raw, engine, contract, snapshot, generation=generation)
    started = perf_counter()
    calculation_ms = 0.0
    evidence = {'status': 'not_applied', 'ruleIds': [rule['id'] for rule in plan],
                'values': [], 'inputSchemaValid': None, 'sourceValid': None,
                'correctnessScope': 'assembled_system_output'}

    def finish(result, status, values=None):
        return {**result, 'calculation': {**evidence, 'status': status, 'values': values or [],
                                        'computeMs': calculation_ms,
                                        'pipelineMs': (perf_counter() - started) * 1000}}

    def blocked(errors=None):
        result = validate_contract(raw, engine, contract, snapshot, generation=generation)
        if errors:
            result.update(accepted=False, success=False, result='NEEDS_CONTEXT' if any(
                e.get('repair') == 'needs_context' for e in errors) else 'FAIL', errors=errors)
            if result['semanticValid'] is not None:
                result['semanticValid'] = False
        return finish(result, 'blocked')

    if raw is None or raw == '' or (generation and generation.completion in {'empty', 'truncated'}):
        return blocked()
    try:
        parsed = loads(raw) if isinstance(raw, str) else loads(canonical(raw))
    except (ValueError, TypeError):
        return blocked()
    if (contract.outputKind == 'tool_envelope' and isinstance(parsed, dict)
            and parsed.get('action') in {'refuse', 'ask_clarification'}):
        result = validate_contract(raw, engine, contract, snapshot, generation=generation)
        return finish(result, 'not_applied')
    original = calculation_input_schema(contract.schema, plan)
    errors = engine.errors(generation_envelope(contract, original), parsed)
    evidence['inputSchemaValid'] = not errors
    if errors:
        return blocked(errors)
    document = parsed['arguments'] if contract.outputKind == 'tool_envelope' else parsed
    effective, context = effective_schema(contract, snapshot)
    errors = [source_error(e, document, context['activeBindings'])
              for e in engine.errors(calculation_input_schema(effective, plan), document)]
    errors.extend(diagnostic('CONTEXT_REQUIRED', 'context', pointer,
                             'Confirm the declared input before calculation', repair='needs_context')
                  for pointer in context['missingBindings'])
    evidence['sourceValid'] = False if errors else True if context['activeBindings'] else None
    if errors:
        return blocked(errors)
    values = []
    def compute(rule):
        nonlocal calculation_ms
        started = perf_counter()
        try:
            return calculation_value(document, rule)
        finally:
            calculation_ms += (perf_counter() - started) * 1000
    for rule in plan:
        try:
            value = compute(rule)
        except (KeyError, TypeError, ValueError) as exc:
            return blocked([diagnostic('CALCULATION_INPUT_INVALID', 'calculation', rule['target'],
                                       'Calculation input missing or invalid: ' + str(exc),
                                       ruleId=rule['id'], kind=rule['kind'],
                                       inputLocations=rule.get('operands', [rule.get('arrayLocation')]),
                                       protectedInputs=[b['instanceLocation'] for b in context['activeBindings']])])
        values.append({'ruleId': rule['id'], 'kind': rule['kind'], 'target': rule['target'],
                       'value': value})
    # Atomic assembly: no output field is written until every calculation succeeds.
    assembled = copy.deepcopy(parsed)
    output = assembled['arguments'] if contract.outputKind == 'tool_envelope' else assembled
    for record in values:
        output[parts(record['target'])[0]] = record['value']
    result = validate_contract(assembled, engine, contract, snapshot, generation=generation)
    return finish(result, 'applied', values)
