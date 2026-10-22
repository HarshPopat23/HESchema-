# HESchema: 60 Tasks Adapted from Real Public Records

**60 tasks · 10 source projects · 6 relationship families · 0 model requests run**

**The upstream records are authentic public API responses. The task instructions, output schemas, contracts and evaluation rules were authored for this study with AI assistance. This is not a collection of 60 original human production prompts. Expected answers are computed from preserved records, not original LLM responses.**

Prepared 21 October 2026. This is a dataset and planned experiment, not a performance report. Research covered the ten primary sources below; it was not an exhaustive search of the entire internet.

## What is included

Each numbered task below contains its exact prompt, source facts, ordinary output schema, HESchema contract and one valid expected-answer example. The companion ZIP contains the original response bytes, capture timestamps, URLs, SHA-256 hashes, field-level source projections, all enumerated valid answers, independent checks, prepared request templates and randomized schedule.

- 60 tasks, six per project; ten tasks in each relationship family.
- 28 primary-service JSON response snapshots. Selected source subsets are explicitly scoped; they are not asserted to be complete upstream databases.
- 734 enumerated valid answer alternatives, checked against the independent oracle and current HESchema implementation.
- 120 constructed negative engineering controls, kept separate from the 60 live inputs. They are not original model failures.
- 240 prepared request templates: one per task and approach. They have not been sent to a provider.
- 2,160 planned initial slots: 60 tasks × 4 approaches × 3 models × 3 repeats. Repairs are additional.

## Source projects

| Project | Real records used | Tasks |
|---|---|---:|
| NASA EONET | Closed natural events, observation dates, source IDs and geometry series | 6 |
| RCSB PDB | Six deposited structure entries and archive metadata | 6 |
| UniProt | Six reviewed E. coli ribosomal protein entries | 6 |
| Open Library | Six actual edition/catalogue records | 6 |
| Kysely / npm | Published Kysely release metadata and dependency names | 6 |
| Rails / RubyGems | Published Rails release metadata and download counters | 6 |
| U.S. Treasury DTS | 1,267 operating-cash rows across all three pages of the captured query | 6 |
| World Bank WDI | Six countries' 2020 population observations | 6 |
| Wikimedia Pageviews | Ten daily observations for English Wikipedia's Saturn article | 6 |
| GBIF / eBird | Denmark house-sparrow occurrences and publisher attribution metadata | 6 |

Attributions, licence notes, official documentation and exact query URLs are recorded in `sources/manifest.json`. Preserve publisher attributions when redistributing. The pack makes no blanket licence claim over every upstream service.

## Relationship coverage

| Family | Tasks | Purpose |
|---|---:|---|
| Date ordering | 10 | Two observed dates with a strict chronological relationship |
| Identifier matching | 10 | Keep fields associated with the correct source record |
| Membership | 10 | Select a value actually present in approved source facts |
| Uniqueness | 10 | Select distinct source values without duplicates |
| Counts | 10 | Copy a scoped list and provide its exact length |
| Sums / products | 10 | Aggregate explicitly selected values; one product and nine sums |

Ordinary schemas already express some rules, including `uniqueItems`. These are useful controls, not evidence that new keywords are necessary. Source-derived `const` and `enum` constraints are also tested as an ordinary-schema replay comparator.

## Four approaches

| Approach | Prompt and runtime behavior |
|---|---|
| A — Ordinary schema | Original output schema, necessary trusted facts and exact task instructions; ordinary JSON Schema checks afterward. |
| B — FULL contract | FULL prompt and effective projected schema; complete contract validation afterward. |
| C — COMPACT contract | Compact prompt with the same trusted facts; complete contract validation afterward. |
| D — Selective calculations | C, but declared count/sum/product targets are omitted from the generation schema and computed in application code. Non-arithmetic D prompts exactly match C. |

A/B/C have the same final output shape and available source facts, although their presentation and validation differ. D intentionally changes the raw generation shape for 20 arithmetic tasks; score its assembled system output separately. A calculated field is not evidence that the model became better at arithmetic.

All task contexts use `confirmed: true` solely to mark source-verified benchmark context. No independent human or end-user approval is claimed. The full application contract remains outside the provider in COMPACT mode. All four arms use the same task facts, and evaluation answers stay outside all prompts and repair feedback.

## Freshness and independence

The exposure audit at HESchema commit `0bed2a57d22a8b1a70d015e05c404109a9509af5` examined 348 tracked research, benchmark and test files. It found no exact prompt or context matches for the final tasks and no selected source API URL hits in that scanned corpus. Earlier Crossref, PyPI, USGS, Citi Bike, WfCommons and other exposed collections were excluded.

This is a limited corpus audit, not proof that these records are absent from training data, deleted history or private experiments. An initial generic empty-list Rails context matched an old control; the delivered task binds the empty list to an actual release version. The empty-list pattern itself is not novel. See `EXPOSURE_AUDIT.json`.

These are fresh record adaptations for confirmation, but they share six main task shapes and sometimes source records. Repeats are not new tasks. Ten project clusters, including two biological archives and two package registries, limit generalization; do not describe them as 60 independent workflow designs.

## Before a live experiment

Use a separate engineering pilot on already exposed tasks or separate pilot records. Do not tune prompts, validators or retries on these 60 inputs. The supplied freeze records dataset bytes; availability, model IDs, generation settings, feedback renderer and pacing must be sealed after the separate engineering pilot and before inference on this pack.

The planned model IDs are `openai/gpt-oss-120b`, `openai/gpt-oss-20b` and `qwen/qwen3.8-27b`. Their availability has not been verified for this pack. A replacement must be documented before execution, with a newly sealed execution manifest. Planned generation uses temperature 0, prompt-only JSON, no provider schema enforcement, a 2,048-token output ceiling and one detector-triggered repair. Pilot-check whether that ceiling is appropriate before sealing it.

The existing repository's confirmation runner is tied to its older 30-task pack. This ZIP is not a claim that its existing CLI accepts the new inputs directly. Integrate a harness for `requests.jsonl` plus `schedule.json`, preserving the evidence and scoring rules in `README.md` and `PROTOCOL.json`.

## Interpretation and safeguards

- Measure independent task correctness before and after the allowed repair, wrong acceptance, correct rejection, and repair recovery by category. Only the runtime detector may trigger repair; the independent oracle must not supply feedback.
- Separate initial/repair input and output tokens, actual billing versus reference estimates, provider response time, local validation/calculation, evidence I/O, retry/rate-limit waits and total elapsed time.
- Preserve exact raw provider responses and usage before advancing result status. Missing evidence or usage stays explicitly missing. Do not replace a missing original response with a retry and call it the same attempt.
- Report denominators, missing slots, truncation and provider errors. Include results by model, project and family, paired differences and project-cluster uncertainty. Avoid claims based only on pooled repeats.
- Replay saved outputs through original schema, source-compiled ordinary schema, independent conventional application checks and HESchema checks. This replay is a validator comparison, not an additional end-to-end generation or repair arm.
- Keep caching off for independent repeats. D has 40 non-arithmetic controls with the same prompts as C, but they are separately scheduled calls. If running D only on 20 eligible tasks, declare the alternate 1,800-slot design before inference.
- Offline controls and compatibility checks establish engineering behavior only. They establish no model accuracy, token savings, latency improvement or necessity for new JSON Schema keywords.

## Source-specific cautions

EONET observation dates do not necessarily stay within the query's event-selection interval and are not exact event lifetime bounds. Open Library dates are catalogue creation/update dates, not publication dates; missing page counts are excluded, not zero. Kysely releases are ordered by publication timestamp, not lexical version order. Rails dates use publication metadata, not historical archive build timestamps; downloads are events, not people. Treasury sums retain the original reported units and exclude subtotals and year/month cumulative fields. World Bank sums cover only the specified countries. Wikimedia pageviews are not unique visitors. GBIF reported counts are not distinct bird identities or population estimates; missing counts are excluded, not zero. Selected eBird occurrence and dataset metadata both report CC BY 4.0.

## Task index

| ID | Project | Family | Task | Application calculation |
|---|---|---|---|---|
| H60-01 | NASA EONET | Date ordering | Select an observation interval for Tropical Cyclone Kevin | D = C |
| H60-02 | NASA EONET | Date ordering | Select an observation interval for Tropical Cyclone Judy | D = C |
| H60-03 | NASA EONET | Identifier matching | Resolve an EONET event without mixing its title and status | D = C |
| H60-04 | NASA EONET | List membership | Choose a registered source for Tropical Cyclone Kevin | D = C |
| H60-05 | NASA EONET | Uniqueness | Choose two distinct event information sources | D = C |
| H60-06 | NASA EONET | Counts | Copy and count an actual cyclone geometry series | Eligible |
| H60-07 | RCSB PDB | Date ordering | Choose a valid crambin archive-history interval | D = C |
| H60-08 | RCSB PDB | Identifier matching | Associate a PDB ID with its own experimental metadata | D = C |
| H60-09 | RCSB PDB | List membership | Select an existing 4HHB polymer entity | D = C |
| H60-10 | RCSB PDB | Uniqueness | Select two different structures for a structure viewer | D = C |
| H60-11 | RCSB PDB | Counts | Count the entity IDs in the 4HHB manifest | Eligible |
| H60-12 | RCSB PDB | Sums / products | Reconcile deposited DNA monomers in 1BNA | Eligible |
| H60-13 | UniProt | Date ordering | Order the audit dates of an E. coli protein entry | D = C |
| H60-14 | UniProt | Identifier matching | Keep protein accession, mnemonic and length associated | D = C |
| H60-15 | UniProt | List membership | Choose a keyword attached to the selected protein | D = C |
| H60-16 | UniProt | Uniqueness | Choose two different protein accessions | D = C |
| H60-17 | UniProt | Counts | Preserve and count a protein keyword annotation list | Eligible |
| H60-18 | UniProt | Sums / products | Total residues across six downloaded protein sequences | Eligible |
| H60-19 | Open Library | Date ordering | Order the creation and update dates of a catalogue entry | D = C |
| H60-20 | Open Library | Identifier matching | Match the exact edition key to its multilingual title | D = C |
| H60-21 | Open Library | List membership | Choose an actual source reference for a book edition | D = C |
| H60-22 | Open Library | Uniqueness | Choose two distinct catalogue edition keys | D = C |
| H60-23 | Open Library | Counts | Count catalogue source references without dropping entries | Eligible |
| H60-24 | Open Library | Sums / products | Aggregate only edition records with reported page counts | Eligible |
| H60-25 | Kysely / npm | Date ordering | Choose a chronological interval in Kysely release history | D = C |
| H60-26 | Kysely / npm | Identifier matching | Match a published version to its own integrity metadata | D = C |
| H60-27 | Kysely / npm | List membership | Choose a declared development dependency | D = C |
| H60-28 | Kysely / npm | Uniqueness | Choose two different published stable versions | D = C |
| H60-29 | Kysely / npm | Counts | Count the actual development-dependency names | Eligible |
| H60-30 | Kysely / npm | Sums / products | Total unpacked bytes across six published release artifacts | Eligible |
| H60-31 | Rails / RubyGems | Date ordering | Choose a Rails publication interval | D = C |
| H60-32 | Rails / RubyGems | Identifier matching | Match a Rails version to its platform and archive hash | D = C |
| H60-33 | Rails / RubyGems | List membership | Select a published non-prerelease Rails version | D = C |
| H60-34 | Rails / RubyGems | Uniqueness | Choose two distinct Rails release archive hashes | D = C |
| H60-35 | Rails / RubyGems | Counts | Preserve a real empty requirements list | Eligible |
| H60-36 | Rails / RubyGems | Sums / products | Aggregate recorded downloads of six selected Rails versions | Eligible |
| H60-37 | U.S. Treasury DTS | Date ordering | Choose a valid Treasury reporting interval | D = C |
| H60-38 | U.S. Treasury DTS | Identifier matching | Match a source line within a specified daily statement | D = C |
| H60-39 | U.S. Treasury DTS | List membership | Choose a transaction type actually present in the query | D = C |
| H60-40 | U.S. Treasury DTS | Uniqueness | Select two different reported deposit categories | D = C |
| H60-41 | U.S. Treasury DTS | Counts | Copy and count a scoped deposit-category excerpt | Eligible |
| H60-42 | U.S. Treasury DTS | Sums / products | Sum one deposit category over seven reporting dates | Eligible |
| H60-43 | World Bank WDI | Identifier matching | Associate a country code with its own population observation | D = C |
| H60-44 | World Bank WDI | List membership | Select a country code available in the frozen extract | D = C |
| H60-45 | World Bank WDI | Uniqueness | Choose two distinct countries for a comparison | D = C |
| H60-46 | World Bank WDI | Counts | Count the actual observations in a fixed WDI response | Eligible |
| H60-47 | World Bank WDI | Sums / products | Aggregate selected 2020 populations: BGD, IND, LKA | Eligible |
| H60-48 | World Bank WDI | Sums / products | Aggregate selected 2020 populations: BTN, MDV, NPL | Eligible |
| H60-49 | Wikimedia Pageviews | Date ordering | Choose an observed UTC pageview reporting interval | D = C |
| H60-50 | Wikimedia Pageviews | Date ordering | Choose an observed UTC pageview reporting interval | D = C |
| H60-51 | Wikimedia Pageviews | Identifier matching | Keep a pageview date associated with its own view count | D = C |
| H60-52 | Wikimedia Pageviews | List membership | Choose an available source reporting timestamp | D = C |
| H60-53 | Wikimedia Pageviews | Uniqueness | Select two different daily reporting rows | D = C |
| H60-54 | Wikimedia Pageviews | Sums / products | Total the captured ten-day pageviews | Eligible |
| H60-55 | GBIF | Identifier matching | Keep a GBIF occurrence key associated with its own record | D = C |
| H60-56 | GBIF | List membership | Choose an observed basisOfRecord value | D = C |
| H60-57 | GBIF | Uniqueness | Choose two distinct GBIF occurrence records | D = C |
| H60-58 | GBIF | Counts | Count a scoped occurrence-record batch | Eligible |
| H60-59 | GBIF | Counts | Preserve and count an actual taxonomic classification path | Eligible |
| H60-60 | GBIF | Sums / products | Sum only reported individualCount values in selected observations | Eligible |

## Complete task inputs

The expected example is one valid answer, not an instruction to require that exact answer when alternatives satisfy the rules. Full alternatives and evaluator code are in the ZIP. Do not include this expected-answer section in model requests.

### H60-01 — Select an observation interval for Tropical Cyclone Kevin

Project: **NASA EONET** · Family: **Date ordering** · Valid answer alternatives: **10**

**Exact task prompt**

