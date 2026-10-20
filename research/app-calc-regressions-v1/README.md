# APP CALC regression investigation

Investigated on 20 October 2026 using the original resumed pilot archive. This is
an offline analysis of actual saved model outputs, not a new model experiment.
Research-authored tasks use unchanged public records; they are not organic
production task logs. Repeats are not independent tasks.

## Findings

The supplied report's totals reproduce. All **11 final APP CALC failures** are
GPT OSS 20b JSON syntax failures, across four distinct tasks. Parsing failed
before the historical application enrichment step could execute. There is no
observed final arithmetic or source-mapping failure among these 11 results.

| Source / case | Failed slots | Observed defect | Recorded repair |
| --- | ---: | --- | --- |
| Crossref first affected task | 2 | Extra final `}` after a complete root object | Identical malformed text |
| Crossref second affected task | 3 | Extra final `}` after a complete root object | Identical malformed text |
| PyPI first affected task | 3 | An extra quote before the second file object's opening brace | Identical malformed text |
| PyPI second affected task | 3 | Extra quote or missing opening brace at the second file record | Identical malformed text |

The 11 slots contain **22 unsuccessful initial/repair responses**, with five
distinct text hashes. Every response has `finish_reason: stop`; these failures
are not recorded as output-cap truncations. Each failed repair is byte-for-byte
identical to its initial response. The old feedback only said to return a valid
JSON object, without a parser location or specific syntax diagnosis.

An additional initial APP CALC failure did concern copied data: GPT OSS 20b omitted
one letter from a WfCommons filename. The sizes, array length and resulting arithmetic were
unchanged. The historical source check rejected it and the saved repair corrected
the filename. This is the pilot's one APP CALC recovery, not a new recovery from
this investigation. Current replay blocks the typo before any application calculation.

### Matched final correctness

| Source | FULL | COMPACT | APP CALC |
| --- | ---: | ---: | ---: |
| Crossref | 53/53 | 53/53 | 48/53 |
| PyPI | 47/54 | 54/54 | 48/54 |
| WfCommons | 36/54 | 36/54 | 54/54 |

| Model | FULL | COMPACT | APP CALC |
| --- | ---: | ---: | ---: |
| GPT OSS 20b | 80/90 | 87/90 | 79/90 |
| GPT OSS 120b | 89/89 | 89/89 | 89/89 |
| Qwen 27b | 75/90 | 75/90 | 90/90 |

This confirms why a universal APP CALC policy is inappropriate. It does not prove
that arithmetic offloading caused a particular syntax error: APP CALC changed
the output schema, omitted fields, relationship presentation and user wording.
Those changes were not separately randomized. The Crossref extra brace is
consistent with retaining the source's outer `work` wrapper closure while mapping
its fields to the output root; that is an inference, not evidence of model intent.

### Mapping and transformation checks

In a separate, explicitly offline counterfactual, one punctuation edit per failed
response makes all 22 responses parse and reproduce the full source-derived
reference after calculation. No author, title, publisher, file, hash, flag, size
or array order needs changing. Thus there is no evidence here of a transformation
that corrupts an otherwise valid copied response in these final failures.

These edited candidates are **not** provider responses, model repairs, recovered
results or new success-rate evidence. They are never passed through production
as automatic corrections. Original malformed responses remain rejected.

## Implementation changes

- Keep strict whole-output parsing. Do not strip extra braces, extract JSON
  prefixes, replace file records from a reference answer, or accept malformed text.
- Enrich `JSON_INVALID` diagnostics with decoder reason, syntax kind, exact
  zero-based character offset, and one-based line/column when actually available.
- Pass those structured details and a source-preserving syntax hint through
  existing actionable repair feedback. Budgets, models and generation mode do not change.
- Provide tooling to replay the real failures privately through current application
  calculations. Add public-source, labelled mutation controls proving that changed
  values, dropped nested fields and reordered arrays are rejected. The committed
  controls are constructed tests, not original model responses.
- Retain per-relationship opt-in, pre-calculation source checks, raw-response
  preservation and full assembled-output validation from the preceding implementation.

This improves diagnosis and protects copied-field checks. It does **not** establish
that new model responses or repairs will improve. A prospective comparison on
untouched tasks is needed to measure that.

## Evidence and reproducibility

Original archive: `HESchema_Resumed_Pilot_Evidence.zip`.

The audit checked all 1,620 members covered by its manifest and all 58 members
covered by the nested input-pack manifest. It independently replayed every saved
phase score for the 809 verified results and linked 873 successful initial/repair
phases to their raw provider responses and submitted requests, with zero score or
trace discrepancies. All 809 initial prompts matched the frozen input pack, and
all 64 repair prompts retained that initial prompt and the actual previous answer.
Six successful preflight responses are outside those 873
measured phases. The protected result without a raw response remains excluded;
269 complete three-mode blocks provide the matched comparisons above.

The retrieved raw prompts, responses and extracted evidence remain private and are
not included in this PR. The aggregate findings above were checked locally against
that archive. The tool can produce a private extraction with raw responses and text
hashes for the 12 initial failure slots across five tasks, reusing existing
hash-matching repository source snapshots. This verifies consistency within the
supplied archive, not independent provider attestation or immutable model weights.

Run the committed public-source controls without credentials or network access:

```sh
pytest -q tests/test_app_calc_regressions.py
```

To repeat the full archive verification when the original archive is available:

```sh
python scripts/analyze_app_calc_regressions.py \
  --archive /path/to/HESchema_Resumed_Pilot_Evidence.zip \
  --out results/app-calc-regressions/full-audit.json
```

The generated file includes private evidence; it belongs in the ignored `results/`
directory. An existing private extraction can be replayed using `--bundle` in place
of `--archive`. No retrieved raw evidence is embedded in the source code or tests.

The script reads JSON from the archive; it never executes bundled Python code,
calls a model, changes frozen scores, or regenerates missing evidence. The original
pilot reports, inputs and logs remain unchanged.

Source format references: [Crossref REST API](https://api.crossref.org/swagger-ui/index.html),
[PyPI JSON API](https://docs.pypi.org/api/json/), and
[Python JSON decoder errors](https://docs.python.org/3.12/library/json.html#json.JSONDecodeError).
