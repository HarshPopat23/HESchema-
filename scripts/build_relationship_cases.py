"""Build prospective, explicitly unreviewed cases. Does not invoke any provider."""

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research/relationship-categories-v1"
CASES = []
SCENARIOS = [
    "hotel stay",
    "school term",
    "maintenance window",
    "publication schedule",
    "licence period",
    "delivery reservation",
    "insurance coverage",
    "sprint plan",
    "conference booking",
    "equipment rental",
]


def obj(properties, required=None, **keywords):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
        **keywords,
    }


def add(
    family,
    category,
    prompt,
    schema,
    expected,
    bad,
    *,
    rules=(),
    approved=(),
    source_refs=(),
    failure_stage="relationships",
    accepted=False,
):
    case_id = f"R{len(CASES) + 1:03}"
    contract = {
        "id": "relationship-" + case_id.lower(),
        "version": "1",
        "schema": schema,
        "relationships": list(rules),
        "bindings": [
            {"instanceLocation": "/" + key, "contextLocation": "/" + key} for key in approved
        ],
    }
    c = {
        "id": case_id,
        "family": family,
        "category": category,
        "classification": "authoring_gap"
        if family in {"schema_controls", "public_tool_controls"}
        else "source_interpretation_requirement"
        if failure_stage == "oracleOnly"
        else "relationship_requirement",
        "provenance": "public_schema_adaptation_synthetic_task"
        if source_refs
        else "author_created_synthetic",
        "reviewStatus": "unreviewed",
        "sourceRefs": list(source_refs),
        "publicationPermission": "synthetic_example_only",
        "contract": contract,
        "prompt": prompt,
        "expected": expected,
        "counterexamples": [
            {
                "id": case_id + "-negative",
                "output": bad,
                "expectedFailureStage": failure_stage,
                "expectedAccepted": accepted,
                "expectedIntentAgreement": False,
            }
        ],
    }
    if approved:
        c["context"] = {
            "id": case_id + "-source",
            "version": 1,
            "confirmed": True,
            "data": {k: copy.deepcopy(expected[k]) for k in approved},
            "approvedPointers": ["/" + k for k in approved],
            "facts": [],
        }
    CASES.append(c)


for i, scenario in enumerate(SCENARIOS):
    expected = {"start": f"2026-{i + 1:02}-10", "end": f"2026-{i + 1:02}-12"}
    add(
        "date_order",
        "relationship_date_order",
        f"Prepare the {scenario}. Start on {expected['start']}, end on {expected['end']}; start must precede end.",
        obj(
            {
                "start": {"type": "string", "format": "date"},
                "end": {"type": "string", "format": "date"},
            }
        ),
        expected,
        {**expected, "end": expected["start"]},
        rules=[{"id": "date-order", "kind": "date_before", "left": "/start", "right": "/end"}],
        approved=["start"],
    )

for i, scenario in enumerate(SCENARIOS):
    value = f"APPROVED-{i + 101}"
    expected = {"sourceId": value, "confirmationId": value}
    add(
        "field_equality",
        "relationship_equality",
        f"For the {scenario}, sourceId is {value}. Copy it exactly into confirmationId.",
        obj({"sourceId": {"type": "string"}, "confirmationId": {"type": "string"}}),
        expected,
        {**expected, "confirmationId": f"DRAFT-{i}"},
        rules=[
            {"id": "same-id", "kind": "equals", "left": "/confirmationId", "right": "/sourceId"}
        ],
        approved=["sourceId"],
    )

for i, scenario in enumerate(SCENARIOS):
    choices = [f"{i}-standard", f"{i}-priority", f"{i}-economy"]
    expected = {"available": choices, "selected": choices[1]}
    add(
        "document_membership",
        "relationship_membership",
        f"For the {scenario}, available choices are {json.dumps(choices)}. Select {choices[1]}; selected must belong to available.",
        obj(
            {
                "available": {"type": "array", "items": {"type": "string"}},
                "selected": {"type": "string"},
            }
        ),
        expected,
        {**expected, "selected": f"{i}-unavailable"},
        rules=[
            {
                "id": "selection",
                "kind": "member_of",
                "target": "/selected",
                "arrayLocation": "/available",
            }
        ],
        approved=["available"],
    )

