# Validator acceptance and boundary controls

The main study's observed wrong-acceptance count is evidence about its saved
outputs. It does not establish complete validator coverage or a zero error rate.
This suite adds labelled positive and negative controls to exercise the declared
acceptance set, including legitimate outputs that differ from one gold answer.
No live inference is needed or performed by these tests.

## Defects reproduced and fixed

The audit started from `c75bd31a55cbe58eca42061633dcad3877abe6e5`.

### Bound fields using local references

A schema can define a string in `$defs`, reference it from a property, and bind
that property to approved context. Previously, preflight constructed a validator
from the detached field schema. A valid value then raised `PointerToNowhere`
because the field's `$ref` no longer had its original root.

Preflight now locates the field through a JSON Pointer in the original schema,
using `Validator.evolve` to preserve reference resolution. Pointer lookup also
preserves enclosing `$id` resource scopes, so a nested resource resolves its own
definitions rather than a same-named definition at the outer root. Fragment and
pointer escaping are tested. Field contradictions are still rejected; missing
references are not replaced with permissive schemas. No external reference
fetching or new dialect support is introduced.

Tests cover `const` and `enum`, root definitions, local anchors, nested resources,
tool envelopes within their existing restrictions, and API context confirmation.
The full original/effective schema checks remain in place.

### Noncanonical array binding tokens

The old projection used `str.isdecimal()`, which accepts non-ASCII decimal digits.
A pointer token such as `/١` could be silently projected as array index 1 even
though runtime pointer resolution rejects that array token. Projection and field
lookup now share an ASCII canonical-index check and the existing 0–1024 limit.
Noncanonical array indices raise `ContextError`; object property names such as
`"01"`, `"-"` and `"١"` remain legal literal keys.

## Control matrix

| Area | Valid controls | Invalid or unavailable controls |
| --- | --- | --- |
| Multiple answers | Either of two actual approved Citi Bike station IDs, independent traveller counts and optional notes | ID outside the set, wrong types, adjacent invalid counts, excess text and extra properties |
| Public source copying | Preserved WfCommons, USGS, Citi Bike, Crossref and PyPI answers with whitespace, key-order and Unicode serialization changes | Existing source-mutation tests remain; alternate serializations must not create false rejections |
| Source bounds | Inclusive endpoints and integral real aliases | Just outside projected limits while original shape passes, original limits, booleans and fractions |
| Standard bounds | Character lengths, array sizes, exclusive numeric limits, nullable required fields | Empty/oversized values, excluded endpoints, missing fields and extra properties |
| JSON equality | Object reordering, mathematical numeric aliases, bool/null preservation | Boolean/number confusion, missing fields, reordered arrays and codepoint-different strings |
| All nine relationship kinds | At least two valid documents per kind | Wrong result, incompatible input/value and missing input; assert stage and rule ID |
| Context | Approved bindings, specific approved membership arrays, optional bindings absent without false rejection | Absent/partial/unapproved/missing required facts, unconfirmed/expired approval, wrong contract hash and expired/unverified facts |
| Pointers | Root bindings, escaped names and indices 0 and 1024 | Leading-zero, signed, non-ASCII, noninteger, append and out-of-limit array tokens |
| Strict JSON | Root null, false, zero, empty string, array and object distinguished from absence | Duplicate keys, non-finite/underflow numbers, multiple values, trailing text, Markdown wrappers and incomplete JSON |
| Calculations | Empty arrays, negative values/cancellation and matching model/application results | Corrupted copied inputs rejected before arithmetic; existing target-limit and atomicity controls remain |
| Decisions | Valid refusal/clarification remain distinct from successful data answers | Tool-bearing control envelopes, missing context and known truncation cannot become successful authorized answers |

The matrix explicitly checks all registered relationship kinds, so adding a kind
requires adding its positive and negative controls. Valid and wrong rule documents
share valid original structure and approved source fields: schema rejection cannot
accidentally stand in for relationship enforcement.

The new files are `tests/test_validator_controls.py` and
`tests/test_validator_references.py`. A shared module-scoped `validation_engine`
fixture runs the same core acceptance controls with Python normally and the native
cross-check when `HESCHEMA_TEST_BLAZE=1`. Native CI now includes both files, in
addition to the pre-existing native smoke suite.

## Data provenance and expectations

Public data is reused from the frozen repository file
`research/contract-main-study-v1/inputs/cases.json`; its existing source links and
snapshot provenance remain unchanged. The station choice contract is a
researcher-authored adaptation permitting multiple approved IDs, not an organic
user task or a task from the earlier live experiment. Alternate source-answer
serializations are constructed representations of computed reference answers.

Other small examples and deliberately corrupted values are constructed test
controls, **not** original provider responses or new empirical results. Expected
outcomes are declared in the tests; arithmetic targets in relationship controls
are literal, inspectable values rather than answers returned by the arithmetic
function under test.

The distinction between `accepted`, `success`, `semanticValid`, context errors and
`executionAuthorized` is retained. Schema-only acceptance does not become proof of
source agreement; optional context absence is not falsely rejected; accepted
refusal/clarification is not a successful data response. Decisions remain
non-authorizing. Tests also check that validation does not mutate inputs, schemas
or approved context.

## Running the checks

```sh
python -m pytest -q tests/test_validator_controls.py tests/test_validator_references.py

# Install native dependencies first if necessary: npm ci --prefix native
HESCHEMA_TEST_BLAZE=1 JSONSCHEMA_CLI="$PWD/native/node_modules/.bin/jsonschema" \
  python -m pytest -q tests/test_blaze.py tests/test_validator_controls.py \
  tests/test_validator_references.py
```

Run the full suite for interactions with repairs, optional calculations, API
approval/version checks and reports. These finite controls do not prove full JSON
Schema conformance, exhaustive application coverage, production security, precise
arbitrary-decimal arithmetic, model accuracy or performance. Native mode still
includes the Python reference check; its known precision and format limitations
have not been removed. Passing both modes is not evidence of two independent
implementations of the application rules.

Parametrized tests and alternate serializations are not independent real-world
tasks. New schemas, rules and developer workflows need additional reviewed valid
and invalid acceptance sets. Zero observed wrong acceptance/rejection should
always name the tested cohort and its limits.

## Primary technical references

- [JSON Schema Core: instance equality](https://json-schema.org/draft/2020-12/json-schema-core#section-4.2.2)
  defines numeric equality, object ordering, array ordering and exact strings.
- [JSON Schema Validation](https://json-schema.org/draft/2020-12/json-schema-validation)
  defines inclusive/exclusive numeric limits, lengths, sizes, required and nullable values.
- [RFC 6901: evaluation](https://www.rfc-editor.org/rfc/rfc6901#section-4)
  distinguishes literal object keys from canonical ASCII array indices.
- [python-jsonschema Validator.evolve](https://python-jsonschema.readthedocs.io/en/stable/validate/#jsonschema.protocols.Validator.evolve)
  preserves reference-resolution behavior when changing the evaluated schema.
