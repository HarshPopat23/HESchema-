"""Model construction cannot manufacture approval for a required binding."""
import pytest
from pydantic import BaseModel

from heschema import ContractViolationError
from heschema.integrations.pydantic import guarded_model


def test_pydantic_required_binding_without_snapshot_rejects_before_post_init():
    calls = []

    @guarded_model(bindings=[{'instanceLocation': '/destination',
                             'contextLocation': '/destination'}])
    class Trip(BaseModel):
        destination: str

        def model_post_init(self, context):
            calls.append(self.destination)

    with pytest.raises(ContractViolationError):
        Trip(destination='Goa')
    assert calls == []