For EONET event EONET_6329 (Tropical Cyclone Kevin), select any two distinct provided observation calendar dates. Return start and end with start strictly before end. These are sampled observation days, not an assertion of the event's exact start or end. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [eonet](https://eonet.gsfc.nasa.gov/api/v3/events?status=closed&start=2023-01-01&end=2023-03-01&limit=20) — saved `sources/raw/eonet.json`; SHA-256 `fe77e4fe12918cb2856e0dd09b696e8244d8b2f471521d7a4ff283fd172e27a9`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "2023-03-01",
    "2023-03-02",
    "2023-03-03",
    "2023-03-04",
    "2023-03-05"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-01",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Select an observation interval for Tropical Cyclone Kevin",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "2023-03-01",
  "end": "2023-03-02"
}
```

### H60-02 — Select an observation interval for Tropical Cyclone Judy

Project: **NASA EONET** · Family: **Date ordering** · Valid answer alternatives: **10**

**Exact task prompt**

For EONET event EONET_6328 (Tropical Cyclone Judy), select any two distinct provided observation calendar dates. Return start and end with start strictly before end. These are sampled observation days, not an assertion of the event's exact start or end. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [eonet](https://eonet.gsfc.nasa.gov/api/v3/events?status=closed&start=2023-01-01&end=2023-03-01&limit=20) — saved `sources/raw/eonet.json`; SHA-256 `fe77e4fe12918cb2856e0dd09b696e8244d8b2f471521d7a4ff283fd172e27a9`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "2023-02-27",
    "2023-02-28",
    "2023-03-01",
    "2023-03-02",
    "2023-03-03"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-02",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Select an observation interval for Tropical Cyclone Judy",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "2023-02-27",
  "end": "2023-02-28"
}
```

### H60-03 — Resolve an EONET event without mixing its title and status

Project: **NASA EONET** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Find the supplied catalogue record whose event ID is EONET_6327. Return requestedId and that complete candidate record. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [eonet](https://eonet.gsfc.nasa.gov/api/v3/events?status=closed&start=2023-01-01&end=2023-03-01&limit=20) — saved `sources/raw/eonet.json`; SHA-256 `fe77e4fe12918cb2856e0dd09b696e8244d8b2f471521d7a4ff283fd172e27a9`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": "EONET_6327",
  "candidates": [
    {
      "id": "EONET_5389",
      "title": "Iceberg D29C",
      "closed": "2024-03-29T00:00:00Z"
    },
    {
      "id": "EONET_6329",
      "title": "Tropical Cyclone Kevin",
      "closed": "2023-03-10T00:00:00Z"
    },
    {
      "id": "EONET_6327",
      "title": "Tropical Cyclone Enala",
      "closed": "2023-03-05T00:00:00Z"
    },
    {
      "id": "EONET_6328",
      "title": "Tropical Cyclone Judy",
      "closed": "2023-03-08T00:00:00Z"
    },
    {
      "id": "EONET_6330",
      "title": "Iceberg A80D",
      "closed": "2024-10-25T00:00:00Z"
    },
    {
      "id": "EONET_4125",
      "title": "Iceberg B15AB",
      "closed": "2026-03-13T00:00:00Z"
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-03",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string",
        "const": "EONET_6327"
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "closed": {
            "type": "string"
          }
        },
        "required": [
          "id",
          "title",
          "closed"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Resolve an EONET event without mixing its title and status",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "closed": {
              "type": "string"
            },
            "id": {
              "type": "string"
            },
            "title": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "title",
            "closed"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/2"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": "EONET_6327",
  "record": {
    "id": "EONET_6327",
    "title": "Tropical Cyclone Enala",
    "closed": "2023-03-05T00:00:00Z"
  }
}
```

### H60-04 — Choose a registered source for Tropical Cyclone Kevin

Project: **NASA EONET** · Family: **List membership** · Valid answer alternatives: **2**

**Exact task prompt**

Select any source identifier actually attached to the supplied EONET_6329 event. Return selected; do not substitute another weather agency. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [eonet](https://eonet.gsfc.nasa.gov/api/v3/events?status=closed&start=2023-01-01&end=2023-03-01&limit=20) — saved `sources/raw/eonet.json`; SHA-256 `fe77e4fe12918cb2856e0dd09b696e8244d8b2f471521d7a4ff283fd172e27a9`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "GDACS",
    "JTWC"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-04",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose a registered source for Tropical Cyclone Kevin",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "GDACS"
}
```

### H60-05 — Choose two distinct event information sources

Project: **NASA EONET** · Family: **Uniqueness** · Valid answer alternatives: **12**

**Exact task prompt**

Return records containing exactly two different source IDs selected from the supplied actual event-source references. Each record has only id; repeated source references must not become duplicate output IDs. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [eonet](https://eonet.gsfc.nasa.gov/api/v3/events?status=closed&start=2023-01-01&end=2023-03-01&limit=20) — saved `sources/raw/eonet.json`; SHA-256 `fe77e4fe12918cb2856e0dd09b696e8244d8b2f471521d7a4ff283fd172e27a9`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    "GDACS",
    "JTWC",
    "GDACS",
    "JTWC",
    "NATICE",
    "NATICE",
    "NATICE",
    "SIVolcano",
    "GDACS",
    "JTWC"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-05",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose two distinct event information sources",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": "GDACS"
    },
    {
      "id": "JTWC"
    }
  ]
}
```

### H60-06 — Copy and count an actual cyclone geometry series

Project: **NASA EONET** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy every supplied EONET_6329 observation into items, preserving order and each observedAt value, then set count to the number of observations. The supplied items are the complete saved geometry-date series for this event. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [eonet](https://eonet.gsfc.nasa.gov/api/v3/events?status=closed&start=2023-01-01&end=2023-03-01&limit=20) — saved `sources/raw/eonet.json`; SHA-256 `fe77e4fe12918cb2856e0dd09b696e8244d8b2f471521d7a4ff283fd172e27a9`.

**Trusted facts sent to every arm**

```json
{
  "items": [
    {
      "observedAt": "2023-03-01T18:00:00Z"
    },
    {
      "observedAt": "2023-03-02T00:00:00Z"
    },
    {
      "observedAt": "2023-03-02T06:00:00Z"
    },
    {
      "observedAt": "2023-03-02T12:00:00Z"
    },
    {
      "observedAt": "2023-03-02T18:00:00Z"
    },
    {
      "observedAt": "2023-03-03T00:00:00Z"
    },
    {
      "observedAt": "2023-03-03T06:00:00Z"
    },
    {
      "observedAt": "2023-03-03T12:00:00Z"
    },
    {
      "observedAt": "2023-03-03T18:00:00Z"
    },
    {
      "observedAt": "2023-03-04T00:00:00Z"
    },
    {
      "observedAt": "2023-03-04T06:00:00Z"
    },
    {
      "observedAt": "2023-03-04T12:00:00Z"
    },
    {
      "observedAt": "2023-03-04T18:00:00Z"
    },
    {
      "observedAt": "2023-03-05T00:00:00Z"
    },
    {
      "observedAt": "2023-03-05T06:00:00Z"
    },
    {
      "observedAt": "2023-03-05T12:00:00Z"
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-06",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "observedAt": {
              "type": "string"
            }
          },
          "required": [
            "observedAt"
          ],
          "type": "object"
        }
      },
      "count": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [
      "items",
      "count"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Copy and count an actual cyclone geometry series",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "observedAt": {
              "type": "string"
            }
          },
          "required": [
            "observedAt"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "items"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [
    {
      "observedAt": "2023-03-01T18:00:00Z"
    },
    {
      "observedAt": "2023-03-02T00:00:00Z"
    },
    {
      "observedAt": "2023-03-02T06:00:00Z"
    },
    {
      "observedAt": "2023-03-02T12:00:00Z"
    },
    {
      "observedAt": "2023-03-02T18:00:00Z"
    },
    {
      "observedAt": "2023-03-03T00:00:00Z"
    },
    {
      "observedAt": "2023-03-03T06:00:00Z"
    },
    {
      "observedAt": "2023-03-03T12:00:00Z"
    },
    {
      "observedAt": "2023-03-03T18:00:00Z"
    },
    {
      "observedAt": "2023-03-04T00:00:00Z"
    },
    {
      "observedAt": "2023-03-04T06:00:00Z"
    },
    {
      "observedAt": "2023-03-04T12:00:00Z"
    },
    {
      "observedAt": "2023-03-04T18:00:00Z"
    },
    {
      "observedAt": "2023-03-05T00:00:00Z"
    },
    {
      "observedAt": "2023-03-05T06:00:00Z"
    },
    {
      "observedAt": "2023-03-05T12:00:00Z"
    }
  ],
  "count": 16
}
```

### H60-07 — Choose a valid crambin archive-history interval

Project: **RCSB PDB** · Family: **Date ordering** · Valid answer alternatives: **3**

**Exact task prompt**

For PDB 1CRN, choose any two distinct supplied archive-history calendar dates, returning start strictly before end. Deposition, first release and revision are different archive events. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [pdb-1CRN](https://data.rcsb.org/rest/v1/core/entry/1CRN) — saved `sources/raw/pdb-1CRN.json`; SHA-256 `9bc483a29663a13833e4e872093a376ed09e34d1ebe97c1f1e897416251b5542`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "1981-04-30",
    "1981-07-28",
    "2024-10-30"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-07",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose a valid crambin archive-history interval",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "1981-04-30",
  "end": "1981-07-28"
}
```

### H60-08 — Associate a PDB ID with its own experimental metadata

