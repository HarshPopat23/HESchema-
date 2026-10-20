"""Shared engine for the acceptance controls; native CI opts into the same cases."""

import os

import pytest

from heschema.schema import SchemaEngine


@pytest.fixture(scope='module')
def validation_engine():
    engine = SchemaEngine('blaze' if os.getenv('HESCHEMA_TEST_BLAZE') else 'jsonschema')
    yield engine
    engine.close()
