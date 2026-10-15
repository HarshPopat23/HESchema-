"""Descriptive, separate-model category tables from saved controlled reports."""

from .jsonio import read_json


def category_report(paths):
    reports = [read_json(path) for path in paths]
    if not reports:
        raise ValueError('Provide at least one controlled report')
    configs = [r['config'] for r in reports]
    if any(r.get('study') != 'controlled_decoding' or not r.get('byFamily') for r in reports):
        raise ValueError('Category reporting requires current controlled-decoding family reports')
    for key in ('datasetHash', 'maxTokens', 'temperature', 'engine', 'failureCategoryVersion', 'scoringVersion'):
        if key not in configs[0] or any(c.get(key) != configs[0][key] for c in configs):
            raise ValueError(f'Category reports differ in {key}')
    for key in ('codeHash', 'dependencies'):
        if any(c['provenance'].get(key) != configs[0]['provenance'].get(key) for c in configs):
            raise ValueError(f'Category evaluator provenance differs in {key}')
    rows = []
    for path, report in zip(paths, reports):
        grouped = report.get('byCategory') or report['byFamily']
        group_kind = 'category' if report.get('byCategory') else 'family'
        for group, arms in grouped.items():
            for mode, arm in arms.items():
                rows.append({'sourceReport': str(path), 'provider': report['config']['provider'],
                             'requestedModel': report['config']['requestedModel'], 'observedModels': report['observedModels'],
                             'groupKind': group_kind, 'group': group, 'mode': mode, 'trials': arm['runs'],
                             'taskCorrect': arm['firstPassSuccess'], 'stages': arm['stages'],
                             'schemaValidRelationshipRejected': arm['schemaValidRelationshipRejected'],
                             'observedFailureCategories': arm['firstFailureCategories'],
                             'relationshipChecks': arm['firstRelationshipChecks'],
                             'empiricalLLMEvidence': report['empiricalLLMEvidence'],
                             'comparisonValid': report['comparisonValid'], 'complete': report['complete']})
    return {'reportType': 'descriptive_category_comparison', 'version': '1', 'rows': rows,
            'datasetHash': configs[0]['datasetHash'], 'pooledAccuracy': None,
            'notice': 'Models remain separate. Repeated/synthetic cases are not independent real workflows. Inspect completeness, controls and review status before making cross-model or vocabulary claims.'}
