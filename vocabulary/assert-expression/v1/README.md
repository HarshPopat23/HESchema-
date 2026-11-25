# JSON assertion expressions v1

Select this experimental dialect at the schema root:

`https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/assert-expression-v1.json`

The Python HESchema validator executes the JSON object in `assertExpression`.
Register schemas through SchemaEngine so every expression branch is checked
before evaluation. A successful expression must return the Boolean true.
This standalone dialect does not include the other eight custom keywords.

## Example

Every quantity must be at most the document's limit:

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/assert-expression-v1.json",
  "type": "object",
  "assertExpression": {
    "all": {
      "array": {"get": {"from": "root", "path": "/items"}},
      "as": "item",
      "test": {
        "lte": [
          {"get": {"from": "item", "path": "/quantity"}},
          {"get": {"from": "root", "path": "/limit"}}
        ]
      }
    }
  }
}
```

`{"limit":3,"items":[{"quantity":2}]}` passes.
Changing quantity to 4 fails. Add standard properties, required, and type
constraints for the application's full document contract.

## Operators

Each expression has exactly one operator. All operands are expressions,
except the contents of literal and the binding/pointer metadata.

| Operator | Arguments and behavior |
| --- | --- |
| literal | Any JSON value, kept as data |
| get | Object with from and path, resolves an RFC 6901 pointer |
| exists | Same object, checks presence independently of null or empty string |
| eq, ne | Exactly two expressions, JSON structural equality or inequality |
| lt, lte, gt, gte | Exactly two finite numeric expressions; booleans and strings fail |
| not | One Boolean expression |
| and, or | Nonempty expression array, short-circuits left to right |
| if | Object with test, then, else; evaluates only the selected branch |
| all, some | Object with array expression, fresh as identifier, test expression |

The root binding is the instance at the schema containing the assertion,
including when evaluated through a local reference or array subschema. It is
not automatically the outermost document. Predicates introduce lexical bindings
and can read their enclosing bindings. Binding shadowing is rejected. Empty
arrays satisfy all and fail some. Missing get pointers are evaluation errors.

Objects compare without member-order sensitivity; arrays compare in order.
Booleans differ from numbers, while 1 equals 1.0. Python integers retain their
precision. Floats retain only the precision supplied by the caller's parser.
Converting an already rounded value cannot recover lost digits.

## Registration, errors and limits

Registration checks names, arity, bindings and pointers in all branches.
Operand types and the final Boolean requirement are checked during evaluation.
Nesting is limited to 48 operator levels and each evaluation to 10,000 visited
expression nodes. Collection traversal consumes the same budget.
SchemaEngine's existing instance and schema complexity limits also apply.

Errors use the existing SchemaEngine diagnostic format with keyword
assertExpression and its schema location. Messages distinguish
ASSERT_EXPRESSION_FALSE from ASSERT_EXPRESSION_ERROR. An array predicate
currently reports at the containing assertion's instance location; it does not
automatically identify every failing item.

## Relationship to the earlier 15-gap audit

This v1 addresses pointer access, literal values, presence, structural equality,
lexical predicate scope, empty-array semantics, strict operand types and built-in
lazy evaluation. Registration catches structural rule errors in untaken branches.
Basic diagnostics and input precision have the limitations described above.

Dynamic regex, civil dates/timestamps, decimal expression arithmetic, Unicode
slicing, custom lazy extensions, per-item provenance, and static type inference
remain future work. The existing arithmeticEquals dialect handles its documented
decimal-string calculations separately.

These are HESchema expression semantics. They are not a stock JsonLogic
implementation or a Blaze integration. Juan's proposed JsonLogic experiment in
Blaze is a separate project.
