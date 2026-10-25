"""File loads follow current bytes; constructed decorators are pinned snapshots."""
import asyncio
import copy
import json
import os

import pytest

from heschema import ContractViolationError, guard
from heschema.guard import load_contract


def definition(value):
    return {'id': 'file-policy', 'version': '1', 'schema': {
        'type': 'object', 'properties': {'value': {'const': value}},
        'required': ['value'], 'additionalProperties': False,
    }}


def test_same_size_same_mtime_edit_is_reloaded(tmp_path):
    path = tmp_path / 'contract.json'
    path.write_text(json.dumps(definition(1)))
    original_stat = path.stat()
    assert load_contract(path).schema['properties']['value']['const'] == 1
    path.write_text(json.dumps(definition(2)))
    os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    assert path.stat().st_size == original_stat.st_size
    assert guard.validate({'value': 2}, path)['accepted']
    assert not guard.validate({'value': 1}, path)['accepted']


def test_atomic_replacement_and_returned_mutation(tmp_path):
    path = tmp_path / 'contract.json'
    path.write_text(json.dumps(definition(1)))
    loaded = load_contract(path)
    loaded.schema['properties']['value']['const'] = 9
    assert load_contract(path).schema['properties']['value']['const'] == 1
    replacement = tmp_path / 'replacement.json'
    replacement.write_text(json.dumps(definition(2)))
    replacement.replace(path)
    assert load_contract(path).schema['properties']['value']['const'] == 2


@pytest.mark.parametrize('bad', ['{', json.dumps({'id': 'invalid'}),
                                  json.dumps({**definition(2), 'schema': {'type': 'invalid'}})])
def test_invalid_edits_never_fall_back_to_cached_contract(tmp_path, bad):
    path = tmp_path / 'contract.json'
    path.write_text(json.dumps(definition(1)))
    load_contract(path)
    path.write_text(bad)
    with pytest.raises((ValueError, TypeError)):
        load_contract(path)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        load_contract(path)
    path.write_text(json.dumps(definition(2)))
    assert load_contract(path).schema['properties']['value']['const'] == 2


@pytest.mark.parametrize('is_async', [False, True])
def test_decorators_pin_contract_until_reconstructed(tmp_path, is_async):
    path = tmp_path / 'contract.json'
    path.write_text(json.dumps(definition(1)))
    if is_async:
        async def function(value):
            return value
    else:
        def function(value):
            return value
    pinned = guard(path)(function)
    before = copy.deepcopy(pinned.contract.as_dict())
    path.write_text(json.dumps(definition(2)))
    fresh = guard(path)(function)
    def invoke(fn, value):
        return asyncio.run(fn(value)) if is_async else fn(value)
    assert invoke(pinned, 1) == 1
    with pytest.raises(ContractViolationError):
        invoke(pinned, 2)
    assert pinned.contract.as_dict() == before
    assert invoke(fresh, 2) == 2
