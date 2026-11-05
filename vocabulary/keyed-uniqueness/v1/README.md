# Keyed Uniqueness vocabulary v1

`uniqueKeys` checks whether the items in an array have distinct keys, even when the rest of their fields differ. The [Relationships v1 dialect](../../../src/heschema/relationships-v1.json) includes this vocabulary and [Field Comparison v1](../../field-comparison/v1/README.md). Use its `$id` as the root `$schema`.

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v1.json",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["datasetId", "sampleId"]
  },
  "uniqueKeys": ["/datasetId", "/sampleId"]
}
```

Two records may share a `sampleId` when they belong to different datasets. Two records with both IDs equal fail, even if one has a different label or timestamp. Use `["/sku"]` for a single key.

## Assertion behavior

- The keyword value must be a nonempty array of RFC 6901 JSON Pointers. Each pointer resolves from the current item. An empty pointer selects the whole item.
- For each item, build an ordered tuple of the resolved values. All tuples must be distinct. JSON Schema equality applies to each component. Numeric aliases such as `1` and `1.0` compare equal. Booleans and numbers remain distinct, arrays compare in order, and object member order is immaterial.
- A pointer that cannot resolve contributes an internal missing value, distinct from JSON `null`. A missing component only causes failure when the entire tuple duplicates another item's tuple. Use standard `items` and `required` assertions wherever every item must supply a key.
- The assertion succeeds for empty arrays and is ignored for non-arrays. Add `type: array` when an array is required.

These semantics align with the [Array Extensions `uniqueKeys` keyword](https://docs.json-everything.net/schema/vocabs/array-ext/#31-uniquekeys). HESchema implements this single keyword under its own vocabulary URI. Ajv's [`uniqueItemProperties`](https://ajv.js.org/packages/ajv-keywords.html#uniqueitemproperties) instead requires each named property to be individually unique.

HESchema's existing contract rule `unique_by` treats a missing item value as `needs_context`. To migrate a required single-field key, pair `uniqueKeys` with a schema requiring that field and expect a schema validation error if it is absent.

The HESchema Python backend supports this dialect for local validation and prompt-only generation. It accepts same-resource static JSON Pointer references with one root dialect declaration. Blaze and native provider generation reject it explicitly. Existing field-comparison schemas may continue using their original dialect URI.

[Conformance vectors](cases.json) contain schema fragments and instance validity expectations. Select the Relationships v1 dialect at the root before evaluating.
