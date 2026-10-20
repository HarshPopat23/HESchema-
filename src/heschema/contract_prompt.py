"""Contract prompt presentation; runtime validation remains independent of it."""

from .context_schema import trusted_information
from .jsonio import canonical


def contract_messages(contract, snapshot, evidence, output_schema, prompt, *, style='full'):
    if style not in {'full', 'compact'}:
        raise ValueError('Unknown contract prompt style')
    content = (
        'Return only whole JSON. Never execute tools. Use clarification for missing '
        'information and preserve refusals. Authoritative output schema: '
        + canonical(output_schema)
        + '\nDeclared application relationships: ' + canonical(contract.relationships)
    )
    if style == 'full':
        content += '\nApproved bindings: ' + canonical(evidence['activeBindings'])
    else:
        # Describe how facts constrain fields, without repeating their values.
        bindings = [{key: value for key, value in binding.items() if key != 'value'}
                    for binding in evidence['activeBindings']]
        content += (
            '\nBindings map instanceLocation (document/tool arguments) to '
            'Trusted facts[contextLocation]; keyword defaults to const.'
            '\nApproved bindings: ' + canonical(bindings)
        )
        if evidence['missingBindings']:
            content += ('\nMissing required bindings (do not invent): '
                        + canonical(evidence['missingBindings']))
    content += '\nTrusted facts: ' + canonical(trusted_information(snapshot))
    return [{'role': 'system', 'content': content}, {'role': 'user', 'content': prompt}]
