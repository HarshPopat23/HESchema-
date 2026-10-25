import pytest

from heschema import Contract, guard
from heschema.calculations import calculation_plan, validate_with_calculations
from heschema.contract_prompt import contract_messages
from heschema.rules import calculation_value, check_rules, evaluate_rules
from heschema.schema import SchemaEngine


def test_division_and_percentage_rules():
    rules = [
        {
            "id": "r_div",
            "kind": "division_equals",
            "compute": "application",
            "target": "/average",
            "operands": ["/total", "/count"],
            "precision": 2,
        },
        {
            "id": "r_pct",
            "kind": "percentage_of",
            "compute": "application",
            "target": "/tax",
            "operands": ["/tax_rate", "/subtotal"],
            "precision": 2,
        },
    ]
    check_rules(rules)

    doc = {"total": 100, "count": 3, "tax_rate": 8.5, "subtotal": 200.0}
    val_div = calculation_value(doc, rules[0])
    assert val_div == 33.33

    val_pct = calculation_value(doc, rules[1])
    assert val_pct == 17.0

    # Test evaluation
    doc_with_targets = {**doc, "average": 33.33, "tax": 17.0}
    eval_res = evaluate_rules(doc_with_targets, rules)
    assert eval_res["status"] == "valid"
    assert len(eval_res["errors"]) == 0

    # Test division by zero
    doc_zero = {"total": 100, "count": 0}
    with pytest.raises(ValueError, match="Division by zero"):
        calculation_value(doc_zero, rules[0])


def test_nested_calculation_targets():
    contract_data = {
        "id": "nested_contract",
        "version": "1.0",
        "outputKind": "document",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["financials"],
            "properties": {
                "financials": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["subtotal", "tax", "total"],
                    "properties": {
                        "subtotal": {"type": "number"},
                        "tax": {"type": "number"},
                        "total": {"type": "number"},
                    },
                }
            },
        },
        "relationships": [
            {
                "id": "nested_total",
                "kind": "sum_equals",
                "compute": "application",
                "target": "/financials/total",
                "operands": ["/financials/subtotal", "/financials/tax"],
                "precision": 2,
            }
        ],
    }
    contract = Contract(**contract_data)
    plan = calculation_plan(contract)
    assert len(plan) == 1
    assert plan[0]["target"] == "/financials/total"

    engine = SchemaEngine()
    # Input has subtotal and tax; total is calculated and assembled atomically
    payload = {"financials": {"subtotal": 120.50, "tax": 9.64}}
    res = validate_with_calculations(payload, engine, contract)
    assert res["accepted"] is True
    assert res["parsed"]["financials"]["total"] == 130.14
    assert res["calculation"]["status"] == "applied"


def test_guard_with_nested_and_floats():
    contract_data = {
        "id": "discount_contract",
        "version": "1.0",
        "outputKind": "document",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["item", "pricing"],
            "properties": {
                "item": {"type": "string"},
                "pricing": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["original", "discount_rate", "final_price"],
                    "properties": {
                        "original": {"type": "number", "minimum": 0},
                        "discount_rate": {"type": "number", "minimum": 0, "maximum": 100},
                        "final_price": {"type": "number", "minimum": 0},
                    },
                },
            },
        },
        "relationships": [
            {
                "id": "discount_calc",
                "kind": "percentage_of",
                "compute": "application",
                "target": "/pricing/final_price",
                "operands": ["/pricing/discount_rate", "/pricing/original"],
                "precision": 2,
            }
        ],
    }

    @guard(contract=contract_data, on_fail="repair")
    def calculate_deal(item: str, pricing: dict):
        return pricing["final_price"]

    # Original $80 with 25% = $20.0
    result = calculate_deal(item="Sneakers", pricing={"original": 80.0, "discount_rate": 25.0, "final_price": 0})
    assert result == 20.0


def test_dynamic_list_membership_prompting():
    contract = Contract(
        id="list_test",
        version="1.0",
        schema={"type": "object", "properties": {"color": {"type": "string"}}},
    )
    snapshot = {"confirmed": True, "data": {}, "approvedPointers": []}
    evidence = {
        "activeBindings": [
            {
                "instanceLocation": "/color",
                "contextLocation": "/colors",
                "keyword": "enum",
                "value": ["crimson", "emerald", "sapphire", "amber"],
            }
        ],
        "missingBindings": [],
    }

    msgs = contract_messages(contract, snapshot, evidence, contract.schema, "Pick a color")
    prompt_text = msgs[0]["content"]
    assert "Dynamic list boundaries:" in prompt_text
    assert "Permitted choices for `/color`: [`crimson`, `emerald`, `sapphire`, `amber`]" in prompt_text
