> Raw-response archives are verified locally but publication is blocked pending explicit user authorization. This PR alone is not yet sufficient for independent replay. See PUBLICATION_STATUS.md.

# H60 independent-oracle replication results

These are new inferences on the existing authored public-record tasks, not untouched tasks.
Historical outputs were independently rescored separately in `independent-rescore.json`.

Verified selected slots: 2160. Primary matched slots: 2156. Physical request receipts: 2504.
Selected initial/repair contents and usage match their receipts. Failed and explicitly unverifiable original receipts are retained.
Three missing derived rows were recovered from intact receipts. Two original slots lacked complete initial receipts and were regenerated with their original budgets; their entire matched group is excluded from the primary tables below to avoid selection bias. See reconciliation.json and the preserved original artifacts. The missing-write root cause is unknown.

## Results

| Arm | Slots | First correct | Final correct | Wrong accepted | Correct rejected | Input tokens incl. repair | Output tokens incl. repair |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 539 | 482 | 486 | 49 | 0 | 188453 | 149665 |
| B | 539 | 450 | 488 | 0 | 0 | 456404 | 174570 |
| C | 539 | 439 | 484 | 0 | 0 | 344524 | 163235 |
| D | 539 | 423 | 477 | 0 | 0 | 356341 | 172958 |

## Final correctness by model, family and project


### model

| Group | A | B | C | D |
|---|---:|---:|---:|---:|
| openai/gpt-oss-120b | 159/179 | 160/179 | 161/179 | 153/179 |
| openai/gpt-oss-20b | 156/180 | 148/180 | 146/180 | 150/180 |
| qwen/qwen3.8-27b | 171/180 | 180/180 | 177/180 | 174/180 |

### family

| Group | A | B | C | D |
|---|---:|---:|---:|---:|
| Counts | 76/90 | 80/90 | 81/90 | 76/90 |
| Date ordering | 90/90 | 87/90 | 89/90 | 87/90 |
| Identifier matching | 87/90 | 87/90 | 87/90 | 87/90 |
| List membership | 62/89 | 60/89 | 57/89 | 56/89 |
| Sums / products | 84/90 | 90/90 | 90/90 | 90/90 |
| Uniqueness | 87/90 | 84/90 | 80/90 | 81/90 |

### project

| Group | A | B | C | D |
|---|---:|---:|---:|---:|
| GBIF | 48/54 | 49/54 | 51/54 | 51/54 |
| Kysely / npm | 42/54 | 46/54 | 42/54 | 42/54 |
| NASA EONET | 43/53 | 44/53 | 48/53 | 48/53 |
| Open Library | 51/54 | 45/54 | 44/54 | 42/54 |
| RCSB PDB | 52/54 | 54/54 | 54/54 | 51/54 |
| Rails / RubyGems | 54/54 | 51/54 | 52/54 | 49/54 |
| U.S. Treasury DTS | 49/54 | 50/54 | 45/54 | 45/54 |
| UniProt | 51/54 | 48/54 | 45/54 | 45/54 |
| Wikimedia Pageviews | 48/54 | 51/54 | 53/54 | 53/54 |
| World Bank WDI | 48/54 | 50/54 | 50/54 | 51/54 |

## Paired descriptive uncertainty

- B-A: final-correct difference 0.37 percentage points; project-bootstrap interval [-3.33, 3.52]. D-C uses arithmetic-eligible tasks only.
- C-B: final-correct difference -0.73 percentage points; project-bootstrap interval [-4.06, 2.26]. D-C uses arithmetic-eligible tasks only.
- D-C: final-correct difference -2.78 percentage points; project-bootstrap interval [-6.67, 0.00]. D-C uses arithmetic-eligible tasks only.

## Conventional application-check replay

These task-specific checks were written from source facts and task families without calling the oracle or HESchema rule evaluator. This is an offline counterfactual, not an additional generation/repair arm.
- A: 0 wrong accepted, 0 correct rejected; 49 decisions differ from the original arm detector.
- B: 0 wrong accepted, 0 correct rejected; 0 decisions differ from the original arm detector.
- C: 0 wrong accepted, 0 correct rejected; 0 decisions differ from the original arm detector.
- D: 0 wrong accepted, 0 correct rejected; 0 decisions differ from the original arm detector.

## Limits and claim boundaries

- D scores assembled system output; its calculations do not establish improved LLM arithmetic.
- Wrong acceptance is a count over scheduled slots, not the conditional rate among incorrect answers.
- Reported token usage is observed returned usage, not verified billed cost.
- Round-trip provider timings exclude full local/wait decomposition; no speed-improvement claim is supported.
- Three repeats measure consistency, not independent tasks; ten shared project clusters limit generalization.
- Original source response archives were not recaptured in this replication.
- See RERUN_PROTOCOL.md for controls and the JSON summary for grouped results.
- Zero observed wrong acceptance is not a universal validator guarantee or proof that new keywords are needed.

## Interpretation

COMPACT used 19.53% fewer selected-primary total tokens than FULL, including repairs. Its final correctness was 484/539 versus 488/539. This does not establish non-inferior accuracy.
The FULL-versus-ordinary final-correctness interval includes zero; there is no demonstrated general generation-accuracy improvement. Contract checks and conventional application checks caught all observed wrong selected-primary outputs, while the ordinary shape-only detector accepted 49 wrong outputs.
Application calculation did not improve aggregate correctness here. It matched COMPACT on sums/products but had lower correctness on count tasks. Keep calculation optional.
Physical finish reasons: {'stop': 2456, 'length': 14, 'no_return': 34}. Missing original response metadata remains explicit; neither replacements nor archived data erase that evidence gap.
