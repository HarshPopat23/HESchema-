import os

import pytest

from heschema.calculations import validate_with_calculations
from heschema.contracts import Contract
from heschema.dataset import values
from heschema.domains import DOMAINS, reference_schema
from heschema.jsonio import read_json
from heschema.providers import ROOT
from heschema.schema import SchemaEngine

pytestmark = pytest.mark.skipif(not os.getenv("HESCHEMA_TEST_BLAZE"), reason="Opt-in native integration")


@pytest.mark.parametrize('schema,good,bad', [
    ({'type': 'integer'}, 1, 'wrong'),
    ({'type': 'object', 'properties': {'n': {'type': 'integer'}}}, {'n': 1}, {'n': 'wrong'}),
])
def test_contract_default_dialect_is_also_used_by_native_compiler(schema, good, bad):
    engine = SchemaEngine('blaze')
    try:
        assert not engine.errors(schema, good)
        assert engine.errors(schema, bad)
        assert '$schema' not in schema
        assert not engine.errors(True, good)
        assert engine.errors(False, good)
    finally:
        engine.close()


@pytest.mark.parametrize("domain", list(DOMAINS))
def test_native_template_parity_and_format_guard(domain):
    engine = SchemaEngine("blaze", capacity=2)
    try:
        schema = reference_schema(domain)
        assert not engine.errors(schema, values(domain, 0))
        assert engine.errors(schema, {})
        args = values(domain, 0)
        for field, rule in schema["properties"].items():
            if rule.get("format") == "date":
                args[field] = "2027-02-30"
                assert engine.errors(schema, args)
                break
    finally:
        engine.close()


def test_application_calculations_check_inputs_and_full_output_with_native_backend():
    example = read_json(ROOT / 'examples/contracts/application-calculations.json')
    contract = Contract(**example['contract'])
    context = {'id': 'example', 'version': 1, 'confirmed': True, 'facts': [], **example['context']}
    engine = SchemaEngine('blaze')
    try:
        result = validate_with_calculations(example['modelOutput'], engine, contract, context)
        assert result['success'] and result['parsed'] == example['expectedOutput']
        assert 'blaze_boolean_crosscheck_ipc' in result['validationComponents']
        bad = validate_with_calculations({'items': []}, engine, contract, context)
        assert not bad['accepted'] and bad['calculation']['status'] == 'blocked'
    finally:
        engine.close()
