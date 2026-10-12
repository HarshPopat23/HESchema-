"""Versioned, local contracts. JSON documents and tool envelopes have different shapes."""

import copy
from dataclasses import dataclass, field

from .diagnostics import parts
from .jsonio import digest
from .schema import check_schema
from .validation import ENVELOPE


@dataclass(frozen=True)
class Contract:
    id: str
    version: str
    schema: dict | bool
    outputKind: str = 'document'
    tool: str | None = None
    description: str = ''
    contextSchema: dict | bool = field(default_factory=lambda: {'type': 'object'})
    bindings: list = field(default_factory=list)
    relationships: list = field(default_factory=list)

    def __post_init__(self):
        if not self.id or not self.version or self.outputKind not in {'document', 'tool_envelope'}:
            raise ValueError('Contract requires ID, version, and a supported outputKind')
        if self.outputKind == 'tool_envelope' and not self.tool:
            raise ValueError('A tool envelope requires a tool name')
        check_schema(self.schema)
        check_schema(self.contextSchema)
        for binding in self.bindings:
            if set(binding) - {'instanceLocation', 'contextLocation', 'keyword', 'required'}:
                raise ValueError('Unknown context binding option')
            parts(binding['instanceLocation'])
            parts(binding['contextLocation'])
            if binding.get('keyword', 'const') not in {'const', 'enum', 'minimum', 'maximum'}:
                raise ValueError('Unsupported context projection keyword')
            if not isinstance(binding.get('required', True), bool):
                raise ValueError('Binding required must be boolean')
        from .rules import check_rules
        check_rules(self.relationships)

    @property
    def identity(self):
        return {'id': self.id, 'version': self.version, 'hash': digest(self.as_dict())}

    def as_dict(self):
        from dataclasses import asdict
        return asdict(self)


def generation_envelope(contract, arguments_schema):
    if contract.outputKind == 'document':
        return copy.deepcopy(arguments_schema)
    branches = []
    for action in ('call_tool', 'ask_clarification', 'refuse'):
        branch = copy.deepcopy(ENVELOPE)
        branch['properties']['action'] = {'const': action}
        branch['properties']['tool'] = {'const': contract.tool if action == 'call_tool' else None}
        embedded = copy.deepcopy(arguments_schema)
        def rebase(node):
            if isinstance(node, dict):
                if '$id' in node or '$dynamicRef' in node or '$anchor' in node or '$dynamicAnchor' in node:
                    raise ValueError('Tool envelopes require bundled schemas without resource IDs or anchors')
                if '$ref' in node:
                    if node['$ref'] != '#' and not node['$ref'].startswith('#/'):
                        raise ValueError('Tool envelopes require JSON Pointer references')
                    node['$ref'] = '#/oneOf/0/properties/arguments' + node['$ref'][1:]
                for value in node.values():
                    rebase(value)
            elif isinstance(node, list):
                for value in node:
                    rebase(value)
        if action == 'call_tool':
            rebase(embedded)
        branch['properties']['arguments'] = embedded if action == 'call_tool' else {'const': {}}
        if action != 'ask_clarification':
            branch['properties']['missingFields'] = {'const': []}
        else:
            branch['properties']['missingFields']['minItems'] = 1
        branches.append(branch)
    return {'oneOf': branches}