for i, scenario in enumerate(SCENARIOS):
    items = [f"{scenario} item {n + 1}" for n in range(i % 5)]
    expected = {"items": items, "count": len(items)}
    add(
        "collection_count",
        "relationship_count",
        f"For the {scenario}, return exactly these items {json.dumps(items)} and their count. Empty lists have count zero.",
        obj(
            {
                "items": {"type": "array", "items": {"type": "string"}},
                "count": {"type": "integer", "minimum": 0},
            }
        ),
        expected,
        {**expected, "count": len(items) + 1},
        rules=[
            {"id": "count", "kind": "count_equals", "target": "/count", "arrayLocation": "/items"}
        ],
        approved=["items"],
    )

for i, scenario in enumerate(SCENARIOS):
    items = [{"amountMinor": i * 103 + 17}, {"amountMinor": 203 + i}, {"amountMinor": 0}]
    total = sum(x["amountMinor"] for x in items)
    expected = {"items": items, "totalMinor": total}
    add(
        "collection_sum",
        "arithmetic_collection_sum",
        f"For the {scenario}, preserve line items {json.dumps(items)}. totalMinor is the exact sum of all amountMinor fields, using integer minor units.",
        obj(
            {
                "items": {"type": "array", "items": obj({"amountMinor": {"type": "integer"}})},
                "totalMinor": {"type": "integer"},
            }
        ),
        expected,
        {**expected, "totalMinor": total + 1},
        rules=[
            {
                "id": "line-total",
                "kind": "sum_items_equals",
                "arrayLocation": "/items",
                "itemLocation": "/amountMinor",
                "target": "/totalMinor",
            }
        ],
        approved=["items"],
    )

for i, scenario in enumerate(SCENARIOS):
    records = [{"id": f"{i}-A", "label": "primary"}, {"id": f"{i}-B", "label": "secondary"}]
    bad = copy.deepcopy(records)
    bad[1]["id"] = bad[0]["id"]
    add(
        "record_key_uniqueness",
        "relationship_unique_key",
        f"For the {scenario}, return records {json.dumps(records)}. Record IDs must be distinct even if labels differ.",
        obj(
            {
                "records": {
                    "type": "array",
                    "items": obj({"id": {"type": "string"}, "label": {"type": "string"}}),
                    "uniqueItems": True,
                }
            }
        ),
        {"records": records},
        {"records": bad},
        rules=[
            {
                "id": "unique-record-id",
                "kind": "unique_by",
                "arrayLocation": "/records",
                "itemLocation": "/id",
            }
        ],
    )

for i, scenario in enumerate(SCENARIOS):
    a, b = i + 2, 99 + i * 107
    kind = "product_equals" if i < 5 else "sum_equals"
    total = a * b if i < 5 else a + b
    expected = {"a": a, "b": b, "result": total}
    add(
        "arithmetic_scalar",
        "arithmetic_product" if i < 5 else "arithmetic_sum",
        f"For the {scenario}, a={a}, b={b}. Return their {'product' if i < 5 else 'sum'} in result; preserve a and b.",
        obj({k: {"type": "integer"} for k in expected}),
        expected,
        {**expected, "result": total + 1},
        rules=[{"id": "arithmetic", "kind": kind, "operands": ["/a", "/b"], "target": "/result"}],
        approved=["a", "b"],
    )

