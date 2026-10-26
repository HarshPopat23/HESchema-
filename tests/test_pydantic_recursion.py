"""Conversion rejects recursive models before Python exhausts its stack."""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from heschema.integrations.pydantic import _inline_defs, contract_from_model


class Node(BaseModel):
    children: list[Node] = []


class Left(BaseModel):
    right: Right | None = None


class Right(BaseModel):
    left: Left | None = None


Left.model_rebuild()


@pytest.mark.parametrize('model', [Node, Left, Right])
def test_recursive_models_raise_compatibility_error(model):
    with pytest.raises(ValueError, match='Recursive Pydantic model reference.*not supported'):
        contract_from_model(model)


def test_shared_nonrecursive_definition_is_not_a_cycle():
    class Child(BaseModel):
        value: int

    class Parent(BaseModel):
        first: Child
        second: Child

    contract = contract_from_model(Parent)
    assert contract.schema['properties']['first']['properties']['value']['type'] == 'integer'
    assert contract.schema['properties']['second']['properties']['value']['type'] == 'integer'


def test_inlining_does_not_mutate_schema():
    raw = Node.model_json_schema()
    import copy
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError, match='Recursive Pydantic'):
        _inline_defs(raw)
    assert raw == before
