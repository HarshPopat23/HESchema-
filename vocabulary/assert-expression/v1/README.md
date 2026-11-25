# JSON assertion expressions v1

The experimental Python dialect evaluates JSON-only rules inside
assertExpression. It supports the fifteen audited assertion use cases through
the operators, lexical scope, exact representations and diagnostics below.
It is a custom language with explicit semantics. The stock JsonLogic experiment
proposed for Blaze remains a separate integration.

## Select the dialect

Use this root $schema URI:

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/assert-expression-v1.json"
}
```

Install HESchema with Python 3.11+ and run the example using SchemaEngine.
The regex and Unicode dependencies are google-re2 and regex. A regular
expression implementation is required even when the rule contains no matches.
The standalone dialect includes standard Draft 2020-12 validation and
assertExpression; the eight dedicated keywords retain their own dialects.
The optional Blaze backend and hosted provider constrained decoding do not
execute this custom language.

## Complete schema and data

This rule reads the containing object's limit from a predicate over its items.

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/assert-expression-v1.json",
  "type": "object",
  "properties": {
    "limit": {"type": "number"},
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {"quantity": {"type": "number"}},
        "required": ["quantity"]
      }
    }
  },
  "required": ["limit", "items"],
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

Passing data:

```json
{"limit": 3, "items": [{"quantity": 2}]}
```

Failing data:

```json
{"limit": 3, "items": [{"quantity": 4}]}
```

Save these as schema.json and data.json, then run:

```python
import json
from pathlib import Path
from heschema.jsonio import loads
from heschema.schema import SchemaEngine