Project: **RCSB PDB** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Find PDB entry 4HHB among the supplied candidates. Return requestedId and the entire matching record, without borrowing another structure's atom count or experimental method. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [pdb-4HHB](https://data.rcsb.org/rest/v1/core/entry/4HHB) — saved `sources/raw/pdb-4HHB.json`; SHA-256 `a95a79421b90211667e08cc21555acb6e2c384fe882bb7c9b174eadb4e9fdb1a`.
- [pdb-1CRN](https://data.rcsb.org/rest/v1/core/entry/1CRN) — saved `sources/raw/pdb-1CRN.json`; SHA-256 `9bc483a29663a13833e4e872093a376ed09e34d1ebe97c1f1e897416251b5542`.
- [pdb-1UBQ](https://data.rcsb.org/rest/v1/core/entry/1UBQ) — saved `sources/raw/pdb-1UBQ.json`; SHA-256 `ae6dffdc03b6e2b7873f76409fe1727970b25640c367ec62e3de4e9b8a158f1f`.
- [pdb-1BNA](https://data.rcsb.org/rest/v1/core/entry/1BNA) — saved `sources/raw/pdb-1BNA.json`; SHA-256 `fbc0fbc995c879dd08ade56d6d866a5f65f88cf99fa7b169eee7af1d404fcc55`.
- [pdb-1A3N](https://data.rcsb.org/rest/v1/core/entry/1A3N) — saved `sources/raw/pdb-1A3N.json`; SHA-256 `00155895e52d2101801362c4ef13d1d5e730602ed3156324c7e2dd9e1ede313c`.
- [pdb-1MBO](https://data.rcsb.org/rest/v1/core/entry/1MBO) — saved `sources/raw/pdb-1MBO.json`; SHA-256 `c860a6b684579dd73cbe0f00d983b9c1aa234c3c6292e1e9eb6426d573c7d0df`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": "4HHB",
  "candidates": [
    {
      "id": "1CRN",
      "method": "X-RAY DIFFRACTION",
      "atomCount": 327
    },
    {
      "id": "1UBQ",
      "method": "X-RAY DIFFRACTION",
      "atomCount": 660
    },
    {
      "id": "1BNA",
      "method": "X-RAY DIFFRACTION",
      "atomCount": 566
    },
    {
      "id": "4HHB",
      "method": "X-RAY DIFFRACTION",
      "atomCount": 4779
    },
    {
      "id": "1A3N",
      "method": "X-RAY DIFFRACTION",
      "atomCount": 4997
    },
    {
      "id": "1MBO",
      "method": "X-RAY DIFFRACTION",
      "atomCount": 1611
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-08",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string",
        "const": "4HHB"
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "method": {
            "type": "string"
          },
          "atomCount": {
            "type": "integer"
          }
        },
        "required": [
          "id",
          "method",
          "atomCount"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Associate a PDB ID with its own experimental metadata",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "atomCount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            },
            "method": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "method",
            "atomCount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/3"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": "4HHB",
  "record": {
    "id": "4HHB",
    "method": "X-RAY DIFFRACTION",
    "atomCount": 4779
  }
}
```

### H60-09 — Select an existing 4HHB polymer entity

Project: **RCSB PDB** · Family: **List membership** · Valid answer alternatives: **2**

**Exact task prompt**

Return selected as any polymer entity ID explicitly listed for PDB 4HHB. Entity IDs are local to that structure; do not choose a non-polymer entity. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [pdb-4HHB](https://data.rcsb.org/rest/v1/core/entry/4HHB) — saved `sources/raw/pdb-4HHB.json`; SHA-256 `a95a79421b90211667e08cc21555acb6e2c384fe882bb7c9b174eadb4e9fdb1a`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "1",
    "2"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-09",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Select an existing 4HHB polymer entity",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "1"
}
```

### H60-10 — Select two different structures for a structure viewer

Project: **RCSB PDB** · Family: **Uniqueness** · Valid answer alternatives: **30**

**Exact task prompt**

Return exactly two records with distinct id values chosen from the supplied PDB entry IDs. Both orders are acceptable; do not duplicate a structure. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [pdb-1CRN](https://data.rcsb.org/rest/v1/core/entry/1CRN) — saved `sources/raw/pdb-1CRN.json`; SHA-256 `9bc483a29663a13833e4e872093a376ed09e34d1ebe97c1f1e897416251b5542`.
- [pdb-1UBQ](https://data.rcsb.org/rest/v1/core/entry/1UBQ) — saved `sources/raw/pdb-1UBQ.json`; SHA-256 `ae6dffdc03b6e2b7873f76409fe1727970b25640c367ec62e3de4e9b8a158f1f`.
- [pdb-1BNA](https://data.rcsb.org/rest/v1/core/entry/1BNA) — saved `sources/raw/pdb-1BNA.json`; SHA-256 `fbc0fbc995c879dd08ade56d6d866a5f65f88cf99fa7b169eee7af1d404fcc55`.
- [pdb-4HHB](https://data.rcsb.org/rest/v1/core/entry/4HHB) — saved `sources/raw/pdb-4HHB.json`; SHA-256 `a95a79421b90211667e08cc21555acb6e2c384fe882bb7c9b174eadb4e9fdb1a`.
- [pdb-1A3N](https://data.rcsb.org/rest/v1/core/entry/1A3N) — saved `sources/raw/pdb-1A3N.json`; SHA-256 `00155895e52d2101801362c4ef13d1d5e730602ed3156324c7e2dd9e1ede313c`.
- [pdb-1MBO](https://data.rcsb.org/rest/v1/core/entry/1MBO) — saved `sources/raw/pdb-1MBO.json`; SHA-256 `c860a6b684579dd73cbe0f00d983b9c1aa234c3c6292e1e9eb6426d573c7d0df`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    "1CRN",
    "1UBQ",
    "1BNA",
    "4HHB",
    "1A3N",
    "1MBO"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-10",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Select two different structures for a structure viewer",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": "1CRN"
    },
    {
      "id": "1UBQ"
    }
  ]
}
```

### H60-11 — Count the entity IDs in the 4HHB manifest

Project: **RCSB PDB** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy all supplied 4HHB entity IDs into items in order, then return count. Include polymer, non-polymer and solvent entity IDs that appear in this saved manifest. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [pdb-4HHB](https://data.rcsb.org/rest/v1/core/entry/4HHB) — saved `sources/raw/pdb-4HHB.json`; SHA-256 `a95a79421b90211667e08cc21555acb6e2c384fe882bb7c9b174eadb4e9fdb1a`.

**Trusted facts sent to every arm**

```json
{
  "items": [
    "1",
    "2",
    "3",
    "4",
    "5"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-11",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "count": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [
      "items",
      "count"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Count the entity IDs in the 4HHB manifest",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "items"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [
    "1",
    "2",
    "3",
    "4",
    "5"
  ],
  "count": 5
}
```

**Independent publisher aggregate cross-check**

```json
{
  "sourceId": "pdb-4HHB",
  "sourcePointer": "/rcsb_entry_info/entity_count",
  "outputField": "count"
}
```

### H60-12 — Reconcile deposited DNA monomers in 1BNA

Project: **RCSB PDB** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

For PDB 1BNA, copy copies and perCopy from the supplied deposited polymer-instance count and monomers-per-chain value. Return total as copies multiplied by perCopy. This record has one polymer entity type and equal minimum/maximum chain lengths. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [pdb-1BNA](https://data.rcsb.org/rest/v1/core/entry/1BNA) — saved `sources/raw/pdb-1BNA.json`; SHA-256 `fbc0fbc995c879dd08ade56d6d866a5f65f88cf99fa7b169eee7af1d404fcc55`.

**Trusted facts sent to every arm**

```json
{
  "copies": 2,
  "perCopy": 12
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-12",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "copies": {
        "type": "integer"
      },
      "perCopy": {
        "type": "integer"
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "copies",
      "perCopy",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Reconcile deposited DNA monomers in 1BNA",
  "contextSchema": {
    "type": "object",
    "properties": {
      "copies": {
        "type": "integer"
      },
      "perCopy": {
        "type": "integer"
      }
    },
    "required": [
      "copies",
      "perCopy"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/copies",
      "contextLocation": "/copies"
    },
    {
      "instanceLocation": "/perCopy",
      "contextLocation": "/perCopy"
    }
  ],
  "relationships": [
    {
      "id": "exact-product",
      "kind": "product_equals",
      "target": "/total",
      "operands": [
        "/copies",
        "/perCopy"
      ]
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-product",
    "kind": "product_equals",
    "target": "/total",
    "operands": [
      "/copies",
      "/perCopy"
    ],
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "copies": 2,
  "perCopy": 12,
  "total": 24
}
```

**Independent publisher aggregate cross-check**

```json
{
  "sourceId": "pdb-1BNA",
  "sourcePointer": "/rcsb_entry_info/deposited_polymer_monomer_count",
  "outputField": "total"
}
```

### H60-13 — Order the audit dates of an E. coli protein entry

Project: **UniProt** · Family: **Date ordering** · Valid answer alternatives: **3**

**Exact task prompt**

For UniProt P0A7V0, select two distinct supplied audit dates and return start strictly before end. These dates describe the entry audit, not the organism's lifetime. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [uniprot-P0A7V0](https://rest.uniprot.org/uniprotkb/P0A7V0.json) — saved `sources/raw/uniprot-P0A7V0.json`; SHA-256 `8091209174d12b5a31374f907c9afb7e2ee1aa8aab3844ebdd3c2a70066005a7`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "1986-07-21",
    "2007-01-23",
    "2026-09-02"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-13",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Order the audit dates of an E. coli protein entry",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "1986-07-21",
  "end": "2007-01-23"
}
```

### H60-14 — Keep protein accession, mnemonic and length associated

Project: **UniProt** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Resolve accession P0A7W1 among the candidates. Return requestedId and its complete matching record; preserve the mnemonic, taxonId and sequenceLength belonging to that accession. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [uniprot-P0A7W1](https://rest.uniprot.org/uniprotkb/P0A7W1.json) — saved `sources/raw/uniprot-P0A7W1.json`; SHA-256 `610cfd978f4d645e545ad2fccf75ab76ad946377e5a7073e6f13ca8f133723f9`.
- [uniprot-P0A7V0](https://rest.uniprot.org/uniprotkb/P0A7V0.json) — saved `sources/raw/uniprot-P0A7V0.json`; SHA-256 `8091209174d12b5a31374f907c9afb7e2ee1aa8aab3844ebdd3c2a70066005a7`.
- [uniprot-P0A7U7](https://rest.uniprot.org/uniprotkb/P0A7U7.json) — saved `sources/raw/uniprot-P0A7U7.json`; SHA-256 `25ff3217b5a151fb008ab5b100b1b1fddf7718f94f6da9169c7655ae3807133f`.
- [uniprot-P0A7V8](https://rest.uniprot.org/uniprotkb/P0A7V8.json) — saved `sources/raw/uniprot-P0A7V8.json`; SHA-256 `96c13dcbe6b59dd7e2a0c3cec859f8e7440649b2e20f1255332a005102db8b0e`.
- [uniprot-P0A7T3](https://rest.uniprot.org/uniprotkb/P0A7T3.json) — saved `sources/raw/uniprot-P0A7T3.json`; SHA-256 `f332065d4bb67233ccbba854acf5a44ca3b925dca51e92e09d0d49d67e6889ce`.
- [uniprot-P0A7S9](https://rest.uniprot.org/uniprotkb/P0A7S9.json) — saved `sources/raw/uniprot-P0A7S9.json`; SHA-256 `7ea9992309fac544acd16ec0a96d613d0d319d594bab533c22b5feccea1d79e9`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": "P0A7W1",
  "candidates": [
    {
      "id": "P0A7V0",
      "mnemonic": "RS2_ECOLI",
      "taxonId": 83333,
      "sequenceLength": 241
    },
    {
      "id": "P0A7U7",
      "mnemonic": "RS20_ECOLI",
      "taxonId": 83333,
      "sequenceLength": 87
    },
    {
      "id": "P0A7W1",
      "mnemonic": "RS5_ECOLI",
      "taxonId": 83333,
      "sequenceLength": 167
    },
    {
      "id": "P0A7V8",
      "mnemonic": "RS4_ECOLI",
      "taxonId": 83333,
      "sequenceLength": 206
    },
    {
      "id": "P0A7T3",
      "mnemonic": "RS16_ECOLI",
      "taxonId": 83333,
      "sequenceLength": 82
    },
    {
      "id": "P0A7S9",
      "mnemonic": "RS13_ECOLI",
      "taxonId": 83333,
      "sequenceLength": 118
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-14",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string",
        "const": "P0A7W1"
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "mnemonic": {
            "type": "string"
          },
          "taxonId": {
            "type": "integer"
          },
          "sequenceLength": {
            "type": "integer"
          }
        },
        "required": [
          "id",
          "mnemonic",
          "taxonId",
          "sequenceLength"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Keep protein accession, mnemonic and length associated",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "id": {
              "type": "string"
            },
            "mnemonic": {
              "type": "string"
            },
            "sequenceLength": {
              "type": "integer"
            },
            "taxonId": {
              "type": "integer"
            }
          },
          "required": [
            "id",
            "mnemonic",
            "taxonId",
            "sequenceLength"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/2"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": "P0A7W1",
  "record": {
    "id": "P0A7W1",
    "mnemonic": "RS5_ECOLI",
    "taxonId": 83333,
    "sequenceLength": 167
  }
}
```

### H60-15 — Choose a keyword attached to the selected protein

Project: **UniProt** · Family: **List membership** · Valid answer alternatives: **5**

**Exact task prompt**

Return selected as any keyword ID actually attached to UniProt P0A7V0 in the supplied annotation snapshot. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [uniprot-P0A7V0](https://rest.uniprot.org/uniprotkb/P0A7V0.json) — saved `sources/raw/uniprot-P0A7V0.json`; SHA-256 `8091209174d12b5a31374f907c9afb7e2ee1aa8aab3844ebdd3c2a70066005a7`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "KW-0002",
    "KW-0903",
    "KW-1185",
    "KW-0687",
    "KW-0689"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-15",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose a keyword attached to the selected protein",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "KW-0002"
}
```

### H60-16 — Choose two different protein accessions

Project: **UniProt** · Family: **Uniqueness** · Valid answer alternatives: **30**

**Exact task prompt**

Return records with exactly two distinct id values chosen from the supplied UniProt accessions. Do not duplicate an accession, even though the proteins share an organism. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [uniprot-P0A7V0](https://rest.uniprot.org/uniprotkb/P0A7V0.json) — saved `sources/raw/uniprot-P0A7V0.json`; SHA-256 `8091209174d12b5a31374f907c9afb7e2ee1aa8aab3844ebdd3c2a70066005a7`.
- [uniprot-P0A7U7](https://rest.uniprot.org/uniprotkb/P0A7U7.json) — saved `sources/raw/uniprot-P0A7U7.json`; SHA-256 `25ff3217b5a151fb008ab5b100b1b1fddf7718f94f6da9169c7655ae3807133f`.
- [uniprot-P0A7W1](https://rest.uniprot.org/uniprotkb/P0A7W1.json) — saved `sources/raw/uniprot-P0A7W1.json`; SHA-256 `610cfd978f4d645e545ad2fccf75ab76ad946377e5a7073e6f13ca8f133723f9`.
- [uniprot-P0A7V8](https://rest.uniprot.org/uniprotkb/P0A7V8.json) — saved `sources/raw/uniprot-P0A7V8.json`; SHA-256 `96c13dcbe6b59dd7e2a0c3cec859f8e7440649b2e20f1255332a005102db8b0e`.
- [uniprot-P0A7T3](https://rest.uniprot.org/uniprotkb/P0A7T3.json) — saved `sources/raw/uniprot-P0A7T3.json`; SHA-256 `f332065d4bb67233ccbba854acf5a44ca3b925dca51e92e09d0d49d67e6889ce`.
- [uniprot-P0A7S9](https://rest.uniprot.org/uniprotkb/P0A7S9.json) — saved `sources/raw/uniprot-P0A7S9.json`; SHA-256 `7ea9992309fac544acd16ec0a96d613d0d319d594bab533c22b5feccea1d79e9`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    "P0A7V0",
    "P0A7U7",
    "P0A7W1",
    "P0A7V8",
    "P0A7T3",
    "P0A7S9"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-16",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose two different protein accessions",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": "P0A7V0"
    },
    {
      "id": "P0A7U7"
    }
  ]
}
```

### H60-17 — Preserve and count a protein keyword annotation list

Project: **UniProt** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy every supplied keyword annotation for P0A7V0 into items without changing its id, name or category. Return count equal to the full list length. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [uniprot-P0A7V0](https://rest.uniprot.org/uniprotkb/P0A7V0.json) — saved `sources/raw/uniprot-P0A7V0.json`; SHA-256 `8091209174d12b5a31374f907c9afb7e2ee1aa8aab3844ebdd3c2a70066005a7`.

**Trusted facts sent to every arm**

```json
{
  "items": [
    {
      "id": "KW-0002",
      "category": "Technical term",
      "name": "3D-structure"
    },
    {
      "id": "KW-0903",
      "category": "Technical term",
      "name": "Direct protein sequencing"
    },
    {
      "id": "KW-1185",
      "category": "Technical term",
      "name": "Reference proteome"
    },
    {
      "id": "KW-0687",
      "category": "Molecular function",
      "name": "Ribonucleoprotein"
    },
    {
      "id": "KW-0689",
      "category": "Molecular function",
      "name": "Ribosomal protein"
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-17",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "category": {
              "type": "string"
            },
            "id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "category",
            "name"
          ],
          "type": "object"
        }
      },
      "count": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [
      "items",
      "count"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Preserve and count a protein keyword annotation list",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "category": {
              "type": "string"
            },
            "id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "category",
            "name"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "items"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [
    {
      "id": "KW-0002",
      "category": "Technical term",
      "name": "3D-structure"
    },
    {
      "id": "KW-0903",
      "category": "Technical term",
      "name": "Direct protein sequencing"
    },
    {
      "id": "KW-1185",
      "category": "Technical term",
      "name": "Reference proteome"
    },
    {
      "id": "KW-0687",
      "category": "Molecular function",
      "name": "Ribonucleoprotein"
    },
    {
      "id": "KW-0689",
      "category": "Molecular function",
      "name": "Ribosomal protein"
    }
  ],
  "count": 5
}
```

### H60-18 — Total residues across six downloaded protein sequences

Project: **UniProt** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

Copy rows containing each accession and its reported sequence length as amount. Return total as the sum of those six lengths, in amino-acid residues. This is a combined sequence-size total, not a molecular-weight calculation. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [uniprot-P0A7V0](https://rest.uniprot.org/uniprotkb/P0A7V0.json) — saved `sources/raw/uniprot-P0A7V0.json`; SHA-256 `8091209174d12b5a31374f907c9afb7e2ee1aa8aab3844ebdd3c2a70066005a7`.
- [uniprot-P0A7U7](https://rest.uniprot.org/uniprotkb/P0A7U7.json) — saved `sources/raw/uniprot-P0A7U7.json`; SHA-256 `25ff3217b5a151fb008ab5b100b1b1fddf7718f94f6da9169c7655ae3807133f`.
- [uniprot-P0A7W1](https://rest.uniprot.org/uniprotkb/P0A7W1.json) — saved `sources/raw/uniprot-P0A7W1.json`; SHA-256 `610cfd978f4d645e545ad2fccf75ab76ad946377e5a7073e6f13ca8f133723f9`.
- [uniprot-P0A7V8](https://rest.uniprot.org/uniprotkb/P0A7V8.json) — saved `sources/raw/uniprot-P0A7V8.json`; SHA-256 `96c13dcbe6b59dd7e2a0c3cec859f8e7440649b2e20f1255332a005102db8b0e`.
- [uniprot-P0A7T3](https://rest.uniprot.org/uniprotkb/P0A7T3.json) — saved `sources/raw/uniprot-P0A7T3.json`; SHA-256 `f332065d4bb67233ccbba854acf5a44ca3b925dca51e92e09d0d49d67e6889ce`.
- [uniprot-P0A7S9](https://rest.uniprot.org/uniprotkb/P0A7S9.json) — saved `sources/raw/uniprot-P0A7S9.json`; SHA-256 `7ea9992309fac544acd16ec0a96d613d0d319d594bab533c22b5feccea1d79e9`.

**Trusted facts sent to every arm**

```json
{
  "rows": [
    {
      "id": "P0A7V0",
      "amount": 241
    },
    {
      "id": "P0A7U7",
      "amount": 87
    },
    {
      "id": "P0A7W1",
      "amount": 167
    },
    {
      "id": "P0A7V8",
      "amount": 206
    },
    {
      "id": "P0A7T3",
      "amount": 82
    },
    {
      "id": "P0A7S9",
      "amount": 118
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-18",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "rows",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Total residues across six downloaded protein sequences",
  "contextSchema": {
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "rows"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/rows",
      "contextLocation": "/rows"
    }
  ],
  "relationships": [
    {
      "id": "exact-sum",
      "kind": "sum_items_equals",
      "target": "/total",
      "arrayLocation": "/rows",
      "itemLocation": "/amount"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-sum",
    "kind": "sum_items_equals",
    "target": "/total",
    "arrayLocation": "/rows",
    "itemLocation": "/amount",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "rows": [
    {
      "id": "P0A7V0",
      "amount": 241
    },
    {
      "id": "P0A7U7",
      "amount": 87
    },
    {
      "id": "P0A7W1",
      "amount": 167
    },
    {
      "id": "P0A7V8",
      "amount": 206
    },
    {
      "id": "P0A7T3",
      "amount": 82
    },
    {
      "id": "P0A7S9",
      "amount": 118
    }
  ],
  "total": 901
}
```

### H60-19 — Order the creation and update dates of a catalogue entry

Project: **Open Library** · Family: **Date ordering** · Valid answer alternatives: **1**

**Exact task prompt**

For edition OL7353617M, choose its earlier and later supplied catalogue-history days as start and end. These are metadata creation/update dates, not the book publication date; no timezone is inferred from the naive source timestamps. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [openlibrary](https://openlibrary.org/books/OL7353617M.json) — saved `sources/raw/openlibrary.json`; SHA-256 `5c06c441c0eac420e3fb85b7ea87fd86107e485a4bfd42e70594385884638d36`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "2008-04-29",
    "2025-12-15"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-19",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Order the creation and update dates of a catalogue entry",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "2008-04-29",
  "end": "2025-12-15"
}
```

### H60-20 — Match the exact edition key to its multilingual title

Project: **Open Library** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Resolve edition /books/OL26470256M. Return requestedId and the complete matching candidate record, preserving its Spanish title exactly rather than substituting an English title. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [ol-OL26470256M](https://openlibrary.org/books/OL26470256M.json) — saved `sources/raw/ol-OL26470256M.json`; SHA-256 `5e95c2284d177375518138553a9ddbf5df87ee5f13850ba2a4a424b7c2dcd216`.
- [openlibrary](https://openlibrary.org/books/OL7353617M.json) — saved `sources/raw/openlibrary.json`; SHA-256 `5c06c441c0eac420e3fb85b7ea87fd86107e485a4bfd42e70594385884638d36`.
- [ol-OL26331930M](https://openlibrary.org/books/OL26331930M.json) — saved `sources/raw/ol-OL26331930M.json`; SHA-256 `906e974f1899ded48d050041b81943bf8ba0dba13027ddc6a0770670a4116bd3`.
- [ol-OL7353618M](https://openlibrary.org/books/OL7353618M.json) — saved `sources/raw/ol-OL7353618M.json`; SHA-256 `fda82ec20e20195d31018388d54a34522250706f9eda77972076baa5c89a0d29`.
- [ol-OL24397122M](https://openlibrary.org/books/OL24397122M.json) — saved `sources/raw/ol-OL24397122M.json`; SHA-256 `69360fe00a065d49f1d0dc021e6b912dc91d153cc7b9de9493807b6de14f8be2`.
- [ol-OL25468407M](https://openlibrary.org/books/OL25468407M.json) — saved `sources/raw/ol-OL25468407M.json`; SHA-256 `e33a75ad41ac5c59ea18340109c7d2767d082958754c02f4686d51c0b5bc6825`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": "/books/OL26470256M",
  "candidates": [
    {
      "id": "/books/OL7353617M",
      "title": "Fantastic Mr. Fox"
    },
    {
      "id": "/books/OL26331930M",
      "title": "Harry Potter and the Sorcerer's Stone"
    },
    {
      "id": "/books/OL26470256M",
      "title": "Instrumentación quirúrgica : teoría, técnicas y procedimiento - 5. ed."
    },
    {
      "id": "/books/OL7353618M",
      "title": "Danny, The Champion of the World"
    },
    {
      "id": "/books/OL24397122M",
      "title": "The old forts of Winnipeg, 1738-1927"
    },
    {
      "id": "/books/OL25468407M",
      "title": "[Letter to] My Dear Friend"
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-20",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string",
        "const": "/books/OL26470256M"
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "required": [
          "id",
          "title"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Match the exact edition key to its multilingual title",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "id": {
              "type": "string"
            },
            "title": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "title"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/2"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": "/books/OL26470256M",
  "record": {
    "id": "/books/OL26470256M",
    "title": "Instrumentación quirúrgica : teoría, técnicas y procedimiento - 5. ed."
  }
}
```

### H60-21 — Choose an actual source reference for a book edition

Project: **Open Library** · Family: **List membership** · Valid answer alternatives: **7**

**Exact task prompt**

Return selected as any source_records value recorded for edition OL7353617M. An ISBN or source string from another edition is not acceptable. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [openlibrary](https://openlibrary.org/books/OL7353617M.json) — saved `sources/raw/openlibrary.json`; SHA-256 `5c06c441c0eac420e3fb85b7ea87fd86107e485a4bfd42e70594385884638d36`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "promise:bwb_daily_pallets_2021-05-13:KP-140-654",
    "ia:fantasticmrfox00dahl_834",
    "marc:marc_openlibraries_sanfranciscopubliclibrary/sfpl_chq_2018_12_24_run02.mrc:85081404:4525",
    "amazon:0140328726",
    "bwb:9780140328721",
    "promise:bwb_daily_pallets_2021-04-19:KP-128-107",
    "promise:bwb_daily_pallets_2020-04-30:O6-BTK-941"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-21",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose an actual source reference for a book edition",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "promise:bwb_daily_pallets_2021-05-13:KP-140-654"
}
```

### H60-22 — Choose two distinct catalogue edition keys

Project: **Open Library** · Family: **Uniqueness** · Valid answer alternatives: **30**

**Exact task prompt**

Return records with exactly two distinct edition keys as id values, selected from the supplied metadata records. Edition IDs, not titles or author IDs, define uniqueness here. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [openlibrary](https://openlibrary.org/books/OL7353617M.json) — saved `sources/raw/openlibrary.json`; SHA-256 `5c06c441c0eac420e3fb85b7ea87fd86107e485a4bfd42e70594385884638d36`.
- [ol-OL26331930M](https://openlibrary.org/books/OL26331930M.json) — saved `sources/raw/ol-OL26331930M.json`; SHA-256 `906e974f1899ded48d050041b81943bf8ba0dba13027ddc6a0770670a4116bd3`.
- [ol-OL26470256M](https://openlibrary.org/books/OL26470256M.json) — saved `sources/raw/ol-OL26470256M.json`; SHA-256 `5e95c2284d177375518138553a9ddbf5df87ee5f13850ba2a4a424b7c2dcd216`.
- [ol-OL7353618M](https://openlibrary.org/books/OL7353618M.json) — saved `sources/raw/ol-OL7353618M.json`; SHA-256 `fda82ec20e20195d31018388d54a34522250706f9eda77972076baa5c89a0d29`.
- [ol-OL24397122M](https://openlibrary.org/books/OL24397122M.json) — saved `sources/raw/ol-OL24397122M.json`; SHA-256 `69360fe00a065d49f1d0dc021e6b912dc91d153cc7b9de9493807b6de14f8be2`.
- [ol-OL25468407M](https://openlibrary.org/books/OL25468407M.json) — saved `sources/raw/ol-OL25468407M.json`; SHA-256 `e33a75ad41ac5c59ea18340109c7d2767d082958754c02f4686d51c0b5bc6825`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    "/books/OL7353617M",
    "/books/OL26331930M",
    "/books/OL26470256M",
    "/books/OL7353618M",
    "/books/OL24397122M",
    "/books/OL25468407M"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-22",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose two distinct catalogue edition keys",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": "/books/OL7353617M"
    },
    {
      "id": "/books/OL26331930M"
    }
  ]
}
```

### H60-23 — Count catalogue source references without dropping entries

Project: **Open Library** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the complete saved source_records list for OL7353617M into items in order and return count. Treat each supplied reference as an item, even when several refer to the same organisation. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [openlibrary](https://openlibrary.org/books/OL7353617M.json) — saved `sources/raw/openlibrary.json`; SHA-256 `5c06c441c0eac420e3fb85b7ea87fd86107e485a4bfd42e70594385884638d36`.

**Trusted facts sent to every arm**

```json
{
  "items": [
    "promise:bwb_daily_pallets_2021-05-13:KP-140-654",
    "ia:fantasticmrfox00dahl_834",
    "marc:marc_openlibraries_sanfranciscopubliclibrary/sfpl_chq_2018_12_24_run02.mrc:85081404:4525",
    "amazon:0140328726",
    "bwb:9780140328721",
    "promise:bwb_daily_pallets_2021-04-19:KP-128-107",
    "promise:bwb_daily_pallets_2020-04-30:O6-BTK-941"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-23",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "count": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [
      "items",
      "count"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Count catalogue source references without dropping entries",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "items"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [
    "promise:bwb_daily_pallets_2021-05-13:KP-140-654",
    "ia:fantasticmrfox00dahl_834",
    "marc:marc_openlibraries_sanfranciscopubliclibrary/sfpl_chq_2018_12_24_run02.mrc:85081404:4525",
    "amazon:0140328726",
    "bwb:9780140328721",
    "promise:bwb_daily_pallets_2021-04-19:KP-128-107",
    "promise:bwb_daily_pallets_2020-04-30:O6-BTK-941"
  ],
  "count": 7
}
```

### H60-24 — Aggregate only edition records with reported page counts

Project: **Open Library** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the supplied five rows of edition keys and reported number_of_pages values, mapped to amount. Sum them into total pages across these catalogue records. The manuscript edition OL25468407M has no number_of_pages and is excluded; do not replace that missing value with zero or infer it. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [openlibrary](https://openlibrary.org/books/OL7353617M.json) — saved `sources/raw/openlibrary.json`; SHA-256 `5c06c441c0eac420e3fb85b7ea87fd86107e485a4bfd42e70594385884638d36`.
- [ol-OL26331930M](https://openlibrary.org/books/OL26331930M.json) — saved `sources/raw/ol-OL26331930M.json`; SHA-256 `906e974f1899ded48d050041b81943bf8ba0dba13027ddc6a0770670a4116bd3`.
- [ol-OL26470256M](https://openlibrary.org/books/OL26470256M.json) — saved `sources/raw/ol-OL26470256M.json`; SHA-256 `5e95c2284d177375518138553a9ddbf5df87ee5f13850ba2a4a424b7c2dcd216`.
- [ol-OL7353618M](https://openlibrary.org/books/OL7353618M.json) — saved `sources/raw/ol-OL7353618M.json`; SHA-256 `fda82ec20e20195d31018388d54a34522250706f9eda77972076baa5c89a0d29`.
- [ol-OL24397122M](https://openlibrary.org/books/OL24397122M.json) — saved `sources/raw/ol-OL24397122M.json`; SHA-256 `69360fe00a065d49f1d0dc021e6b912dc91d153cc7b9de9493807b6de14f8be2`.

**Trusted facts sent to every arm**

```json
{
  "rows": [
    {
      "id": "/books/OL7353617M",
      "amount": 96
    },
    {
      "id": "/books/OL26331930M",
      "amount": 309
    },
    {
      "id": "/books/OL26470256M",
      "amount": 1152
    },
    {
      "id": "/books/OL7353618M",
      "amount": 208
    },
    {
      "id": "/books/OL24397122M",
      "amount": 39
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-24",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "rows",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Aggregate only edition records with reported page counts",
  "contextSchema": {
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "rows"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/rows",
      "contextLocation": "/rows"
    }
  ],
  "relationships": [
    {
      "id": "exact-sum",
      "kind": "sum_items_equals",
      "target": "/total",
      "arrayLocation": "/rows",
      "itemLocation": "/amount"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-sum",
    "kind": "sum_items_equals",
    "target": "/total",
    "arrayLocation": "/rows",
    "itemLocation": "/amount",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "rows": [
    {
      "id": "/books/OL7353617M",
      "amount": 96
    },
    {
      "id": "/books/OL26331930M",
      "amount": 309
    },
    {
      "id": "/books/OL26470256M",
      "amount": 1152
    },
    {
      "id": "/books/OL7353618M",
      "amount": 208
    },
    {
      "id": "/books/OL24397122M",
      "amount": 39
    }
  ],
  "total": 1804
}
```

### H60-25 — Choose a chronological interval in Kysely release history

Project: **Kysely / npm** · Family: **Date ordering** · Valid answer alternatives: **10**

**Exact task prompt**

Choose any two different supplied publication calendar dates of the six most recently published stable Kysely versions. Return start strictly before end. Publication time, not numeric version order, defines these dates. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [npm-kysely](https://registry.npmjs.org/kysely) — saved `sources/raw/npm-kysely.json`; SHA-256 `a75c715f6f86bf736c603127a11a7b711940ec220f15818e211fd4ebe1618251`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "2026-07-05",
    "2026-07-17",
    "2026-08-10",
    "2026-09-16",
    "2026-10-17",
    "2026-10-17"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-25",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose a chronological interval in Kysely release history",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "2026-07-05",
  "end": "2026-07-17"
}
```

### H60-26 — Match a published version to its own integrity metadata

Project: **Kysely / npm** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Find Kysely version 0.28.18. Return requestedId and that complete candidate record, retaining the correct shasum, fileCount and unpackedSize rather than mixing releases. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [npm-kysely](https://registry.npmjs.org/kysely) — saved `sources/raw/npm-kysely.json`; SHA-256 `a75c715f6f86bf736c603127a11a7b711940ec220f15818e211fd4ebe1618251`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": "0.28.18",
  "candidates": [
    {
      "id": "0.29.3",
      "shasum": "e219d9290a4398706fb5d1aa73fbe46a13e37287",
      "fileCount": 610,
      "unpackedSize": 1724883
    },
    {
      "id": "0.29.4",
      "shasum": "1d61f583026f9b071dc5c8fe58cc3bef5153dff4",
      "fileCount": 610,
      "unpackedSize": 1725100
    },
    {
      "id": "0.29.5",
      "shasum": "c07a51700a4b4db53c60bd373e6e098f919fccae",
      "fileCount": 610,
      "unpackedSize": 1726867
    },
    {
      "id": "0.29.6",
      "shasum": "f3af9a818a5a6def8e63fbc32ffb773346be911a",
      "fileCount": 610,
      "unpackedSize": 1726989
    },
    {
      "id": "0.29.7",
      "shasum": "fa505bb5e1cc67a14dc93a3cda7fbaa82268f2f0",
      "fileCount": 610,
      "unpackedSize": 1734447
    },
    {
      "id": "0.28.18",
      "shasum": "d594fbee63241ccdb6e3849bf44c05b39aa68741",
      "fileCount": 1130,
      "unpackedSize": 3310580
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-26",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string",
        "const": "0.28.18"
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "shasum": {
            "type": "string"
          },
          "fileCount": {
            "type": "integer"
          },
          "unpackedSize": {
            "type": "integer"
          }
        },
        "required": [
          "id",
          "shasum",
          "fileCount",
          "unpackedSize"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Match a published version to its own integrity metadata",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "fileCount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            },
            "shasum": {
              "type": "string"
            },
            "unpackedSize": {
              "type": "integer"
            }
          },
          "required": [
            "id",
            "shasum",
            "fileCount",
            "unpackedSize"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/5"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": "0.28.18",
  "record": {
    "id": "0.28.18",
    "shasum": "d594fbee63241ccdb6e3849bf44c05b39aa68741",
    "fileCount": 1130,
    "unpackedSize": 3310580
  }
}
```

### H60-27 — Choose a declared development dependency

Project: **Kysely / npm** · Family: **List membership** · Valid answer alternatives: **32**

**Exact task prompt**

Return selected as any development-dependency package name present in the published Kysely 0.28.18 manifest. Choose a key from the supplied actual devDependencies object; do not invent a production dependency. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [npm-kysely](https://registry.npmjs.org/kysely) — saved `sources/raw/npm-kysely.json`; SHA-256 `a75c715f6f86bf736c603127a11a7b711940ec220f15818e211fd4ebe1618251`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "@arethetypeswrong/cli",
    "@ark/attest",
    "@types/better-sqlite3",
    "@types/chai",
    "@types/chai-as-promised",
    "@types/mocha",
    "@types/node",
    "@types/pg",
    "@types/pg-cursor",
    "@types/semver",
    "@types/sinon",
    "better-sqlite3",
    "chai",
    "chai-as-promised",
    "esbuild",
    "jsr",
    "lodash",
    "mocha",
    "mysql2",
    "pathe",
    "pg",
    "pg-cursor",
    "pkg-types",
    "playwright",
    "prettier",
    "semver",
    "sinon",
    "std-env",
    "tarn",
    "tedious",
    "tsd",
    "typescript"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-27",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose a declared development dependency",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "@arethetypeswrong/cli"
}
```

### H60-28 — Choose two different published stable versions

Project: **Kysely / npm** · Family: **Uniqueness** · Valid answer alternatives: **30**

**Exact task prompt**

Return records with two distinct stable Kysely version strings as id values, selected from the supplied publication records. Both major/minor release branches remain valid candidates. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [npm-kysely](https://registry.npmjs.org/kysely) — saved `sources/raw/npm-kysely.json`; SHA-256 `a75c715f6f86bf736c603127a11a7b711940ec220f15818e211fd4ebe1618251`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    "0.29.3",
    "0.29.4",
    "0.29.5",
    "0.29.6",
    "0.29.7",
    "0.28.18"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-28",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose two different published stable versions",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": "0.29.3"
    },
    {
      "id": "0.29.4"
    }
  ]
}
```

### H60-29 — Count the actual development-dependency names

Project: **Kysely / npm** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the complete sorted list of devDependencies keys for Kysely 0.28.18 into items and return count. This is development-dependency count, not package tarball fileCount. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [npm-kysely](https://registry.npmjs.org/kysely) — saved `sources/raw/npm-kysely.json`; SHA-256 `a75c715f6f86bf736c603127a11a7b711940ec220f15818e211fd4ebe1618251`.

**Trusted facts sent to every arm**

```json
{
  "items": [
    "@arethetypeswrong/cli",
    "@ark/attest",
    "@types/better-sqlite3",
    "@types/chai",
    "@types/chai-as-promised",
    "@types/mocha",
    "@types/node",
    "@types/pg",
    "@types/pg-cursor",
    "@types/semver",
    "@types/sinon",
    "better-sqlite3",
    "chai",
    "chai-as-promised",
    "esbuild",
    "jsr",
    "lodash",
    "mocha",
    "mysql2",
    "pathe",
    "pg",
    "pg-cursor",
    "pkg-types",
    "playwright",
    "prettier",
    "semver",
    "sinon",
    "std-env",
    "tarn",
    "tedious",
    "tsd",
    "typescript"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-29",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "count": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [
      "items",
      "count"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Count the actual development-dependency names",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "items"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [
    "@arethetypeswrong/cli",
    "@ark/attest",
    "@types/better-sqlite3",
    "@types/chai",
    "@types/chai-as-promised",
    "@types/mocha",
    "@types/node",
    "@types/pg",
    "@types/pg-cursor",
    "@types/semver",
    "@types/sinon",
    "better-sqlite3",
    "chai",
    "chai-as-promised",
    "esbuild",
    "jsr",
    "lodash",
    "mocha",
    "mysql2",
    "pathe",
    "pg",
    "pg-cursor",
    "pkg-types",
    "playwright",
    "prettier",
    "semver",
    "sinon",
    "std-env",
    "tarn",
    "tedious",
    "tsd",
    "typescript"
  ],
  "count": 32
}
```

### H60-30 — Total unpacked bytes across six published release artifacts

Project: **Kysely / npm** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the supplied version rows and unpackedSize values as amount. Return total as their exact sum in bytes. This is the sum of six separate published artifacts, not deduplicated disk usage or compressed transfer size. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [npm-kysely](https://registry.npmjs.org/kysely) — saved `sources/raw/npm-kysely.json`; SHA-256 `a75c715f6f86bf736c603127a11a7b711940ec220f15818e211fd4ebe1618251`.

**Trusted facts sent to every arm**

```json
{
  "rows": [
    {
      "id": "0.29.3",
      "amount": 1724883
    },
    {
      "id": "0.29.4",
      "amount": 1725100
    },
    {
      "id": "0.29.5",
      "amount": 1726867
    },
    {
      "id": "0.29.6",
      "amount": 1726989
    },
    {
      "id": "0.29.7",
      "amount": 1734447
    },
    {
      "id": "0.28.18",
      "amount": 3310580
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-30",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "rows",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Total unpacked bytes across six published release artifacts",
  "contextSchema": {
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "rows"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/rows",
      "contextLocation": "/rows"
    }
  ],
  "relationships": [
    {
      "id": "exact-sum",
      "kind": "sum_items_equals",
      "target": "/total",
      "arrayLocation": "/rows",
      "itemLocation": "/amount"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-sum",
    "kind": "sum_items_equals",
    "target": "/total",
    "arrayLocation": "/rows",
    "itemLocation": "/amount",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "rows": [
    {
      "id": "0.29.3",
      "amount": 1724883
    },
    {
      "id": "0.29.4",
      "amount": 1725100
    },
    {
      "id": "0.29.5",
      "amount": 1726867
    },
    {
      "id": "0.29.6",
      "amount": 1726989
    },
    {
      "id": "0.29.7",
      "amount": 1734447
    },
    {
      "id": "0.28.18",
      "amount": 3310580
    }
  ],
  "total": 11948866
}
```

### H60-31 — Choose a Rails publication interval

Project: **Rails / RubyGems** · Family: **Date ordering** · Valid answer alternatives: **15**

**Exact task prompt**

Choose any two distinct supplied Rails release-publication days, returning start strictly before end. Use created_at; built_at is not a publication timestamp and is deliberately not used. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [rubygems-rails](https://rubygems.org/api/v1/versions/rails.json) — saved `sources/raw/rubygems-rails.json`; SHA-256 `29af19443876bd36f73c15c4a17ccf2c1bb16302f8f964c91ce1086615416582`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "2026-09-24",
    "2026-07-29",
    "2026-03-24",
    "2026-03-23",
    "2026-01-08",
    "2025-10-28"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-31",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose a Rails publication interval",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "2026-07-29",
  "end": "2026-09-24"
}
```

### H60-32 — Match a Rails version to its platform and archive hash

Project: **Rails / RubyGems** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Resolve Rails version 8.1.3 among the candidates. Return requestedId and the complete matching record, preserving its platform and SHA. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [rubygems-rails](https://rubygems.org/api/v1/versions/rails.json) — saved `sources/raw/rubygems-rails.json`; SHA-256 `29af19443876bd36f73c15c4a17ccf2c1bb16302f8f964c91ce1086615416582`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": "8.1.3",
  "candidates": [
    {
      "id": "8.1.4",
      "platform": "ruby",
      "sha": "5f3ecdf9a2a3b79b2e31b8fee3b64a00f7284d76e5631f87d0e58e665911a33b"
    },
    {
      "id": "8.1.3.1",
      "platform": "ruby",
      "sha": "ccd11a36bfc171bf9c66d585d14c0ece91c0c9dde840aae60c0118d6f5c9c52a"
    },
    {
      "id": "8.1.3",
      "platform": "ruby",
      "sha": "6d017ba5348c98fc909753a8169b21d44de14d2a0b92d140d1a966834c3c9cd3"
    },
    {
      "id": "8.1.2.1",
      "platform": "ruby",
      "sha": "93ebf1efc792c9bc47e9795259c920312d3920008dad3ae634b7a0457ffe0af8"
    },
    {
      "id": "8.1.2",
      "platform": "ruby",
      "sha": "5069061b23dfa8706b9f0159ae8b9d35727359103178a26962b868a680ba7d95"
    },
    {
      "id": "8.1.1",
      "platform": "ruby",
      "sha": "877509b7aef309239978685883097d2c03e21383a50a3f78882cf9b3b5c136f7"
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-32",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string",
        "const": "8.1.3"
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "platform": {
            "type": "string"
          },
          "sha": {
            "type": "string"
          }
        },
        "required": [
          "id",
          "platform",
          "sha"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Match a Rails version to its platform and archive hash",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "id": {
              "type": "string"
            },
            "platform": {
              "type": "string"
            },
            "sha": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "platform",
            "sha"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/2"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": "8.1.3",
  "record": {
    "id": "8.1.3",
    "platform": "ruby",
    "sha": "6d017ba5348c98fc909753a8169b21d44de14d2a0b92d140d1a966834c3c9cd3"
  }
}
```

### H60-33 — Select a published non-prerelease Rails version

Project: **Rails / RubyGems** · Family: **List membership** · Valid answer alternatives: **6**

**Exact task prompt**

Return selected as any one of the supplied Rails versions. The allowed list contains actual non-prerelease ruby-platform release records selected from the frozen API response. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [rubygems-rails](https://rubygems.org/api/v1/versions/rails.json) — saved `sources/raw/rubygems-rails.json`; SHA-256 `29af19443876bd36f73c15c4a17ccf2c1bb16302f8f964c91ce1086615416582`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "8.1.4",
    "8.1.3.1",
    "8.1.3",
    "8.1.2.1",
    "8.1.2",
    "8.1.1"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-33",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Select a published non-prerelease Rails version",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "8.1.4"
}
```

### H60-34 — Choose two distinct Rails release archive hashes

Project: **Rails / RubyGems** · Family: **Uniqueness** · Valid answer alternatives: **30**

**Exact task prompt**

Return records with exactly two distinct archive SHA values as id, selected from the supplied release metadata. Do not confuse the archive SHA with spec_sha. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [rubygems-rails](https://rubygems.org/api/v1/versions/rails.json) — saved `sources/raw/rubygems-rails.json`; SHA-256 `29af19443876bd36f73c15c4a17ccf2c1bb16302f8f964c91ce1086615416582`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    "5f3ecdf9a2a3b79b2e31b8fee3b64a00f7284d76e5631f87d0e58e665911a33b",
    "ccd11a36bfc171bf9c66d585d14c0ece91c0c9dde840aae60c0118d6f5c9c52a",
    "6d017ba5348c98fc909753a8169b21d44de14d2a0b92d140d1a966834c3c9cd3",
    "93ebf1efc792c9bc47e9795259c920312d3920008dad3ae634b7a0457ffe0af8",
    "5069061b23dfa8706b9f0159ae8b9d35727359103178a26962b868a680ba7d95",
    "877509b7aef309239978685883097d2c03e21383a50a3f78882cf9b3b5c136f7"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-34",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose two distinct Rails release archive hashes",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": "5f3ecdf9a2a3b79b2e31b8fee3b64a00f7284d76e5631f87d0e58e665911a33b"
    },
    {
      "id": "ccd11a36bfc171bf9c66d585d14c0ece91c0c9dde840aae60c0118d6f5c9c52a"
    }
  ]
}
```

### H60-35 — Preserve a real empty requirements list

Project: **Rails / RubyGems** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the source release version into version. Copy the supplied requirements array into items and return count. It is genuinely empty in the captured record; do not invent requirements from ruby_version or rubygems_version. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [rubygems-rails](https://rubygems.org/api/v1/versions/rails.json) — saved `sources/raw/rubygems-rails.json`; SHA-256 `29af19443876bd36f73c15c4a17ccf2c1bb16302f8f964c91ce1086615416582`.

**Trusted facts sent to every arm**

```json
{
  "items": [],
  "version": "8.1.4"
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-35",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": true
      },
      "count": {
        "type": "integer",
        "minimum": 0
      },
      "version": {
        "type": "string"
      }
    },
    "required": [
      "items",
      "count",
      "version"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Preserve a real empty requirements list",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": true
      },
      "version": {
        "type": "string"
      }
    },
    "required": [
      "items",
      "version"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    },
    {
      "instanceLocation": "/version",
      "contextLocation": "/version"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [],
  "count": 0,
  "version": "8.1.4"
}
```

### H60-36 — Aggregate recorded downloads of six selected Rails versions

Project: **Rails / RubyGems** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the supplied version rows and downloads_count values as amount. Return total as their exact sum at snapshot time. This is a sum of download events for selected versions, not unique users, installations or every Rails release. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [rubygems-rails](https://rubygems.org/api/v1/versions/rails.json) — saved `sources/raw/rubygems-rails.json`; SHA-256 `29af19443876bd36f73c15c4a17ccf2c1bb16302f8f964c91ce1086615416582`.

**Trusted facts sent to every arm**

```json
{
  "rows": [
    {
      "id": "8.1.4",
      "amount": 2263964
    },
    {
      "id": "8.1.3.1",
      "amount": 13159549
    },
    {
      "id": "8.1.3",
      "amount": 12884058
    },
    {
      "id": "8.1.2.1",
      "amount": 1227753
    },
    {
      "id": "8.1.2",
      "amount": 5025891
    },
    {
      "id": "8.1.1",
      "amount": 3415569
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-36",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "rows",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Aggregate recorded downloads of six selected Rails versions",
  "contextSchema": {
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "rows"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/rows",
      "contextLocation": "/rows"
    }
  ],
  "relationships": [
    {
      "id": "exact-sum",
      "kind": "sum_items_equals",
      "target": "/total",
      "arrayLocation": "/rows",
      "itemLocation": "/amount"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-sum",
    "kind": "sum_items_equals",
    "target": "/total",
    "arrayLocation": "/rows",
    "itemLocation": "/amount",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "rows": [
    {
      "id": "8.1.4",
      "amount": 2263964
    },
    {
      "id": "8.1.3.1",
      "amount": 13159549
    },
    {
      "id": "8.1.3",
      "amount": 12884058
    },
    {
      "id": "8.1.2.1",
      "amount": 1227753
    },
    {
      "id": "8.1.2",
      "amount": 5025891
    },
    {
      "id": "8.1.1",
      "amount": 3415569
    }
  ],
  "total": 37976784
}
```

### H60-37 — Choose a valid Treasury reporting interval

Project: **U.S. Treasury DTS** · Family: **Date ordering** · Valid answer alternatives: **21**

**Exact task prompt**

Choose any two distinct record_date values present in the complete captured DTS query for 2024-01-02 through 2024-01-10. Return start strictly before end; weekends and holidays are not invented. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [treasury](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500) — saved `sources/raw/treasury.json`; SHA-256 `28216669d815dae20ac64fbd86fbb667a67cffce283b6add85effe81e4deae4d`.
- [treasury-page2](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500&page[number]=2) — saved `sources/raw/treasury-page2.json`; SHA-256 `83fb15b0cb33bc3d95974b917ea7b5f2fae5ca94f78a4f502ce4f0c644d32aa5`.
- [treasury-page3](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500&page[number]=3) — saved `sources/raw/treasury-page3.json`; SHA-256 `a6fc640ab553adea44e6abafe8a4335dd20c0118e3f7da9b3bb7c2140b0a6105`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "2024-01-02",
    "2024-01-03",
    "2024-01-04",
    "2024-01-05",
    "2024-01-08",
    "2024-01-09",
    "2024-01-10"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-37",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose a valid Treasury reporting interval",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "2024-01-02",
  "end": "2024-01-03"
}
```

### H60-38 — Match a source line within a specified daily statement

Project: **U.S. Treasury DTS** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Within the supplied 2024-01-02 Deposits excerpt, find src_line_nbr 6. Return requestedId and the whole matching record. The line number is local to this date/type, not a globally unique Treasury identifier. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [treasury](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500) — saved `sources/raw/treasury.json`; SHA-256 `28216669d815dae20ac64fbd86fbb667a67cffce283b6add85effe81e4deae4d`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": "6",
  "candidates": [
    {
      "id": "1",
      "date": "2024-01-02",
      "category": "Dept of Agriculture (USDA) - misc",
      "todayAmount": 17
    },
    {
      "id": "2",
      "date": "2024-01-02",
      "category": "USDA - Commodity Credit Corporation",
      "todayAmount": 30
    },
    {
      "id": "3",
      "date": "2024-01-02",
      "category": "USDA - Federal Crop Insurance Corp Fund",
      "todayAmount": 0
    },
    {
      "id": "4",
      "date": "2024-01-02",
      "category": "USDA - Loan Repayments",
      "todayAmount": 499
    },
    {
      "id": "5",
      "date": "2024-01-02",
      "category": "Dept of Commerce (DOC)",
      "todayAmount": 14
    },
    {
      "id": "6",
      "date": "2024-01-02",
      "category": "Dept of Defense (DoD)",
      "todayAmount": 70
    },
    {
      "id": "7",
      "date": "2024-01-02",
      "category": "Dept of Education (ED)",
      "todayAmount": 228
    },
    {
      "id": "8",
      "date": "2024-01-02",
      "category": "Dept of Energy (DOE)",
      "todayAmount": 58
    },
    {
      "id": "9",
      "date": "2024-01-02",
      "category": "Dept of Health & Human Serv (HHS) - misc",
      "todayAmount": 23
    },
    {
      "id": "10",
      "date": "2024-01-02",
      "category": "HHS - Marketplace Receipts",
      "todayAmount": 0
    },
    {
      "id": "11",
      "date": "2024-01-02",
      "category": "HHS - Medicare Premiums",
      "todayAmount": 266
    },
    {
      "id": "12",
      "date": "2024-01-02",
      "category": "Dept of Homeland Security (DHS) - misc",
      "todayAmount": 30
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-38",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string",
        "const": "6"
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "todayAmount": {
            "type": "integer"
          }
        },
        "required": [
          "id",
          "date",
          "category",
          "todayAmount"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Match a source line within a specified daily statement",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "category": {
              "type": "string"
            },
            "date": {
              "type": "string"
            },
            "id": {
              "type": "string"
            },
            "todayAmount": {
              "type": "integer"
            }
          },
          "required": [
            "id",
            "date",
            "category",
            "todayAmount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/5"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": "6",
  "record": {
    "id": "6",
    "date": "2024-01-02",
    "category": "Dept of Defense (DoD)",
    "todayAmount": 70
  }
}
```

### H60-39 — Choose a transaction type actually present in the query

Project: **U.S. Treasury DTS** · Family: **List membership** · Valid answer alternatives: **2**

**Exact task prompt**

Return selected as a transaction_type appearing in the saved Treasury query. Select a reported value, not a guessed bookkeeping label. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [treasury](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500) — saved `sources/raw/treasury.json`; SHA-256 `28216669d815dae20ac64fbd86fbb667a67cffce283b6add85effe81e4deae4d`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "Deposits",
    "Withdrawals"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-39",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose a transaction type actually present in the query",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "Deposits"
}
```

### H60-40 — Select two different reported deposit categories

Project: **U.S. Treasury DTS** · Family: **Uniqueness** · Valid answer alternatives: **132**

**Exact task prompt**

Return records with exactly two distinct transaction_catg labels as id values, selected from the supplied daily Deposits excerpt. These labels identify categories within this excerpt, not unique economic entities. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [treasury](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500) — saved `sources/raw/treasury.json`; SHA-256 `28216669d815dae20ac64fbd86fbb667a67cffce283b6add85effe81e4deae4d`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    "Dept of Agriculture (USDA) - misc",
    "USDA - Commodity Credit Corporation",
    "USDA - Federal Crop Insurance Corp Fund",
    "USDA - Loan Repayments",
    "Dept of Commerce (DOC)",
    "Dept of Defense (DoD)",
    "Dept of Education (ED)",
    "Dept of Energy (DOE)",
    "Dept of Health & Human Serv (HHS) - misc",
    "HHS - Marketplace Receipts",
    "HHS - Medicare Premiums",
    "Dept of Homeland Security (DHS) - misc"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-40",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Select two different reported deposit categories",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": "Dept of Agriculture (USDA) - misc"
    },
    {
      "id": "USDA - Commodity Credit Corporation"
    }
  ]
}
```

### H60-41 — Copy and count a scoped deposit-category excerpt

Project: **U.S. Treasury DTS** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy every supplied daily Deposits excerpt record into items and return count. This explicitly scoped excerpt has the first twelve non-total deposit categories for the earliest captured reporting date; do not treat it as the entire Treasury statement. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [treasury](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500) — saved `sources/raw/treasury.json`; SHA-256 `28216669d815dae20ac64fbd86fbb667a67cffce283b6add85effe81e4deae4d`.

**Trusted facts sent to every arm**

```json
{
  "items": [
    {
      "line": "1",
      "category": "Dept of Agriculture (USDA) - misc",
      "reportedAmount": 17
    },
    {
      "line": "2",
      "category": "USDA - Commodity Credit Corporation",
      "reportedAmount": 30
    },
    {
      "line": "3",
      "category": "USDA - Federal Crop Insurance Corp Fund",
      "reportedAmount": 0
    },
    {
      "line": "4",
      "category": "USDA - Loan Repayments",
      "reportedAmount": 499
    },
    {
      "line": "5",
      "category": "Dept of Commerce (DOC)",
      "reportedAmount": 14
    },
    {
      "line": "6",
      "category": "Dept of Defense (DoD)",
      "reportedAmount": 70
    },
    {
      "line": "7",
      "category": "Dept of Education (ED)",
      "reportedAmount": 228
    },
    {
      "line": "8",
      "category": "Dept of Energy (DOE)",
      "reportedAmount": 58
    },
    {
      "line": "9",
      "category": "Dept of Health & Human Serv (HHS) - misc",
      "reportedAmount": 23
    },
    {
      "line": "10",
      "category": "HHS - Marketplace Receipts",
      "reportedAmount": 0
    },
    {
      "line": "11",
      "category": "HHS - Medicare Premiums",
      "reportedAmount": 266
    },
    {
      "line": "12",
      "category": "Dept of Homeland Security (DHS) - misc",
      "reportedAmount": 30
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-41",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "category": {
              "type": "string"
            },
            "line": {
              "type": "string"
            },
            "reportedAmount": {
              "type": "integer"
            }
          },
          "required": [
            "line",
            "category",
            "reportedAmount"
          ],
          "type": "object"
        }
      },
      "count": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [
      "items",
      "count"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Copy and count a scoped deposit-category excerpt",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "category": {
              "type": "string"
            },
            "line": {
              "type": "string"
            },
            "reportedAmount": {
              "type": "integer"
            }
          },
          "required": [
            "line",
            "category",
            "reportedAmount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "items"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [
    {
      "line": "1",
      "category": "Dept of Agriculture (USDA) - misc",
      "reportedAmount": 17
    },
    {
      "line": "2",
      "category": "USDA - Commodity Credit Corporation",
      "reportedAmount": 30
    },
    {
      "line": "3",
      "category": "USDA - Federal Crop Insurance Corp Fund",
      "reportedAmount": 0
    },
    {
      "line": "4",
      "category": "USDA - Loan Repayments",
      "reportedAmount": 499
    },
    {
      "line": "5",
      "category": "Dept of Commerce (DOC)",
      "reportedAmount": 14
    },
    {
      "line": "6",
      "category": "Dept of Defense (DoD)",
      "reportedAmount": 70
    },
    {
      "line": "7",
      "category": "Dept of Education (ED)",
      "reportedAmount": 228
    },
    {
      "line": "8",
      "category": "Dept of Energy (DOE)",
      "reportedAmount": 58
    },
    {
      "line": "9",
      "category": "Dept of Health & Human Serv (HHS) - misc",
      "reportedAmount": 23
    },
    {
      "line": "10",
      "category": "HHS - Marketplace Receipts",
      "reportedAmount": 0
    },
    {
      "line": "11",
      "category": "HHS - Medicare Premiums",
      "reportedAmount": 266
    },
    {
      "line": "12",
      "category": "Dept of Homeland Security (DHS) - misc",
      "reportedAmount": 30
    }
  ],
  "count": 12
}
```

### H60-42 — Sum one deposit category over seven reporting dates

Project: **U.S. Treasury DTS** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

Copy rows for the single Deposits category Dept of Agriculture (USDA) - misc, mapping transaction_today_amt to amount. Sum the seven daily values into total in the original reported DTS units. Do not add monthly/fiscal-to-date values or subtotal rows; no unit conversion is requested. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [treasury](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500) — saved `sources/raw/treasury.json`; SHA-256 `28216669d815dae20ac64fbd86fbb667a67cffce283b6add85effe81e4deae4d`.
- [treasury-page2](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500&page[number]=2) — saved `sources/raw/treasury-page2.json`; SHA-256 `83fb15b0cb33bc3d95974b917ea7b5f2fae5ca94f78a4f502ce4f0c644d32aa5`.
- [treasury-page3](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash?filter=record_date:gte:2024-01-02,record_date:lte:2024-01-10&page[size]=500&page[number]=3) — saved `sources/raw/treasury-page3.json`; SHA-256 `a6fc640ab553adea44e6abafe8a4335dd20c0118e3f7da9b3bb7c2140b0a6105`.

**Trusted facts sent to every arm**

```json
{
  "rows": [
    {
      "id": "2024-01-02",
      "amount": 17
    },
    {
      "id": "2024-01-03",
      "amount": 22
    },
    {
      "id": "2024-01-04",
      "amount": 56
    },
    {
      "id": "2024-01-05",
      "amount": 10
    },
    {
      "id": "2024-01-08",
      "amount": 10
    },
    {
      "id": "2024-01-09",
      "amount": 5
    },
    {
      "id": "2024-01-10",
      "amount": 15
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-42",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "rows",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Sum one deposit category over seven reporting dates",
  "contextSchema": {
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "rows"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/rows",
      "contextLocation": "/rows"
    }
  ],
  "relationships": [
    {
      "id": "exact-sum",
      "kind": "sum_items_equals",
      "target": "/total",
      "arrayLocation": "/rows",
      "itemLocation": "/amount"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-sum",
    "kind": "sum_items_equals",
    "target": "/total",
    "arrayLocation": "/rows",
    "itemLocation": "/amount",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "rows": [
    {
      "id": "2024-01-02",
      "amount": 17
    },
    {
      "id": "2024-01-03",
      "amount": 22
    },
    {
      "id": "2024-01-04",
      "amount": 56
    },
    {
      "id": "2024-01-05",
      "amount": 10
    },
    {
      "id": "2024-01-08",
      "amount": 10
    },
    {
      "id": "2024-01-09",
      "amount": 5
    },
    {
      "id": "2024-01-10",
      "amount": 15
    }
  ],
  "total": 135
}
```

### H60-43 — Associate a country code with its own population observation

Project: **World Bank WDI** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Resolve countryiso3code NPL in the supplied 2020 SP.POP.TOTL observations. Return requestedId and the matching record with country name, year and population. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [worldbank](https://api.worldbank.org/v2/country/IND;BGD;NPL;BTN;LKA;MDV/indicator/SP.POP.TOTL?date=2020&format=json&per_page=100) — saved `sources/raw/worldbank.json`; SHA-256 `ab2135298ca8bb0119d321ca7ec8baaf94fb283070535eed8be47b8f17dc537d`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": "NPL",
  "candidates": [
    {
      "id": "BGD",
      "country": "Bangladesh",
      "year": "2020",
      "population": 166298024
    },
    {
      "id": "BTN",
      "country": "Bhutan",
      "year": "2020",
      "population": 770006
    },
    {
      "id": "IND",
      "country": "India",
      "year": "2020",
      "population": 1402617695
    },
    {
      "id": "LKA",
      "country": "Sri Lanka",
      "year": "2020",
      "population": 21919000
    },
    {
      "id": "MDV",
      "country": "Maldives",
      "year": "2020",
      "population": 502118
    },
    {
      "id": "NPL",
      "country": "Nepal",
      "year": "2020",
      "population": 28966574
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-43",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string",
        "const": "NPL"
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "year": {
            "type": "string"
          },
          "population": {
            "type": "integer"
          }
        },
        "required": [
          "id",
          "country",
          "year",
          "population"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Associate a country code with its own population observation",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "country": {
              "type": "string"
            },
            "id": {
              "type": "string"
            },
            "population": {
              "type": "integer"
            },
            "year": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "country",
            "year",
            "population"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/5"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": "NPL",
  "record": {
    "id": "NPL",
    "country": "Nepal",
    "year": "2020",
    "population": 28966574
  }
}
```

### H60-44 — Select a country code available in the frozen extract

Project: **World Bank WDI** · Family: **List membership** · Valid answer alternatives: **6**

**Exact task prompt**

Return selected as any countryiso3code actually present in this six-country WDI extract. Do not assume a neighbouring country is included. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [worldbank](https://api.worldbank.org/v2/country/IND;BGD;NPL;BTN;LKA;MDV/indicator/SP.POP.TOTL?date=2020&format=json&per_page=100) — saved `sources/raw/worldbank.json`; SHA-256 `ab2135298ca8bb0119d321ca7ec8baaf94fb283070535eed8be47b8f17dc537d`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "BGD",
    "BTN",
    "IND",
    "LKA",
    "MDV",
    "NPL"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-44",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Select a country code available in the frozen extract",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "BGD"
}
```

### H60-45 — Choose two distinct countries for a comparison

Project: **World Bank WDI** · Family: **Uniqueness** · Valid answer alternatives: **30**

**Exact task prompt**

Return records with exactly two distinct countryiso3code values as id, selected from the supplied 2020 observations. Both orders are valid. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [worldbank](https://api.worldbank.org/v2/country/IND;BGD;NPL;BTN;LKA;MDV/indicator/SP.POP.TOTL?date=2020&format=json&per_page=100) — saved `sources/raw/worldbank.json`; SHA-256 `ab2135298ca8bb0119d321ca7ec8baaf94fb283070535eed8be47b8f17dc537d`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    "BGD",
    "BTN",
    "IND",
    "LKA",
    "MDV",
    "NPL"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-45",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose two distinct countries for a comparison",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": "BGD"
    },
    {
      "id": "BTN"
    }
  ]
}
```

### H60-46 — Count the actual observations in a fixed WDI response

Project: **World Bank WDI** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy every supplied country/year/indicator observation into items and return count. Count observations in this saved extract, not every country in a region or the API catalogue. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [worldbank](https://api.worldbank.org/v2/country/IND;BGD;NPL;BTN;LKA;MDV/indicator/SP.POP.TOTL?date=2020&format=json&per_page=100) — saved `sources/raw/worldbank.json`; SHA-256 `ab2135298ca8bb0119d321ca7ec8baaf94fb283070535eed8be47b8f17dc537d`.

**Trusted facts sent to every arm**

```json
{
  "items": [
    {
      "country": "BGD",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 166298024
    },
    {
      "country": "BTN",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 770006
    },
    {
      "country": "IND",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 1402617695
    },
    {
      "country": "LKA",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 21919000
    },
    {
      "country": "MDV",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 502118
    },
    {
      "country": "NPL",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 28966574
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-46",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "country": {
              "type": "string"
            },
            "indicator": {
              "type": "string"
            },
            "population": {
              "type": "integer"
            },
            "year": {
              "type": "string"
            }
          },
          "required": [
            "country",
            "year",
            "indicator",
            "population"
          ],
          "type": "object"
        }
      },
      "count": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [
      "items",
      "count"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Count the actual observations in a fixed WDI response",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "country": {
              "type": "string"
            },
            "indicator": {
              "type": "string"
            },
            "population": {
              "type": "integer"
            },
            "year": {
              "type": "string"
            }
          },
          "required": [
            "country",
            "year",
            "indicator",
            "population"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "items"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [
    {
      "country": "BGD",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 166298024
    },
    {
      "country": "BTN",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 770006
    },
    {
      "country": "IND",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 1402617695
    },
    {
      "country": "LKA",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 21919000
    },
    {
      "country": "MDV",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 502118
    },
    {
      "country": "NPL",
      "year": "2020",
      "indicator": "SP.POP.TOTL",
      "population": 28966574
    }
  ],
  "count": 6
}
```

**Independent publisher aggregate cross-check**

```json
{
  "sourceId": "worldbank",
  "sourcePointer": "/0/total",
  "outputField": "count"
}
```

### H60-47 — Aggregate selected 2020 populations: BGD, IND, LKA

Project: **World Bank WDI** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the supplied same-year SP.POP.TOTL rows and sum amount into total persons for exactly BGD, IND, LKA. These disjoint country observations are not a full South Asia total and must not be mixed with other years or aggregate regions. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [worldbank](https://api.worldbank.org/v2/country/IND;BGD;NPL;BTN;LKA;MDV/indicator/SP.POP.TOTL?date=2020&format=json&per_page=100) — saved `sources/raw/worldbank.json`; SHA-256 `ab2135298ca8bb0119d321ca7ec8baaf94fb283070535eed8be47b8f17dc537d`.

**Trusted facts sent to every arm**

```json
{
  "rows": [
    {
      "id": "BGD",
      "amount": 166298024
    },
    {
      "id": "IND",
      "amount": 1402617695
    },
    {
      "id": "LKA",
      "amount": 21919000
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-47",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "rows",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Aggregate selected 2020 populations: BGD, IND, LKA",
  "contextSchema": {
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "rows"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/rows",
      "contextLocation": "/rows"
    }
  ],
  "relationships": [
    {
      "id": "exact-sum",
      "kind": "sum_items_equals",
      "target": "/total",
      "arrayLocation": "/rows",
      "itemLocation": "/amount"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-sum",
    "kind": "sum_items_equals",
    "target": "/total",
    "arrayLocation": "/rows",
    "itemLocation": "/amount",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "rows": [
    {
      "id": "BGD",
      "amount": 166298024
    },
    {
      "id": "IND",
      "amount": 1402617695
    },
    {
      "id": "LKA",
      "amount": 21919000
    }
  ],
  "total": 1590834719
}
```

### H60-48 — Aggregate selected 2020 populations: BTN, MDV, NPL

Project: **World Bank WDI** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the supplied same-year SP.POP.TOTL rows and sum amount into total persons for exactly BTN, MDV, NPL. These disjoint country observations are not a full South Asia total and must not be mixed with other years or aggregate regions. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [worldbank](https://api.worldbank.org/v2/country/IND;BGD;NPL;BTN;LKA;MDV/indicator/SP.POP.TOTL?date=2020&format=json&per_page=100) — saved `sources/raw/worldbank.json`; SHA-256 `ab2135298ca8bb0119d321ca7ec8baaf94fb283070535eed8be47b8f17dc537d`.

**Trusted facts sent to every arm**

```json
{
  "rows": [
    {
      "id": "BTN",
      "amount": 770006
    },
    {
      "id": "MDV",
      "amount": 502118
    },
    {
      "id": "NPL",
      "amount": 28966574
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-48",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "rows",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Aggregate selected 2020 populations: BTN, MDV, NPL",
  "contextSchema": {
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "rows"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/rows",
      "contextLocation": "/rows"
    }
  ],
  "relationships": [
    {
      "id": "exact-sum",
      "kind": "sum_items_equals",
      "target": "/total",
      "arrayLocation": "/rows",
      "itemLocation": "/amount"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-sum",
    "kind": "sum_items_equals",
    "target": "/total",
    "arrayLocation": "/rows",
    "itemLocation": "/amount",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "rows": [
    {
      "id": "BTN",
      "amount": 770006
    },
    {
      "id": "MDV",
      "amount": 502118
    },
    {
      "id": "NPL",
      "amount": 28966574
    }
  ],
  "total": 30238698
}
```

### H60-49 — Choose an observed UTC pageview reporting interval

Project: **Wikimedia Pageviews** · Family: **Date ordering** · Valid answer alternatives: **6**

**Exact task prompt**

For the English Wikipedia Saturn page, select any two distinct supplied daily reporting dates. Return start strictly before end. The source timestamps YYYYMMDD00 are converted to ISO calendar dates; no missing days are fabricated. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [wikimedia](https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Saturn/daily/2024010100/2024011000) — saved `sources/raw/wikimedia.json`; SHA-256 `2733ee783808154ed756c32e348e3ec1beb0200ce9f7ac68741e1032a3c06bd7`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "2024-01-01",
    "2024-01-02",
    "2024-01-04",
    "2024-01-06"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-49",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose an observed UTC pageview reporting interval",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "2024-01-01",
  "end": "2024-01-02"
}
```

### H60-50 — Choose an observed UTC pageview reporting interval

Project: **Wikimedia Pageviews** · Family: **Date ordering** · Valid answer alternatives: **6**

**Exact task prompt**

For the English Wikipedia Saturn page, select any two distinct supplied daily reporting dates. Return start strictly before end. The source timestamps YYYYMMDD00 are converted to ISO calendar dates; no missing days are fabricated. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [wikimedia](https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Saturn/daily/2024010100/2024011000) — saved `sources/raw/wikimedia.json`; SHA-256 `2733ee783808154ed756c32e348e3ec1beb0200ce9f7ac68741e1032a3c06bd7`.

**Trusted facts sent to every arm**

```json
{
  "dates": [
    "2024-01-05",
    "2024-01-07",
    "2024-01-08",
    "2024-01-10"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-50",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "start": {
        "type": "string",
        "format": "date"
      },
      "end": {
        "type": "string",
        "format": "date"
      }
    },
    "required": [
      "start",
      "end"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose an observed UTC pageview reporting interval",
  "contextSchema": {
    "type": "object",
    "properties": {
      "dates": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "dates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/start",
      "contextLocation": "/dates",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/end",
      "contextLocation": "/dates",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "chronology",
      "kind": "date_before",
      "left": "/start",
      "right": "/end"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "start": "2024-01-05",
  "end": "2024-01-07"
}
```

### H60-51 — Keep a pageview date associated with its own view count

Project: **Wikimedia Pageviews** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Resolve source timestamp 2024010500 in the supplied Saturn daily pageview candidates. Return requestedId and that complete record; preserve the associated article, access, agent and views. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [wikimedia](https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Saturn/daily/2024010100/2024011000) — saved `sources/raw/wikimedia.json`; SHA-256 `2733ee783808154ed756c32e348e3ec1beb0200ce9f7ac68741e1032a3c06bd7`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": "2024010500",
  "candidates": [
    {
      "id": "2024010100",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 4224
    },
    {
      "id": "2024010200",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 4261
    },
    {
      "id": "2024010300",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 4312
    },
    {
      "id": "2024010400",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 4278
    },
    {
      "id": "2024010500",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 5141
    },
    {
      "id": "2024010600",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 4524
    },
    {
      "id": "2024010700",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 5092
    },
    {
      "id": "2024010800",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 4736
    },
    {
      "id": "2024010900",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 5120
    },
    {
      "id": "2024011000",
      "article": "Saturn",
      "access": "all-access",
      "agent": "user",
      "views": 5239
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-51",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string",
        "const": "2024010500"
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "article": {
            "type": "string"
          },
          "access": {
            "type": "string"
          },
          "agent": {
            "type": "string"
          },
          "views": {
            "type": "integer"
          }
        },
        "required": [
          "id",
          "article",
          "access",
          "agent",
          "views"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Keep a pageview date associated with its own view count",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "string"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "access": {
              "type": "string"
            },
            "agent": {
              "type": "string"
            },
            "article": {
              "type": "string"
            },
            "id": {
              "type": "string"
            },
            "views": {
              "type": "integer"
            }
          },
          "required": [
            "id",
            "article",
            "access",
            "agent",
            "views"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/4"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": "2024010500",
  "record": {
    "id": "2024010500",
    "article": "Saturn",
    "access": "all-access",
    "agent": "user",
    "views": 5141
  }
}
```

### H60-52 — Choose an available source reporting timestamp

Project: **Wikimedia Pageviews** · Family: **List membership** · Valid answer alternatives: **10**

**Exact task prompt**

Return selected as any source timestamp present in the saved ten-day Saturn pageview response. The result must use the original YYYYMMDD00 string, not a guessed timestamp. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [wikimedia](https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Saturn/daily/2024010100/2024011000) — saved `sources/raw/wikimedia.json`; SHA-256 `2733ee783808154ed756c32e348e3ec1beb0200ce9f7ac68741e1032a3c06bd7`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "2024010100",
    "2024010200",
    "2024010300",
    "2024010400",
    "2024010500",
    "2024010600",
    "2024010700",
    "2024010800",
    "2024010900",
    "2024011000"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-52",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose an available source reporting timestamp",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "2024010100"
}
```

### H60-53 — Select two different daily reporting rows

Project: **Wikimedia Pageviews** · Family: **Uniqueness** · Valid answer alternatives: **90**

**Exact task prompt**

Return records with exactly two distinct source timestamp strings as id, chosen from the Saturn daily pageview records. Two copies of the same day are invalid. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [wikimedia](https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Saturn/daily/2024010100/2024011000) — saved `sources/raw/wikimedia.json`; SHA-256 `2733ee783808154ed756c32e348e3ec1beb0200ce9f7ac68741e1032a3c06bd7`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    "2024010100",
    "2024010200",
    "2024010300",
    "2024010400",
    "2024010500",
    "2024010600",
    "2024010700",
    "2024010800",
    "2024010900",
    "2024011000"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-53",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Select two different daily reporting rows",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": "2024010100"
    },
    {
      "id": "2024010200"
    }
  ]
}
```

### H60-54 — Total the captured ten-day pageviews

Project: **Wikimedia Pageviews** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

Copy all ten daily Saturn rows with their source timestamp as id and views as amount. Return total as the exact sum. These are pageviews under all-access/user, not unique people or all agent types. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [wikimedia](https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Saturn/daily/2024010100/2024011000) — saved `sources/raw/wikimedia.json`; SHA-256 `2733ee783808154ed756c32e348e3ec1beb0200ce9f7ac68741e1032a3c06bd7`.

**Trusted facts sent to every arm**

```json
{
  "rows": [
    {
      "id": "2024010100",
      "amount": 4224
    },
    {
      "id": "2024010200",
      "amount": 4261
    },
    {
      "id": "2024010300",
      "amount": 4312
    },
    {
      "id": "2024010400",
      "amount": 4278
    },
    {
      "id": "2024010500",
      "amount": 5141
    },
    {
      "id": "2024010600",
      "amount": 4524
    },
    {
      "id": "2024010700",
      "amount": 5092
    },
    {
      "id": "2024010800",
      "amount": 4736
    },
    {
      "id": "2024010900",
      "amount": 5120
    },
    {
      "id": "2024011000",
      "amount": 5239
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-54",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "rows",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Total the captured ten-day pageviews",
  "contextSchema": {
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "rows"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/rows",
      "contextLocation": "/rows"
    }
  ],
  "relationships": [
    {
      "id": "exact-sum",
      "kind": "sum_items_equals",
      "target": "/total",
      "arrayLocation": "/rows",
      "itemLocation": "/amount"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-sum",
    "kind": "sum_items_equals",
    "target": "/total",
    "arrayLocation": "/rows",
    "itemLocation": "/amount",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "rows": [
    {
      "id": "2024010100",
      "amount": 4224
    },
    {
      "id": "2024010200",
      "amount": 4261
    },
    {
      "id": "2024010300",
      "amount": 4312
    },
    {
      "id": "2024010400",
      "amount": 4278
    },
    {
      "id": "2024010500",
      "amount": 5141
    },
    {
      "id": "2024010600",
      "amount": 4524
    },
    {
      "id": "2024010700",
      "amount": 5092
    },
    {
      "id": "2024010800",
      "amount": 4736
    },
    {
      "id": "2024010900",
      "amount": 5120
    },
    {
      "id": "2024011000",
      "amount": 5239
    }
  ],
  "total": 46927
}
```

### H60-55 — Keep a GBIF occurrence key associated with its own record

Project: **GBIF** · Family: **Identifier matching** · Valid answer alternatives: **1**

**Exact task prompt**

Resolve the supplied requested GBIF occurrence key. Return requestedId and the matching candidate, preserving occurrenceID, scientificName and datasetKey. A GBIF key and a publisher occurrenceID are different identifiers. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [gbif-ebird](https://api.gbif.org/v1/occurrence/search?datasetKey=4fa7b334-ce0d-4e88-aaae-2e0c138d049e&country=DK&year=2023&scientificName=Passer%20domesticus&license=CC_BY_4_0&limit=100) — saved `sources/raw/gbif-ebird.json`; SHA-256 `8cf5bd2f262fd44b9274e3822f2cd33fbb2d5b00b6268f4d819a4a29af713ecb`.

**Trusted facts sent to every arm**

```json
{
  "requestedId": 4615447181,
  "candidates": [
    {
      "id": 4608663953,
      "occurrenceID": "URN:catalog:CLO:EBIRD:OBS1599274432",
      "scientificName": "Passer domesticus (Linnaeus, 1758)",
      "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
    },
    {
      "id": 4608680838,
      "occurrenceID": "URN:catalog:CLO:EBIRD:OBS1597119502",
      "scientificName": "Passer domesticus (Linnaeus, 1758)",
      "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
    },
    {
      "id": 4609120465,
      "occurrenceID": "URN:catalog:CLO:EBIRD:OBS1611635751",
      "scientificName": "Passer domesticus (Linnaeus, 1758)",
      "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
    },
    {
      "id": 4609132935,
      "occurrenceID": "URN:catalog:CLO:EBIRD:OBS1612392345",
      "scientificName": "Passer domesticus (Linnaeus, 1758)",
      "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
    },
    {
      "id": 4609408294,
      "occurrenceID": "URN:catalog:CLO:EBIRD:OBS1611541081",
      "scientificName": "Passer domesticus (Linnaeus, 1758)",
      "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
    },
    {
      "id": 4615447181,
      "occurrenceID": "URN:catalog:CLO:EBIRD:OBS1598051874",
      "scientificName": "Passer domesticus (Linnaeus, 1758)",
      "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
    },
    {
      "id": 4616157910,
      "occurrenceID": "URN:catalog:CLO:EBIRD:OBS1599129899",
      "scientificName": "Passer domesticus (Linnaeus, 1758)",
      "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
    },
    {
      "id": 4619836476,
      "occurrenceID": "URN:catalog:CLO:EBIRD:OBS1599628247",
      "scientificName": "Passer domesticus (Linnaeus, 1758)",
      "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-55",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "integer",
        "const": 4615447181
      },
      "record": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer"
          },
          "occurrenceID": {
            "type": "string"
          },
          "scientificName": {
            "type": "string"
          },
          "datasetKey": {
            "type": "string"
          }
        },
        "required": [
          "id",
          "occurrenceID",
          "scientificName",
          "datasetKey"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "requestedId",
      "record"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Keep a GBIF occurrence key associated with its own record",
  "contextSchema": {
    "type": "object",
    "properties": {
      "requestedId": {
        "type": "integer"
      },
      "candidates": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "datasetKey": {
              "type": "string"
            },
            "id": {
              "type": "integer"
            },
            "occurrenceID": {
              "type": "string"
            },
            "scientificName": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "occurrenceID",
            "scientificName",
            "datasetKey"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "requestedId",
      "candidates"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/requestedId",
      "contextLocation": "/requestedId"
    },
    {
      "instanceLocation": "/record",
      "contextLocation": "/candidates/5"
    }
  ],
  "relationships": [
    {
      "id": "identifier-match",
      "kind": "equals",
      "left": "/requestedId",
      "right": "/record/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "requestedId": 4615447181,
  "record": {
    "id": 4615447181,
    "occurrenceID": "URN:catalog:CLO:EBIRD:OBS1598051874",
    "scientificName": "Passer domesticus (Linnaeus, 1758)",
    "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e"
  }
}
```

### H60-56 — Choose an observed basisOfRecord value

Project: **GBIF** · Family: **List membership** · Valid answer alternatives: **1**

**Exact task prompt**

Return selected as a basisOfRecord value actually present in the saved Denmark house-sparrow occurrence extract. Do not substitute a specimen or observation category absent from this extract. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [gbif-ebird](https://api.gbif.org/v1/occurrence/search?datasetKey=4fa7b334-ce0d-4e88-aaae-2e0c138d049e&country=DK&year=2023&scientificName=Passer%20domesticus&license=CC_BY_4_0&limit=100) — saved `sources/raw/gbif-ebird.json`; SHA-256 `8cf5bd2f262fd44b9274e3822f2cd33fbb2d5b00b6268f4d819a4a29af713ecb`.

**Trusted facts sent to every arm**

```json
{
  "allowed": [
    "HUMAN_OBSERVATION"
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-56",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "selected": {
        "type": "string"
      }
    },
    "required": [
      "selected"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose an observed basisOfRecord value",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowed": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "allowed"
    ],
    "additionalProperties": false
  },
  "bindings": [],
  "relationships": [
    {
      "id": "trusted-member",
      "kind": "reference_member",
      "target": "/selected",
      "contextLocation": "/allowed"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "selected": "HUMAN_OBSERVATION"
}
```

### H60-57 — Choose two distinct GBIF occurrence records

Project: **GBIF** · Family: **Uniqueness** · Valid answer alternatives: **132**

**Exact task prompt**

Return records with exactly two distinct numeric GBIF key values as id from the supplied candidates. This is record uniqueness, not proof that observations concern different individual birds. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [gbif-ebird](https://api.gbif.org/v1/occurrence/search?datasetKey=4fa7b334-ce0d-4e88-aaae-2e0c138d049e&country=DK&year=2023&scientificName=Passer%20domesticus&license=CC_BY_4_0&limit=100) — saved `sources/raw/gbif-ebird.json`; SHA-256 `8cf5bd2f262fd44b9274e3822f2cd33fbb2d5b00b6268f4d819a4a29af713ecb`.

**Trusted facts sent to every arm**

```json
{
  "allowedIds": [
    4608663953,
    4608680838,
    4609120465,
    4609132935,
    4609408294,
    4615447181,
    4616157910,
    4619836476,
    4623139304,
    4624852602,
    4628995176,
    4633976316
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-57",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "records": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "integer"
            }
          },
          "required": [
            "id"
          ],
          "additionalProperties": false
        },
        "minItems": 2,
        "maxItems": 2,
        "uniqueItems": true
      }
    },
    "required": [
      "records"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Choose two distinct GBIF occurrence records",
  "contextSchema": {
    "type": "object",
    "properties": {
      "allowedIds": {
        "type": "array",
        "items": {
          "type": "integer"
        }
      }
    },
    "required": [
      "allowedIds"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/records/0/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    },
    {
      "instanceLocation": "/records/1/id",
      "contextLocation": "/allowedIds",
      "keyword": "enum"
    }
  ],
  "relationships": [
    {
      "id": "unique-id",
      "kind": "unique_by",
      "arrayLocation": "/records",
      "itemLocation": "/id"
    }
  ]
}
```

**D policy:** Same prompt and generation schema as C; no application calculation.

**One computed valid answer (evaluation only)**

```json
{
  "records": [
    {
      "id": 4608663953
    },
    {
      "id": 4608680838
    }
  ]
}
```

### H60-58 — Count a scoped occurrence-record batch

Project: **GBIF** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy every supplied occurrence batch record into items and return count, preserving each key, basis and scientific name. The batch is the first twelve saved API results, not the API-wide count field. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [gbif-ebird](https://api.gbif.org/v1/occurrence/search?datasetKey=4fa7b334-ce0d-4e88-aaae-2e0c138d049e&country=DK&year=2023&scientificName=Passer%20domesticus&license=CC_BY_4_0&limit=100) — saved `sources/raw/gbif-ebird.json`; SHA-256 `8cf5bd2f262fd44b9274e3822f2cd33fbb2d5b00b6268f4d819a4a29af713ecb`.

**Trusted facts sent to every arm**

```json
{
  "items": [
    {
      "id": 4608663953,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4608680838,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4609120465,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4609132935,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4609408294,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4615447181,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4616157910,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4619836476,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4623139304,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4624852602,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4628995176,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4633976316,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-58",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "basis": {
              "type": "string"
            },
            "id": {
              "type": "integer"
            },
            "scientificName": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "basis",
            "scientificName"
          ],
          "type": "object"
        }
      },
      "count": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [
      "items",
      "count"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Count a scoped occurrence-record batch",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "basis": {
              "type": "string"
            },
            "id": {
              "type": "integer"
            },
            "scientificName": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "basis",
            "scientificName"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "items"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [
    {
      "id": 4608663953,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4608680838,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4609120465,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4609132935,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4609408294,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4615447181,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4616157910,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4619836476,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4623139304,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4624852602,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4628995176,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    },
    {
      "id": 4633976316,
      "basis": "HUMAN_OBSERVATION",
      "scientificName": "Passer domesticus (Linnaeus, 1758)"
    }
  ],
  "count": 12
}
```

### H60-59 — Preserve and count an actual taxonomic classification path

Project: **GBIF** · Family: **Counts** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the supplied classification path into items and return count of its nodes. Preserve every rank/name pair as reported by this taxonomy version; do not impose a fixed schoolbook number of taxonomic ranks. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [gbif-ebird](https://api.gbif.org/v1/occurrence/search?datasetKey=4fa7b334-ce0d-4e88-aaae-2e0c138d049e&country=DK&year=2023&scientificName=Passer%20domesticus&license=CC_BY_4_0&limit=100) — saved `sources/raw/gbif-ebird.json`; SHA-256 `8cf5bd2f262fd44b9274e3822f2cd33fbb2d5b00b6268f4d819a4a29af713ecb`.

**Trusted facts sent to every arm**

```json
{
  "items": [
    {
      "key": "CS5HF",
      "name": "Eukaryota",
      "rank": "DOMAIN"
    },
    {
      "key": "N",
      "name": "Animalia",
      "rank": "KINGDOM"
    },
    {
      "key": "CH2",
      "name": "Chordata",
      "rank": "PHYLUM"
    },
    {
      "key": "8V4V3",
      "name": "Vertebrata",
      "rank": "SUBPHYLUM"
    },
    {
      "key": "8V4V5",
      "name": "Gnathostomata",
      "rank": "INFRAPHYLUM"
    },
    {
      "key": "8VVWB",
      "name": "Osteichthyes",
      "rank": "PARVPHYLUM"
    },
    {
      "key": "9CK8W",
      "name": "Tetrapoda",
      "rank": "MEGACLASS"
    },
    {
      "key": "V2",
      "name": "Aves",
      "rank": "CLASS"
    },
    {
      "key": "3RL",
      "name": "Passeriformes",
      "rank": "ORDER"
    },
    {
      "key": "626DC",
      "name": "Passeridae",
      "rank": "FAMILY"
    },
    {
      "key": "6JFY",
      "name": "Passer",
      "rank": "GENUS"
    },
    {
      "key": "4DXXM",
      "name": "Passer domesticus",
      "rank": "SPECIES"
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-59",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "key": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "rank": {
              "type": "string"
            }
          },
          "required": [
            "key",
            "name",
            "rank"
          ],
          "type": "object"
        }
      },
      "count": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [
      "items",
      "count"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Preserve and count an actual taxonomic classification path",
  "contextSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "key": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "rank": {
              "type": "string"
            }
          },
          "required": [
            "key",
            "name",
            "rank"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "items"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/items",
      "contextLocation": "/items"
    }
  ],
  "relationships": [
    {
      "id": "exact-count",
      "kind": "count_equals",
      "target": "/count",
      "arrayLocation": "/items"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-count",
    "kind": "count_equals",
    "target": "/count",
    "arrayLocation": "/items",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "items": [
    {
      "key": "CS5HF",
      "name": "Eukaryota",
      "rank": "DOMAIN"
    },
    {
      "key": "N",
      "name": "Animalia",
      "rank": "KINGDOM"
    },
    {
      "key": "CH2",
      "name": "Chordata",
      "rank": "PHYLUM"
    },
    {
      "key": "8V4V3",
      "name": "Vertebrata",
      "rank": "SUBPHYLUM"
    },
    {
      "key": "8V4V5",
      "name": "Gnathostomata",
      "rank": "INFRAPHYLUM"
    },
    {
      "key": "8VVWB",
      "name": "Osteichthyes",
      "rank": "PARVPHYLUM"
    },
    {
      "key": "9CK8W",
      "name": "Tetrapoda",
      "rank": "MEGACLASS"
    },
    {
      "key": "V2",
      "name": "Aves",
      "rank": "CLASS"
    },
    {
      "key": "3RL",
      "name": "Passeriformes",
      "rank": "ORDER"
    },
    {
      "key": "626DC",
      "name": "Passeridae",
      "rank": "FAMILY"
    },
    {
      "key": "6JFY",
      "name": "Passer",
      "rank": "GENUS"
    },
    {
      "key": "4DXXM",
      "name": "Passer domesticus",
      "rank": "SPECIES"
    }
  ],
  "count": 12
}
```

### H60-60 — Sum only reported individualCount values in selected observations

Project: **GBIF** · Family: **Sums / products** · Valid answer alternatives: **1**

**Exact task prompt**

Copy the supplied twelve occurrence rows with key as id and reported individualCount as amount; return their exact sum as total. Missing individualCount records were excluded, never assigned one or zero. The sum is reported counts over records, not unique birds or a population estimate. Return only the requested whole JSON object. Preserve source values exactly; do not infer missing facts.

**Authentic source response(s)**

- [gbif-ebird](https://api.gbif.org/v1/occurrence/search?datasetKey=4fa7b334-ce0d-4e88-aaae-2e0c138d049e&country=DK&year=2023&scientificName=Passer%20domesticus&license=CC_BY_4_0&limit=100) — saved `sources/raw/gbif-ebird.json`; SHA-256 `8cf5bd2f262fd44b9274e3822f2cd33fbb2d5b00b6268f4d819a4a29af713ecb`.

**Trusted facts sent to every arm**

```json
{
  "rows": [
    {
      "id": 4608663953,
      "amount": 2
    },
    {
      "id": 4608680838,
      "amount": 10
    },
    {
      "id": 4609120465,
      "amount": 1
    },
    {
      "id": 4609132935,
      "amount": 3
    },
    {
      "id": 4609408294,
      "amount": 1
    },
    {
      "id": 4615447181,
      "amount": 1
    },
    {
      "id": 4616157910,
      "amount": 8
    },
    {
      "id": 4619836476,
      "amount": 1
    },
    {
      "id": 4623139304,
      "amount": 3
    },
    {
      "id": 4624852602,
      "amount": 10
    },
    {
      "id": 4628995176,
      "amount": 20
    },
    {
      "id": 4633976316,
      "amount": 1
    }
  ]
}
```

**FULL/base contract, including the ordinary output schema**

```json
{
  "id": "H60-60",
  "version": "1",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "integer"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      },
      "total": {
        "type": "integer"
      }
    },
    "required": [
      "rows",
      "total"
    ],
    "additionalProperties": false
  },
  "outputKind": "document",
  "description": "Sum only reported individualCount values in selected observations",
  "contextSchema": {
    "type": "object",
    "properties": {
      "rows": {
        "type": "array",
        "items": {
          "additionalProperties": false,
          "properties": {
            "amount": {
              "type": "integer"
            },
            "id": {
              "type": "integer"
            }
          },
          "required": [
            "id",
            "amount"
          ],
          "type": "object"
        }
      }
    },
    "required": [
      "rows"
    ],
    "additionalProperties": false
  },
  "bindings": [
    {
      "instanceLocation": "/rows",
      "contextLocation": "/rows"
    }
  ],
  "relationships": [
    {
      "id": "exact-sum",
      "kind": "sum_items_equals",
      "target": "/total",
      "arrayLocation": "/rows",
      "itemLocation": "/amount"
    }
  ]
}
```

**D: selective calculation declarations**

The application contract keeps the same facts and final output schema. Only the declared targets below are omitted during generation and filled by the application after validating the model-supplied fields.

```json
[
  {
    "id": "exact-sum",
    "kind": "sum_items_equals",
    "target": "/total",
    "arrayLocation": "/rows",
    "itemLocation": "/amount",
    "compute": "application"
  }
]
```

**One computed valid answer (evaluation only)**

```json
{
  "rows": [
    {
      "id": 4608663953,
      "amount": 2
    },
    {
      "id": 4608680838,
      "amount": 10
    },
    {
      "id": 4609120465,
      "amount": 1
    },
    {
      "id": 4609132935,
      "amount": 3
    },
    {
      "id": 4609408294,
      "amount": 1
    },
    {
      "id": 4615447181,
      "amount": 1
    },
    {
      "id": 4616157910,
      "amount": 8
    },
    {
      "id": 4619836476,
      "amount": 1
    },
    {
      "id": 4623139304,
      "amount": 3
    },
    {
      "id": 4624852602,
      "amount": 10
    },
    {
      "id": 4628995176,
      "amount": 20
    },
    {
      "id": 4633976316,
      "amount": 1
    }
  ],
  "total": 61
}
```

## Reproducing the offline verification

See `README.md` in the ZIP. The verification checks raw snapshot hashes, source projections, schemas, all valid alternatives, constructed negative controls and HESchema compatibility without making model requests. Source data is not re-fetched during verification.

The accompanying dataset freeze records the exact delivered files. Any substantive task change creates a new version and invalidates comparisons to this freeze. Execution settings must be sealed independently before any confirmation inference.
