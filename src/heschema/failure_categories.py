"""Versioned observation labels. A violation never proves a keyword unsupported."""

from collections import Counter

from .providers import content_has_reasoning_markers

VERSION = '1'
RELATIONSHIP_CATEGORIES = {
    'product_equals': 'arithmetic_product', 'sum_equals': 'arithmetic_sum',
    'sum_items_equals': 'collection_sum', 'count_equals': 'collection_count',
    'date_before': 'date_order', 'equals': 'field_equality',
    'reference_member': 'trusted_membership', 'member_of': 'document_membership',
    'unique_by': 'record_key_uniqueness',
}


def classify(evaluation, *, generation=None, failure=None):
    """Categories overlap; return observations, not a diagnosis of model capability."""
    tags = set()
    generation = generation or {}
    text = generation.get('text', '')
    if content_has_reasoning_markers(text):
        tags.add('reasoning_in_content')
    metadata = generation.get('metadata', {})
    controls = metadata.get('requestControls', {})
    if controls.get('thinkingRequested') is False and (generation.get('reasoning') or 'reasoning_in_content' in tags):
        tags.add('thinking_control_mismatch')
    keywords = set()
    def errors(entries, context_error=False):
        for error in entries:
            code = error.get('code')
            if code == 'JSON_INVALID':
                tags.add('numeric_range' if any(message in error.get('message', '') for message in ('Non-finite JSON number', 'Underflow JSON number')) else 'json_syntax')
            elif code == 'SCHEMA_INVALID':
                tags.add('trusted_context_mismatch' if context_error else 'original_schema_violation')
                if error.get('keyword'):
                    keywords.add(error['keyword'])
            elif code == 'CONTEXT_MISMATCH':
                tags.add('trusted_context_mismatch')
            elif code in {'CONTEXT_REQUIRED', 'RELATION_INPUT_MISSING'}:
                tags.add('missing_evidence')
            elif code in {'RELATION_MISMATCH', 'RELATION_TYPE_INVALID'}:
                tags.add('relationship_violation')
                tags.add(RELATIONSHIP_CATEGORIES.get(error.get('kind'), 'relationship_other'))
            elif code == 'OUTPUT_TRUNCATED':
                tags.add('output_truncated')
            errors(error.get('details', []), context_error or code == 'CONTEXT_MISMATCH')
    errors(evaluation.get('errors', []))
    completion = (evaluation.get('generation') or {}).get('completion')
    if completion == 'empty':
        tags.add('output_empty')
    if evaluation.get('accepted') and evaluation.get('intentAgreement') is False:
        tags.add('runtime_accepted_oracle_mismatch')
    if failure:
        code = failure.get('code')
        tags.add('adapter_unsupported' if code == 'unsupported_mode' else 'provider_request_rejected' if code == 'request_rejected' else 'provider_failure')
    return {'version': VERSION, 'categories': sorted(tags), 'schemaKeywords': sorted(keywords),
            'unsupportedKeywordInference': False}


def summary(rows, *, final=False):
    categories, keywords = Counter(), Counter()
    for row in rows:
        key = 'finalObservations' if final else 'firstObservations'
        observation = row.get(key, {})
        categories.update(set(observation.get('categories', [])))
        keywords.update(set(observation.get('schemaKeywords', [])))
    n = len(rows)
    def measures(counts):
        return {key: {'numerator': count, 'denominator': n, 'percent': count / n * 100 if n else None}
                for key, count in sorted(counts.items())}
    return {'version': VERSION, 'rows': n, 'categories': measures(categories), 'schemaKeywords': measures(keywords),
            'notice': 'Overlapping observed failure labels; schema violations do not establish unsupported keywords.'}


def relationship_checks(rows, *, final=False):
    counts = {}
    for row in rows:
        evaluation = row.get('finalEvaluation' if final else 'firstEvaluation') or {}
        for rule in evaluation.get('relationships', {}).get('rules', []):
            kind = rule.get('kind', 'unknown_legacy_kind')
            group = counts.setdefault(kind, {'valid': 0, 'invalid': 0, 'needs_context': 0})
            group[rule['status']] += 1
    return {kind: {**group, 'evaluated': group['valid'] + group['invalid'],
                   'invalidAmongEvaluatedPercent': group['invalid'] / (group['valid'] + group['invalid']) * 100 if group['valid'] + group['invalid'] else None}
            for kind, group in sorted(counts.items())}