schema = loads(Path("schema.json").read_text())
data = loads(Path("data.json").read_text())
errors = SchemaEngine().errors(schema, data)
print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
```

The failure points to /items/0/quantity and the lte node in the expression.

## Expression grammar and result types

Each expression is an object containing exactly one operator. All operands
are expressions, except literal payloads and the explicitly documented metadata.
Literal values are not interpreted as rule objects. A top-level assertion must
produce the Boolean true to pass. False fails validation. Runtime errors also
fail validation, with a different reasonCode.

| Operator | Arguments | Result |
| --- | --- | --- |
| literal | Any JSON value | The value |
| get | Object with from, path | Selected value |
| exists | Object with from, path | Boolean presence |
| eq, ne | Exactly two expressions | Structural equality or inequality |
| lt, lte, gt, gte | Exactly two expressions | Strict ordering |
| not | One Boolean expression | Negation |
| and, or | Nonempty Boolean expression array | Short-circuit Boolean |
| if | Object with test, then, else | Selected branch value |
| all, some | Object with array, as, test | Boolean predicate result |
| matches | Two expressions: text and pattern | RE2 substring match |
| date | One string expression | Typed civil date |
| timestamp | One string expression | Typed instant |
| decimal | Decimal string or string expression | Typed exact rational |
| add, subtract, multiply, divide | Two decimal expressions | Exact rational decimal value |
| round | Object with value, scale, mode | Rounded decimal |
| toInteger | One integer or string expression | Exact integer |
| length | One string expression | Code-point count |
| slice | Object with value, start, end, unit | Unicode substring |
| define | Object with name, params, body, in | Result of in |
| call | Object with name, args | Result of a lexical function body |

Typed decimals, dates and timestamps exist only during evaluation. They are
not injected into or substituted for the input document.

## 1. Arbitrary keys and JSON Pointer

```json
{"eq": [{"get": {"from": "root", "path": "/a.b"}}, {"literal": 1}]}
```

The path /a.b selects the literal dotted key. /a/b selects a nested member.
/ selects an empty member name; the empty pointer selects the binding itself.
Escape a tilde as ~0 and a slash as ~1. Array indices use canonical nonnegative
integer spellings. Invalid pointer syntax fails registration.

## 2. Literal objects

```json
{"literal": {"status": "ok", "tags": [null, true], "get": "ordinary data"}}
```

Objects inside literal remain data. This fragment returns an object for use as
an operand, so it must be compared or otherwise consumed before it can serve
as a top-level Boolean assertion.

## 3. Presence and null

```json
{"exists": {"from": "root", "path": "/email"}}
```

Both {"email":null} and {"email":""} pass. An absent member fails the assertion.
A missing get pointer is an evaluation error, rather than an implicit null or
empty string. Use a lazy if with exists when a fallback is needed.

## 4. Structural equality

```json
{"eq": [{"get": {"from": "root", "path": "/a"}}, {"get": {"from": "root", "path": "/b"}}]}
```

Objects compare by member contents regardless of order. Arrays compare in
order. Boolean true differs from number 1; numeric 1 equals 1.0. Decimal, date
and timestamp values compare within their explicit type; they do not coerce
ordinary strings or JSON numbers. Finite floats represent the actual values
supplied by the caller. Exact decimal relationships require decimal strings.

## 5. Root, enclosing items and local references

Root is the instance evaluated by the schema containing the assertion. It is
the outer document only when that schema evaluates the outer document. Under
items or a local reference it is the current item or object. Put an assertion
at the enclosing object when it must compare child collections and sibling
fields.

All and some introduce a named item binding. Nested predicates retain access
to all enclosing bindings and root. Each name must be a fresh identifier;
shadowing is rejected. get can read the enclosing group's limit while an inner
predicate reads the current item's value. The conformance tests include this
two-level example.

## 6. Dynamic regular expressions

```json
{"matches": [
  {"get": {"from": "root", "path": "/text"}},
  {"get": {"from": "root", "path": "/pattern"}}
]}
```

With text AB12 and pattern ^[A-Z]+[0-9]+$, this passes. matches uses RE2 search
semantics; anchor a pattern for whole-string checks. Lookaround and
backreferences are outside RE2 syntax. A literal invalid pattern is rejected
at registration. A dynamic invalid pattern becomes an evaluation error at the
pattern's instance location.

Patterns have at most 1,000 code points and a 1 MiB RE2 compilation memory
budget. Text has at most 100,000 code points. These are resource bounds, not a
general execution sandbox.

## 7. Civil dates and timestamp instants

```json
{"lt": [
  {"timestamp": {"literal": "2025-01-01T00:30:00+01:00"}},
  {"timestamp": {"literal": "2025-01-01T00:00:00Z"}}
]}
```

This passes because the first instant is 23:30 UTC on the previous day.

Date requires a real Gregorian YYYY-MM-DD value in years 0001 through 9999.
2025-02-29 fails; 2024-02-29 passes. Timestamp reuses HESchema's ordering
profile: uppercase T and Z, explicit offset, seconds 00 through 59, hours
00 through 23, and optional decimal fractional seconds. It compares exact
fractional seconds and normalizes offsets without floating-point arithmetic.
Date-only timestamps, leap-second spellings and 24:00:00 are rejected.
These are a documented timestamp profile, rather than every RFC 3339 spelling.
No implicit time zone is inferred. Temporal text is limited to 128 characters.

## 8. Exact decimal expressions and rounding

```json
{"eq": [
  {"add": [{"decimal": "0.10"}, {"decimal": "0.20"}]},
  {"decimal": "0.30"}
]}
```

This passes exactly. Decimal operands are strings with at most 38 total digits
and 18 fractional digits, following arithmeticEquals's lexical policy. Exponents,
leading plus signs, whitespace and leading integer zeros fail. Dynamic strings
can be supplied through decimal with a get expression.

Arithmetic requires explicitly typed decimals. It computes exact rational
intermediates, including repeating quotients, without a floating-point context.
Intermediates are bounded to 4,096 numerator and denominator bits. Divide by
zero is an evaluation error.

```json
{"eq": [
  {"round": {
    "value": {"divide": [{"decimal": "1"}, {"decimal": "3"}]},
    "scale": 2,
    "mode": "half-even"
  }},
  {"decimal": "0.33"}
]}
```

Scale is an integer from 0 through 18. Modes are half-even, half-up (ties away
from zero), and toward-zero. Rounding occurs only where round is written.
The rounded result must fit the decimal precision profile. Equal decimal
values can have different displayed scales. The instance is never rewritten.

## 9. Exact integer ingestion

HESchema's strict jsonio.loads already parses JSON integer tokens as Python
integers. The conformance suite round-trips the distinct tokens
9007199254740992 and 9007199254740993 through JSON text and SchemaEngine.

Expression values support integers with at most 1,000 decimal digits.
Use canonical decimal strings and toInteger when a transport cannot preserve
integer tokens. JSON floating-point tokens and caller-supplied floats retain
their already parsed precision. An evaluator cannot recover rounded digits;
exact decimal inputs use the explicit string representation above.

## 10. Unicode code points and grapheme clusters

```json
{"eq": [
  {"slice": {"value": {"literal": "😀X"}, "start": 0, "end": 1, "unit": "codePoint"}},
  {"literal": "😀"}
]}
```

Length counts Unicode code points. Slice uses a half-open interval with
0 <= start <= end <= the selected unit count. Bounds are nonnegative integers.
Code-point slicing preserves a complete emoji scalar. Combining marks remain
separate code points. Set unit to grapheme to keep a combining sequence or
joined emoji together using regex's Unicode grapheme implementation.
Grapheme matching has a 50 ms timeout and uses the Unicode tables supplied by
the pinned regex 2026.11.24 release. No normalization is applied. Isolated surrogate code points
are rejected.

## 11. Structured validation diagnostics

The example at the top produces diagnostics shaped like:

```json
{
  "code": "SCHEMA_INVALID",
  "reasonCode": "ASSERT_EXPRESSION_FALSE",
  "instanceLocation": "/items/0/quantity",
  "schemaLocation": "/assertExpression",
  "expressionLocation": "/assertExpression/all/test/lte",
  "keyword": "assertExpression"
}
```

Other existing diagnostic fields, including message, remain available.
reasonCode distinguishes a false assertion from ASSERT_EXPRESSION_ERROR.
Schema locations point to the source declaration even through local references.
Expression locations point to the responsible operator. Instance locations
track get operations and predicate items. Comparisons prefer the left operand's
location, then the right; literal-only rules use the assertion's instance.
These paths identify the values involved; they are not an automatic repair.
All reports the first failing item. Some returns the first success, or reports
the array location when no item succeeds. Logical operations short-circuit,
so diagnostics do not claim an exhaustive failure list.

## 12. Registration and known-type checking

Registration checks the recursive meta-schema, operator names, arity, pointer
syntax, binding names and inferred types in every branch. Known string/number
mismatches, non-Boolean conditions, and invalid types in unused branches are
schema errors. A literal non-Boolean top-level expression is also rejected.
Dynamic get operands cannot be fully typed without data and are checked at
runtime. Standard JSON Schema properties/type checks remain useful.

Functions are checked both at definition and with known argument types at
each call. Unknown functions, recursion and argument-count mismatches fail
registration. An invalid schema raises ValueError. A valid rule that returns
false or encounters bad input produces validation diagnostics.

Compared with the initial experimental release, statically known type errors
now fail registration and instance paths are more precise. Existing well-typed
expressions keep their Boolean behavior.

## 13. Empty-array quantifiers

All over an empty array returns true. Some over an empty array returns false.
Use the standard minItems keyword to require an item. Predicate inputs must be
arrays and predicate results must be actual Booleans.

## 14. Strict operands and explicit conversions

```json
{"lt": [{"toInteger": {"literal": "4"}}, {"literal": 5}]}
```

This passes. Ordinary ordering accepts matching finite numeric or temporal
types; it does not coerce strings, null or booleans. ToInteger accepts an integer
or a whole canonical signed integer string. It rejects "4kg", "+4", "04",
whitespace and floats, including fractional floats. JSON integer conversion
does not silently truncate a fraction. Numeric ordering and decimal ordering
use separate explicit representations.

## 15. Lazy built-ins and user-defined JSON functions

```json
{"define": {
  "name": "choose",
  "params": ["condition", "yes", "no"],
  "body": {"if": {
    "test": {"get": {"from": "condition", "path": ""}},
    "then": {"get": {"from": "yes", "path": ""}},
    "else": {"get": {"from": "no", "path": ""}}
  }},
  "in": {"call": {
    "name": "choose",
    "args": [
      {"literal": true},
      {"literal": true},
      {"eq": [
        {"divide": [{"decimal": "1"}, {"decimal": "0"}]},
        {"decimal": "0"}
      ]}
    ]
  }}
}}
```

This passes: choose evaluates its test and selected argument, leaving the divide
by zero unevaluated. The evaluator still checks that argument's rule structure
and known types at registration.

Define installs a lexical function for its in expression. The body can read
definition-site bindings and its named parameters. Arguments are expressions
captured with their call-site bindings. Parameters evaluate on demand each
time they are read (call-by-name), with the shared budget. Unused arguments
do not run. Names and parameters must be fresh in their respective scope.
The function is not available in its own body, preventing recursive definitions.
Only JSON expression bodies are supported; there is no Python callback,
network lookup, dynamic code execution or operator override mechanism.

## Resource bounds and compatibility

Operator nesting and JSON value nesting have a limit of 48. Schema checking,
runtime evaluation and each input/literal tree have a 10,000-node budget.
The runtime evaluation budget includes repeated lazy argument reads, collection
predicates and structural equality. Text is limited to 100,000 code points.
Regex, temporal, decimal and integer operations have the additional bounds
above. Existing SchemaEngine schema complexity budgets also remain active.

Root and nested instance pointers continue to use the existing custom-dialect
rules: one schema resource, local static references, no nested dialect switches
and no external references. Literal objects are checked as data, not schemas.

The [conformance corpus](cases.json) covers each audit gap with passing and
rejecting data; tests also cover invalid schemas, resource boundaries, local
references and function scope. This profile makes the fifteen audited use cases
expressible with defined boundaries. It does not establish factual correctness
of arbitrary LLM output: source comparisons still need independently trusted data.

## References

- [RE2 syntax](https://github.com/google/re2/wiki/Syntax)
- [RFC 3339 timestamp forms](https://www.rfc-editor.org/rfc/rfc3339)
- [Unicode grapheme segmentation](https://www.unicode.org/reports/tr29/)
- [Grapheme library and timeout API](https://pypi.org/project/regex/)
