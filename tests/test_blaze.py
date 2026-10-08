import os

import pytest

from heschema.dataset import values
from heschema.domains import DOMAINS, reference_schema
from heschema.schema import SchemaEngine

pytestmark = pytest.mark.skipif(not os.getenv("HESCHEMA_TEST_BLAZE"), reason="Opt-in native integration")


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
