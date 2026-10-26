"""Independent probes of nested calculation handoff to Pydantic initialization."""
import copy

import pytest
from pydantic import BaseModel, ConfigDict, Field

from heschema import ContractViolationError
from heschema.integrations.pydantic import guarded_model


@pytest.mark.parametrize('escaped', [False, True])
def test_nested_calculation_preserves_parent_and_sibling_fields(escaped):
    key = 'a/b~c' if escaped else 'total'
    target = '/invoice/a~1b~0c' if escaped else '/invoice/total'
    class Invoice(BaseModel):
        total: int = Field(alias=key)
        note: str

    @guarded_model(relationships=[{'id': 'sum', 'kind': 'sum_equals',
                                   'operands': ['/subtotal', '/tax'], 'target': target,
                                   'compute': 'application'}])
    class Order(BaseModel):
        model_config = ConfigDict(extra='forbid')
        subtotal: int
        tax: int
        invoice: Invoice

    original = {'subtotal': 10, 'tax': 2, 'invoice': {key: 0, 'note': 'keep'}}
    before = copy.deepcopy(original)
    model = Order(**original)
    assert model.invoice.total == 12
    assert model.invoice.note == 'keep'
    assert model.model_dump(by_alias=True)['invoice'] == {key: 12, 'note': 'keep'}
    assert original == before


def test_invalid_calculation_never_reaches_model_post_init():
    calls = []
    @guarded_model(relationships=[{'id': 'sum', 'kind': 'sum_equals',
                                   'operands': ['/subtotal', '/tax'], 'target': '/total',
                                   'compute': 'application'}])
    class Invoice(BaseModel):
        model_config = ConfigDict(extra='forbid')
        subtotal: int
        tax: int
        total: int
        def model_post_init(self, context):
            calls.append(True)
    with pytest.raises(ContractViolationError):
        Invoice(subtotal='wrong', tax=2, total=0)
    assert calls == []


@pytest.mark.parametrize('policy', ['refuse', 'typo', None, [], {}])
def test_unsupported_pydantic_policies_raise_clearly(policy):
    with pytest.raises(ValueError, match='on_fail'):
        guarded_model(on_fail=policy)


def test_tool_envelope_models_require_an_explicit_external_workflow():
    with pytest.raises(ValueError, match='document output only'):
        guarded_model(output_kind='tool_envelope')
