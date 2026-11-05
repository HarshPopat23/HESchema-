# Relationships v2

The [Relationships v2 meta-schema](../../../src/heschema/relationships-v2.json) selects the v2 dialect. It includes [Field Comparison](../../field-comparison/v1/README.md) and [Keyed Uniqueness](../../keyed-uniqueness/v1/README.md) from v1 and adds the two assertions below. Use the v2 meta-schema's `$id` as the root `$schema`. The v1 dialect has its own URI and remains available.

## `aggregateCompare`

Write a nonempty array of rules with `left`, `operator`, and `right`. Every rule must pass. Operators are `eq`, `ne`, `lt`, `lte`, `gt`, and `gte`. Each operand has one of these forms:

| Operand | Value |
| --- | --- |
| `"/itemCount"` | The exact integer at that pointer. |
| `{"count":"/items"}` | The length of the selected array, counting every element. |
| `{"sum":{"array":"/items","item":"/amountMinor"}}` | The exact sum of the selected integer values, one per item. |

Pointers start at the current instance except for `sum.item`, which starts at each item. The empty pointer selects the current value. Empty arrays count and sum to zero. Missing pointers, non-array collections, booleans, numeric strings, and fractional values fail the rule. Both operands must resolve even for `ne`. Totals use integer arithmetic without rounding or fixed-width overflow. HESchema accepts arbitrary-precision integer tokens within its JSON parser limits. It also accepts integral parsed floating-point values in the safe range from −(2⁵³ − 1) to 2⁵³ − 1. Use integer tokens for exact interchange, especially outside that range.

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v2.json",
  "type": "object",
  "aggregateCompare": [
    {"left": "/itemCount", "operator": "eq", "right": {"count": "/items"}},
    {"left": "/totalMinor", "operator": "eq",
     "right": {"sum": {"array": "/items", "item": "/amountMinor"}}}
  ]
}
```

To compare feature and label counts, use a count operand on both sides. Equal lengths establish cardinality. Pairwise alignment needs a common ordering contract or explicit IDs.

## `localReferences`

Write a nonempty array of rules, each with a `source` and a `target`. Each side declares an `array` pointer relative to the current instance and a nonempty list of `keys` pointers relative to each array item. Both lists must have the same length. HESchema checks this cross-field constraint during registration.

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v2.json",
  "type": "object",
  "localReferences": [
    {
      "source": {"array": "/predictions", "keys": ["/datasetId", "/sampleId"]},
      "target": {"array": "/samples", "keys": ["/datasetId", "/id"]}
    }
  ]
}
```

Every source key tuple must identify exactly one target row. Keys are ordered and use the same JSON value equality as `uniqueKeys`. Repeated source references are allowed. Duplicate target tuples fail even when no source points to them. Missing arrays, non-array selections, and missing key parts fail. JSON null is a present value that can match null. To forbid null, use a standard type constraint on the key field. An empty source can reference an empty target. Use `[""]` to key an array of scalar IDs by each whole item.

This covers citations to included sources, predictions tied to samples, and graph endpoints. For a graph, declare separate rules for the two endpoints when both must resolve. All lookups stay within the selected instance. The assertion does not establish whether a citation supports a claim.

## Runtime and conformance

Use HESchema's Python `jsonschema` backend for local validation or prompt-only generation. These assertions only validate the submitted values. Existing contract arithmetic, including `compute: application`, remains a separate path. The v2 dialect supports same-resource static JSON Pointer schema references and one root dialect declaration. Blaze and native provider generation explicitly reject the custom dialect.

[Conformance vectors](cases.json) contain schema fragments and expected instance validity. Apply the v2 dialect at the root. The meta-schema checks keyword syntax. An implementation must evaluate the assertions to establish instance validity.

## Design references

Great Expectations documents count and reconciliation checks, and scikit-learn provides a same-length check for aligned inputs. CSV on the Web and Frictionless Table Schema document ordered foreign key fields. The v2 design applies those patterns to explicitly selected arrays in one JSON instance and uses RFC 6901 for scope and escaping.

[Great Expectations integrity checks](https://docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/integrity/) · [scikit-learn length checks](https://scikit-learn.org/stable/modules/generated/sklearn.utils.check_consistent_length.html) · [CSV on the Web](https://www.w3.org/TR/tabular-metadata/#foreign-key-definitions) · [Frictionless foreign keys](https://specs.frictionlessdata.io/table-schema/#foreign-keys) · [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901) · [RFC 8259 number interoperability](https://www.rfc-editor.org/rfc/rfc8259#section-6)
