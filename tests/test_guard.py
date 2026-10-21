import asyncio
import json
import pytest

from heschema import Contract, ContractViolationError, guard

CONTRACT_DOC = {
    "id": "refund_contract",
    "version": "1.0",
    "outputKind": "document",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["order_id", "amount"],
        "properties": {
            "order_id": {"type": "string"},
            "amount": {"type": "number", "minimum": 1.0},
        },
    },
}

CONTRACT_WITH_CALC = {
    "id": "invoice_contract",
    "version": "1.0",
    "outputKind": "document",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["subtotal", "tax", "total"],
        "properties": {
            "subtotal": {"type": "integer", "minimum": 0},
            "tax": {"type": "integer", "minimum": 0},
            "total": {"type": "integer", "minimum": 0},
        },
    },
    "relationships": [
        {
            "id": "total_calc",
            "kind": "sum_equals",
            "compute": "application",
            "target": "/total",
            "operands": ["/subtotal", "/tax"],
        }
    ],
}


def test_guard_sync_function_success():
    executed = []

    @guard(contract=CONTRACT_DOC, on_fail="raise")
    def process_refund(order_id: str, amount: float):
        executed.append((order_id, amount))
        return {"status": "processed", "id": order_id}

    res = process_refund(order_id="ORD-101", amount=50.0)
    assert res == {"status": "processed", "id": "ORD-101"}
    assert executed == [("ORD-101", 50.0)]


def test_guard_sync_function_violation_raise():
    @guard(contract=CONTRACT_DOC, on_fail="raise")
    def process_refund(order_id: str, amount: float):
        return {"status": "processed"}

    with pytest.raises(ContractViolationError) as exc_info:
        process_refund(order_id="ORD-102", amount=-10.0)

    assert "Contract violation in process_refund" in str(exc_info.value)
    assert len(exc_info.value.errors) > 0


def test_guard_sync_function_violation_refuse():
    called = []

    @guard(contract=CONTRACT_DOC, on_fail="refuse")
    def process_refund(order_id: str, amount: float):
        called.append(order_id)
        return {"status": "processed"}

    res = process_refund(order_id="ORD-103", amount=0.5)  # minimum is 1.0
    assert res["action"] == "refuse"
    assert "Input violates contract" in res["reason"]
    assert len(called) == 0  # Function was NOT executed


@pytest.mark.asyncio
async def test_guard_async_function():
    @guard(contract=CONTRACT_DOC, on_fail="raise")
    async def async_refund(order_id: str, amount: float):
        await asyncio.sleep(0.001)
        return f"Refunded {order_id} for {amount}"

    res = await async_refund(order_id="ORD-200", amount=25.0)
    assert res == "Refunded ORD-200 for 25.0"

    with pytest.raises(ContractViolationError):
        await async_refund(order_id="ORD-200", amount=-5.0)


def test_guard_calculation_repair():
    called_total = []

    @guard(contract=CONTRACT_WITH_CALC, on_fail="repair")
    def process_invoice(subtotal: int, tax: int, total: int = 0):
        called_total.append(total)
        return total

    # Caller passes total=0 or wrong total, but calculation rule computes subtotal + tax = 100 + 15 = 115
    res = process_invoice(subtotal=100, tax=15, total=0)
    assert res == 115
    assert called_total == [115]


def test_guard_direct_validate():
    valid_res = guard.validate({"order_id": "ORD-300", "amount": 99.99}, contract=CONTRACT_DOC)
    assert valid_res["accepted"] is True

    invalid_res = guard.validate({"order_id": "ORD-300", "amount": -1.0}, contract=CONTRACT_DOC)
    assert invalid_res["accepted"] is False
    assert len(invalid_res["errors"]) > 0


def test_guard_load_from_file(tmp_path):
    contract_file = tmp_path / "test_contract.json"
    contract_file.write_text(json.dumps(CONTRACT_DOC), encoding="utf-8")

    @guard(contract=str(contract_file), on_fail="raise")
    def tool_fn(order_id: str, amount: float):
        return f"OK {order_id}"

    assert tool_fn(order_id="ORD-FILE", amount=12.5) == "OK ORD-FILE"