for i in range(4):
    properties = {"card": {"type": "string"}, "billingAddress": {"type": "string"}}
    expected = {"card": f"test-card-{i}", "billingAddress": f"{i + 1} Example Street"}
    add(
        "schema_controls",
        "standard_dependent_required",
        "Return card and its billingAddress from this record: " + json.dumps(expected),
        obj(properties, required=[], dependentRequired={"card": ["billingAddress"]}),
        expected,
        {"card": expected["card"]},
        failure_stage="originalSchema",
    )
for i in range(4):
    expected = {"kind": "priority", "level": i + 1}
    schema = obj(
        {"kind": {"enum": ["priority", "standard"]}, "level": {"type": "integer"}},
        **{
            "if": {"properties": {"kind": {"const": "priority"}}, "required": ["kind"]},
            "then": {"properties": {"level": {"minimum": 1}}},
        },
    )
    add(
        "schema_controls",
        "standard_conditional",
        f"Return priority kind with level={i + 1}. Priority levels must be positive.",
        schema,
        expected,
        {"kind": "priority", "level": 0},
        failure_stage="originalSchema",
    )
for i in range(2):
    expected = {"label": f"final-{i}"}
    add(
        "source_controls",
        "source_interpretation",
        f"Draft label=draft-{i}; final approved correction label=final-{i}. Extract the final label.",
        obj({"label": {"type": "string"}}),
        expected,
        {"label": f"draft-{i}"},
        failure_stage="oracleOnly",
        accepted=True,
    )

# Public schemas/implementation constraints; scenario values are authored, not observed user traffic.
for i in range(2):
    schema = obj(
        {"path": {"type": "string"}, "head": {"type": "number"}, "tail": {"type": "number"}},
        required=["path"],
    )
    # The source checks truthiness, so zero remains allowed alongside the other option.
    schema["not"] = {
        "required": ["head", "tail"],
        "properties": {"head": {"not": {"const": 0}}, "tail": {"not": {"const": 0}}},
    }
    expected = {"path": f"/examples/log-{i}.txt", "head": 3 + i}
    add(
        "public_tool_controls",
        "standard_option_exclusion",
        f"Prepare read_text_file for {expected['path']}, first {3 + i} lines only. Do not also request tail. No filesystem operation will be executed.",
        schema,
        expected,
        {**expected, "tail": 2},
        source_refs=["mcp-filesystem-read-text"],
        failure_stage="originalSchema",
    )
for i in range(4):
    entities = [f"entity-{i}-A", f"entity-{i}-B"]
    expected = {"from": entities[0], "to": entities[1], "relationType": "depends_on"}
    add(
        "public_tool_relations",
        "relationship_trusted_membership",
        f"Prepare one memory create_relations entry: {entities[0]} depends_on {entities[1]}. Both endpoints must exist in the approved graph. Do not execute the tool.",
        obj({k: {"type": "string"} for k in expected}),
        expected,
        {**expected, "to": f"missing-{i}"},
        rules=[
            {
                "id": "from-exists",
                "kind": "reference_member",
                "target": "/from",
                "contextLocation": "/entities",
            },
            {
                "id": "to-exists",
                "kind": "reference_member",
                "target": "/to",
                "contextLocation": "/entities",
            },
        ],
        source_refs=["mcp-memory-create-relations"],
    )
    CASES[-1]["context"] = {
        "id": CASES[-1]["id"] + "-graph",
        "version": 1,
        "confirmed": True,
        "data": {"entities": entities},
        "approvedPointers": ["/entities"],
        "facts": [],
    }

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "cases.jsonl").write_text(
    "".join(json.dumps(c, separators=(",", ":"), ensure_ascii=False) + "\n" for c in CASES),
    encoding="utf-8",
)
sources = json.loads((OUT / "sources.json").read_text(encoding="utf-8"))
for source in sources["sources"]:
    source["excerptSha256"] = hashlib.sha256((OUT / source["excerptPath"]).read_bytes()).hexdigest()
(OUT / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
print(
    f"Built {len(CASES)} prospective cases, including 6 public-tool adaptations; none independently reviewed"
)
