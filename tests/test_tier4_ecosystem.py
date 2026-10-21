import json
import pytest
from pydantic import BaseModel, Field

from heschema import ContractViolationError
from heschema.compat import handle_chat_completion
from heschema.integrations import (
    HESchemaToolInterceptor,
    contract_from_model,
    guard_tool,
    guarded_model,
)


class UserProfile(BaseModel):
    username: str = Field(min_length=3)
    age: int = Field(ge=0)
    role: str = "viewer"


class InvoiceModel(BaseModel):
    subtotal: int
    tax: int
    total: int = 0

    __relationships__ = [
        {
            "id": "invoice_total",
            "kind": "sum_equals",
            "compute": "application",
            "target": "/total",
            "operands": ["/subtotal", "/tax"],
        }
    ]


def test_pydantic_contract_from_model():
    contract = contract_from_model(UserProfile, contract_id="user_profile")
    assert contract.id == "user_profile"
    assert contract.outputKind == "document"
    assert "username" in contract.schema["properties"]
    assert contract.schema["properties"]["username"]["minLength"] == 3


def test_pydantic_guarded_model():
    @guarded_model(contract_id="invoice_guarded", on_fail="repair")
    class GuardedInvoice(InvoiceModel):
        pass

    # Total calculated from 100 + 15 = 115
    inv = GuardedInvoice(subtotal=100, tax=15, total=0)
    assert inv.total == 115

    # Violating model validation (negative tax)
    with pytest.raises(ContractViolationError):
        GuardedInvoice(subtotal=100, tax="not-an-int", total=0)


def test_langchain_tool_interceptor():
    contract_dict = {
        "id": "refund_tool",
        "version": "1.0",
        "outputKind": "document",
        "schema": {
            "type": "object",
            "required": ["order_id", "amount"],
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number", "minimum": 1.0},
            },
        },
    }
    interceptor = HESchemaToolInterceptor({"refund_tool": contract_dict}, on_fail="raise")

    # Valid tool arguments pass through
    args = interceptor.intercept("refund_tool", {"order_id": "ORD-1", "amount": 25.5})
    assert args == {"order_id": "ORD-1", "amount": 25.5}

    # Invalid tool arguments raise ContractViolationError
    with pytest.raises(ContractViolationError):
        interceptor.intercept("refund_tool", {"order_id": "ORD-1", "amount": -10.0})


def test_langchain_guard_tool():
    contract_dict = {
        "id": "simple_tool",
        "version": "1.0",
        "outputKind": "document",
        "schema": {
            "type": "object",
            "required": ["x"],
            "properties": {"x": {"type": "integer", "minimum": 10}},
        },
    }

    class MockTool:
        name = "simple_tool"

        def invoke(self, tool_input):
            return f"Processed {tool_input['x']}"

    tool = MockTool()
    guarded = guard_tool(tool, contract_dict, on_fail="raise")

    assert guarded.invoke({"x": 15}) == "Processed 15"

    with pytest.raises(ContractViolationError):
        guarded.invoke({"x": 5})  # violates minimum 10


def test_langgraph_message_interception():
    calc_contract = {
        "id": "calc_tool",
        "version": "1.0",
        "outputKind": "document",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["a", "b", "c"],
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
                "c": {"type": "integer"},
            },
        },
        "relationships": [
            {
                "id": "c_sum",
                "kind": "sum_equals",
                "compute": "application",
                "target": "/c",
                "operands": ["/a", "/b"],
            }
        ],
    }
    interceptor = HESchemaToolInterceptor({"calc_tool": calc_contract}, on_fail="repair")

    # LangGraph message dict with tool_calls
    message = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_1",
                "name": "calc_tool",
                "args": {"a": 40, "b": 2, "c": 0},
            }
        ],
    }
    interceptor.intercept_message(message)
    # Calculation rule repairs c to 42
    assert message["tool_calls"][0]["args"]["c"] == 42


def test_openai_proxy_chat_completions_with_tools():
    import asyncio

    async def check():
        req_body = {
            "model": "offline-stub",
            "messages": [{"role": "user", "content": "Book refund ORD-99"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "refund",
                        "description": "Process refund",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "order_id": {"type": "string"},
                                "amount": {"type": "number"},
                            },
                        },
                    },
                }
            ],
        }

        resp = await handle_chat_completion(req_body, "local-operator")
        assert resp.status_code == 200
        data = json.loads(resp.body.decode("utf-8"))
        assert data["object"] == "chat.completion"
        assert "choices" in data
        assert len(data["choices"]) == 1

    asyncio.run(check())
