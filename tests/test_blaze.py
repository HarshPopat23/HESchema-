import os

import pytest

from heschema.dataset import values
from heschema.domains import DOMAINS, reference_schema
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
