# Prospective relationship-category study

This pack prepares Juan's proposed research; it contains **no new model results**.
All 86 cases are authored, synthetic and unreviewed, including six adaptations of
public MCP tool schemas/implementation constraints. Public implementation evidence
is different from a naturally observed user task or LLM failure.

| Family | Cases | Constraint/check |
| --- | ---: | --- |
| Date ordering | 10 | `date_before`, strict calendar dates |
| Field equality | 10 | `equals`, approved source ID copied into another field |
| In-document membership | 10 | `member_of`, selection belongs to the approved array |
| Collection counts | 10 | `count_equals`, including empty lists |
| Collection totals | 10 | `sum_items_equals`, integer minor units |
| Record-key uniqueness | 10 | `unique_by`, not whole-record `uniqueItems` |
| Scalar arithmetic | 10 | Five product and five sum cases |
| Standard schema controls | 8 | Four `dependentRequired`, four `if`/`then` |
| Source interpretation controls | 2 | Schema-valid wrong answer, no runtime oracle feedback |
| Public filesystem adaptations | 2 | Standard schema can express the head/tail exclusion |
| Public memory adaptations | 4 | Endpoints must exist in a trusted graph snapshot |

The same scenario themes recur across families. Numeric variants and common
templates are not independent application evidence. Existing controlled reports
cluster by family; do not claim 86 independent real use cases. A human should
review the gold outputs, negative controls and task realism before a live study.

## Offline preflight

```sh
python scripts/build_relationship_cases.py
heschema research-audit --out results/relationship-v1/preflight.json
# Optional second validation engine, after npm ci --prefix native:
JSONSCHEMA_CLI="$PWD/native/node_modules/.bin/jsonschema" heschema research-audit --engine blaze
heschema decoding-study --dataset research/relationship-categories-v1/cases.jsonl \
  --repeats 3 --warmup 3
```

The audit checks accepted/task-correct positives, labelled counterexamples,
scoring-data isolation, provenance, permission status, public-source references
and excerpt hashes. It does not call a provider. There are 86 negative controls
in addition to the 86 positive scoring outputs. A positive example, or a negative
mutation rejected offline, is not an empirical model success/failure.

The three-arm dry run schedules 86 x 3 x 3 = **774 first trials**, plus three
warmups. That is a planning count, not requests already made. Begin with a small
reviewed pilot; use explicit request budgets and fresh result folders. Do not
start the full campaign simply because the fixture audit passes.

## Public sources

`sources.json` pins the MCP servers repository to a commit and records original
blob IDs, exact excerpt line ranges, excerpt SHA-256 values and the bundled
upstream license. `sources/` preserves the relevant implementation and schema
definitions. The original repository documents a license transition; preserve
the supplied license rather than simplifying it to an unqualified MIT label.

The filesystem contract is a **manual adaptation**: it adds a standard `not`
constraint for the implementation's nonzero head/tail exclusion. Zero is false
in that JavaScript check and is not silently forbidden by our adaptation.
The memory cases validate one relation entry, not the complete MCP transport
envelope, against a synthetic approved list of entity names. Neither adaptation
claims byte-for-byte equivalence to the advertised tool schema or observed
company adoption. No filesystem or graph operation is executed.

See [the research protocol](../../docs/relationship-research.md) for failure
categories, provider controls, collection of real tasks and claim boundaries.
