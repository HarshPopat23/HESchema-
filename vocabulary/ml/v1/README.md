# ML v1 vocabulary

The [ML v1 meta-schema](../../../src/heschema/ml-v1.json) defines a standalone Draft 2020-12 dialect for dense tensors encoded as JSON. Use its `$id` as the root `$schema`. The dialect declares the ML vocabulary required and uses the standard Draft 2020-12 assertions.

## `tensorShapes`

Write a nonempty array of declarations. Each declaration has a `path` and a `shape`. The path is an RFC 6901 JSON Pointer from the instance at the schema node containing the keyword. An empty pointer selects that entire instance. An unresolved pointer fails.

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/ml-v1.json",
  "type": "object",
  "tensorShapes": [
    {"path": "/embeddings", "shape": ["batch", 768]},
    {"path": "/labels", "shape": ["batch"]}
  ]
}
```

| Dimension declaration | Meaning |
| --- | --- |
| Nonnegative integer, such as `768` | Every observed array on that axis must have exactly this length. |
| Symbol, such as `"batch"` | Every observed use of that symbol must have the same length, including uses on different axes or in different tensors in this assertion. Names match `[A-Za-z_][A-Za-z0-9_]*`. |
| `null` | The length may vary between tensors and evaluations. Within one tensor, arrays on that axis must still all have the same length. |

The shape length is the declared rank. Before that depth, each value must be an array. At that depth, each value must be a JSON number, string, or boolean. An empty shape therefore describes a scalar. Use standard `type` and nested `items` when numeric leaves or another particular element type are required.

Symbols are scoped to one evaluation of one `tensorShapes` assertion, including all declarations in its array. They do not carry into another schema node, sibling branch, array item evaluation, or validation run. Place tensors that must share a dimension in the same assertion. Equal batch dimensions check cardinality. Pairwise alignment needs an explicit ordering convention or matching IDs.

An empty axis has observed length zero and binds its symbol to zero. It has no children, so later dimensions cannot be observed. For example, `[]` passes `["batch", 768]` with `batch = 0`. It gives no evidence about embedding width. Use a standard `minItems` assertion on the batch when its width must be observable. For shape `[2, 0]`, `[[], []]` passes and `[]` fails.

The profile validates inline dense JSON values. Tensor serialization, dtype conversion, sparse or ragged tensor formats, and model execution are separate concerns. The local Python `jsonschema` backend enforces the keyword. The dialect uses one root declaration and same-resource static JSON Pointer schema references. Blaze and native provider generation explicitly reject the custom dialect. Prompt-only generation can use local validation.

[Conformance vectors](cases.json) give schema fragments and expected instance validity. Select the ML v1 dialect at the root when running them.

## Design references

ONNX distinguishes fixed, symbolic, and anonymous dimensions. MLflow tensor signatures show concrete embedding widths and variable batch dimensions. Hugging Face dataset features describe multidimensional arrays and dynamic outer dimensions. NumPy documents why ragged lists need separate handling.

[ONNX Shape Inference](https://onnx.ai/onnx/repo-docs/ShapeInference.html) · [MLflow model signatures](https://mlflow.org/docs/latest/ml/model/signatures/) · [Hugging Face dataset features](https://huggingface.co/docs/datasets/main/en/about_dataset_features) · [NumPy NEP 34](https://numpy.org/neps/nep-0034-infer-dtype-is-object.html)
