# Field Comparison vocabulary v1

This custom vocabulary adds the `compareFields` assertion to Draft 2020-12. A schema opts in using the `$id` of the [dialect meta-schema](../../../src/heschema/field-comparison-v1.json) as its root `$schema`. The meta-schema declares this vocabulary required. The vocabulary's identifier is its versioned specification URL in that declaration.

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/field-comparison-v1.json",
  "type": "object",
  "required": ["minReplicas", "maxReplicas"],
  "properties": {
    "minReplicas": {"type": "integer"},
    "maxReplicas": {"type": "integer"}
  },
  "compareFields": [
    {"left": "/minReplicas", "operator": "lte", "right": "/maxReplicas", "mode": "number"}
  ]
}
```

Each rule has four required members. A nonempty array of rules passes when every rule passes. Evaluation asserts validity without modifying the document.

- `left` and `right` are RFC 6901 JSON Pointers starting at the instance evaluated by the schema object containing the keyword. Under `items`, each starts at that array item. The empty pointer selects the current instance. Use `~0` for a literal tilde and `~1` for a literal slash. Array indices use canonical decimal notation without leading zeroes. Unresolved pointers, including the array append token, fail the comparison. An existing JSON null is a value.
- `operator` is one of `eq`, `ne`, `lt`, `lte`, `gt`, or `gte`. Both operands must be valid in the selected mode even for `ne`.
- `mode: json` allows only `eq` and `ne`. Equality follows JSON Schema instance equality. Numbers compare by value, booleans are distinct from numbers, arrays compare in order, and object member order is immaterial.
- `mode: number` requires two finite JSON numbers. Compare them by numeric value without coercion or tolerance. Implementations must document the precision of their JSON number representation. HESchema uses its existing Python integer and binary floating-point representations.
- `mode: date` requires two Gregorian calendar dates from year 0001 to 9999 in ASCII `YYYY-MM-DD` form. Compare them chronologically. Invalid dates, timestamps and offsets fail.

To require `startDate < endDate`, use `lt` with `date` mode. To require two IDs to match, use `eq` with `json` mode and describe both IDs as strings with standard keywords. For optional operands, guard the comparison using standard conditionals. The keyword neither creates properties nor marks them as evaluated for `unevaluatedProperties`.

## HESchema implementation

Use the `jsonschema` backend for local schema and contract validation. HESchema's v1 registration supports same-resource static JSON Pointer references to schema nodes, with one dialect declaration at the root. Blaze and native provider generation reject this dialect. Contract generation can use `prompt_only` with local validation. Existing application relationship rules remain available, including checks against separately approved context.

[Conformance vectors](cases.json) are standalone JSON data. Each group contains a schema fragment and named instances with expected validity. Apply the dialect at the root before evaluating.

## Design references

Ajv's `$data` and json-everything's Data vocabulary can derive keyword values from instance data. This vocabulary fixes the operand scope and offers a finite set of comparisons so the behavior can be tested directly across implementations. Pydantic model validators and Great Expectations column-pair rules show corresponding checks in application and data pipelines.

[Ajv data references](https://ajv.js.org/guide/combining-schemas.html#data-reference) · [json-everything Data](https://docs.json-everything.net/schema/vocabs/data-2023/) · [Pydantic model validators](https://docs.pydantic.dev/latest/concepts/validators/#model-validators) · [Great Expectations integrity](https://docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/integrity/) · [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901)
