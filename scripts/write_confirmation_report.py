"""Generate the descriptive report only from independently verified public evidence."""

import json
import runpy
from pathlib import Path

from heschema.confirmation import PACK


def write_report(pack=PACK):
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / 'scripts/verify_confirmation_evidence.py'))['verify'](pack)
    pack = Path(pack)
    s = json.loads((pack / 'evidence/summary.json').read_text())
    responses = [json.loads(line) for line in (pack / 'evidence/responses.jsonl').read_text().splitlines()]
    a, b = s['arms']['full'], s['arms']['compact']

    def rate(numerator, denominator):
        return f'{numerator / denominator * 100:.2f}% ({numerator}/{denominator})' if denominator else 'unavailable'

    def interval(values):
        return f'[{values[0]:.2f}, {values[1]:.2f}] percentage points' if values else 'unavailable'

    def mean_tokens(arm):
        value = arm['totalTokensIncludingEarlierCheckpoints']
        return f"{value / arm['matchedSlots']:.2f}" if value is not None and arm['matchedSlots'] else 'unavailable'

    def seconds(value):
        return f'{value / 1000:.2f} s' if value is not None else 'unavailable'

    n = s['matchedPairs']
    unknown_bound = s['recordingCompleteness']['possibleUnrecordedRequestsUpperBound']
    delta = ((b['totalTokensIncludingEarlierCheckpoints'] / a['totalTokensIncludingEarlierCheckpoints']) - 1) * 100
    status = 'All scheduled slots have recorded results.' if s['completedSlots'] == s['plannedSlots'] else 'The scheduled study is incomplete.'
    stop = s.get('executionStop')
    stop_notice = (f'**Execution block:** {stop["reason"]} The saved checkpoint contains '
                   f'{s["completedSlots"]} of {s["plannedSlots"]} scheduled slots; '
                   f'{s["plannedSlots"] - s["completedSlots"]} remain incomplete. '
                   'This is a partial confirmation report, not a completed study.' if stop else '')
    lines = [
        '# Non-arithmetic confirmation on fresh public records', '',
        f'**{status}** There are **{s["completedSlots"]}/{s["plannedSlots"]} completed slots**, '
        f'**{n} matched pairs**, **{s["tasks"]} tasks** and **{s["sourceClusters"]} source projects**.', '',
        '**Recording remains incomplete at the physical-request level.** Execution interruptions '
        f'may have lost up to {unknown_bound} calls across in-flight slots. Their responses and usage are '
        'unknown. Completed saved slots were retained; the remaining schedule was resumed. '
        'Consequently, “first” below means the first **recorded** generation, and token figures '
        'are observed usage, not verified totals for every call or actual billed cost.', '',
        stop_notice, '',
        '## What was tested', '',
        'The previous pilot reused extraction/aggregation tasks from its earlier study. This pack '
        'uses 30 newly authored tasks with real, byte-preserved public records from Node.js Release, '
        'endoflife.date, SPDX, IANA, Prometheus Operator and Homebrew. Ten tasks test date ordering, '
        'ten exact identifier matching, and ten trusted-list membership. They are researcher-created '
        'adaptations, not naturally collected production prompts or upstream-authored contracts.', '',
        'A baseline exposure audit hashed 315 tracked research/benchmark/test files and compared '
        '653 prior instruction hashes and 204 prior context hashes. No exact overlap was found for '
        'the selected instructions/context records or inspected source identifiers. SchemaStore '
        'was excluded because earlier research had already examined it. “Untouched” is limited to '
        'the inspected local studies; public model-pretraining exposure and unseen external work '
        'are unknown.', '',
        'FULL sends the projected schema, approved bindings and trusted facts. COMPACT sends the '
        'original schema, binding locations and the same trusted facts. Both retain identical full '
        'contract checks after generation. There is **no ordinary-schema-only generation arm**.', '',
        'The schedule uses three Groq models, three repeats, prompt-only generation, temperature '
        'zero, a 2,048-token output budget and at most one returned repair per slot. No application '
        'calculations, output cleanup, provider schema enforcement or oracle feedback are used. '
        'The seed randomizes the schedule; Groq does not receive a generation seed through this '
        'adapter. GPT OSS requests low reasoning effort; Qwen uses its provider-supported default.', '',
        'The cases/protocol/source snapshots were sealed before study inference. The semantic '
        'oracle uses separate date, record-equality and membership logic, accepts all valid '
        'alternatives, and runs only after bounded generation/repair. It is independently '
        'implemented semantic checking, not independent human review or a second independent '
        'JSON Schema implementation.', '',
        '## Matched results', '',
        '| Measure | FULL | COMPACT |', '|---|---:|---:|',
        f'| Correct first recorded answer | {rate(a["firstCorrect"], n)} | {rate(b["firstCorrect"], n)} |',
        f'| Correct final recorded answer | {rate(a["finalCorrect"], n)} | {rate(b["finalCorrect"], n)} |',
        f'| Initially wrong matched slots recovered | {a["finalCorrect"] - a["firstCorrect"]}/{n - a["firstCorrect"]} | {b["finalCorrect"] - b["firstCorrect"]}/{n - b["firstCorrect"]} |',
        f'| Observed tokens, including returned repairs/checkpoints | {a["totalTokensIncludingEarlierCheckpoints"]:,} | {b["totalTokensIncludingEarlierCheckpoints"]:,} |',
        f'| Observed mean tokens per matched slot | {mean_tokens(a)} | {mean_tokens(b)} |',
        f'| Wrong responses accepted by contract | {a["wrongAcceptedResponses"]} | {b["wrongAcceptedResponses"]} |',
        f'| Correct responses rejected by contract | {a["correctRejectedResponses"]} | {b["correctRejectedResponses"]} |',
        f'| Wrong responses accepted by ordinary shape schema, offline counterfactual | {a["schemaOnlyWrongAcceptedResponses"]} | {b["schemaOnlyWrongAcceptedResponses"]} |',
        f'| Median latest-checkpoint coordinator time | {seconds(a["medianCoordinatorMs"])} | {seconds(b["medianCoordinatorMs"])} |', '',
        f'COMPACT changed recorded total token usage by **{delta:+.2f}%** relative to FULL. '
        'This is a matched, observed-token comparison; interruption losses prevent a complete '
        'cost accounting. The earlier pilot’s 20.65% token reduction is not assumed to transfer '
        'to these new tasks.', '',
        ('**The earlier token saving did not replicate in this recorded sample.** '
         if delta >= 0 else '**Recorded token use was lower for COMPACT in this sample.** ')
        + ('COMPACT also had lower final recorded correctness. '
           if b['finalCorrect'] < a['finalCorrect'] else 'Final recorded correctness did not decrease for COMPACT. ')
        + 'These results support keeping prompt modes optional and testing them on the intended '
        'workflow; they do not establish universal accuracy, cost or speed effects.', '',
        '### By model', '',
        '| Model | Matched pairs | FULL first / final correct | COMPACT first / final correct |',
        '|---|---:|---:|---:|',
    ]
    for model in sorted(a['byModel']):
        x, y = a['byModel'][model], b['byModel'][model]
        lines.append(f'| `{model}` | {x["slots"]} | {x["firstCorrect"]} / {x["finalCorrect"]} | {y["firstCorrect"]} / {y["finalCorrect"]} |')
    lines += ['', '### By relationship family', '',
              '| Family | Matched pairs | FULL first / final correct | COMPACT first / final correct |',
              '|---|---:|---:|---:|']
    for family in sorted(a['byFamily']):
        x, y = a['byFamily'][family], b['byFamily'][family]
        lines.append(f'| {family.replace("_", " ")} | {x["slots"]} | {x["firstCorrect"]} / {x["finalCorrect"]} | {y["firstCorrect"]} / {y["finalCorrect"]} |')
    lines += ['', '## Failure analysis', '',
              f'Across all recorded returned responses, **{s["fencedPayloads"]["responses"]}** were '
              f'Markdown-fenced payloads; **{s["fencedPayloads"]["semanticallyCorrectInsideFence"]}** '
              'contained semantically correct payloads inside the fence. This is a post-hoc diagnostic '
              'only: they remain invalid whole JSON and are never converted into successes. A date-task '
              'formatting failure must not be relabeled as an incorrect date-order relationship.', '',
              'Observed failure labels overlap and describe returned responses, not independent tasks:', '']
    for category, count in sorted(s['failureCategories'].items()):
        lines.append(f'- `{category}`: {count} returned responses.')
    semantic = [r for r in responses if 'relationship_violation' in r['failureCategories']['categories']]
    if semantic:
        lines += ['', f'Those semantic failures cover **{len({r["caseId"] for r in semantic})} task records**, '
                  f'**{len({r["cluster"] for r in semantic})} source project(s)** and '
                  f'**{len({r["model"] for r in semantic})} model(s)**. Repeats of one task do not '
                  'establish cross-workflow reproducibility.', '']
        lines += ['', 'Semantic relationship failures were observed in these recorded outputs:', '']
        for r in semantic:
            lines.append(f'- `{r["caseId"]}`, `{r["model"]}`, `{r["arm"]}`, repeat {r["repeat"]}, attempt {r["attempt"]}.')
    for kind in ('date_before', 'equals', 'reference_member'):
        checks = [rule for response in responses for rule in response['ruleChecks'] if rule['kind'] == kind]
        lines.append(f'- `{kind}`: {sum(rule["status"] == "invalid" for rule in checks)} invalid '
                     f'of {sum(rule["status"] in {"valid", "invalid"} for rule in checks)} evaluated checks. '
                     'Unevaluated checks are not counted as passes.')
    lines += ['', 'See [all recorded failures](evidence/failures.jsonl) and '
              '[exact final content for every recorded return](evidence/responses.jsonl). '
              'Neither successful answers nor failures were selected away. Earlier private-study '
              'prompts/responses are excluded; reasoning, credentials and HTTP headers are not published.', '',
              '## Consistency and uncertainty', '',
              'Three repeats measure consistency; they are not three independent tasks. Outcomes are '
              'averaged within each task across models/repeats, then whole source projects are '
              'resampled for the descriptive bootstrap. Six clusters and three shared instruction '
              'templates give limited statistical resolution.', '']
    for outcome, label in (('firstCorrect', 'First recorded'), ('finalCorrect', 'Final recorded')):
        effect = s['paired']['outcomes'][outcome]
        lines.append(f'- {label}: COMPACT wins {effect["compactWins"]}, FULL wins {effect["fullWins"]}, '
                     f'ties {effect["ties"]} among paired trials; mean task difference '
                     f'{effect["meanTaskDifferencePp"]:+.2f} percentage points, descriptive 95% '
                     f'project-bootstrap interval {interval(effect["clusterBootstrap95Pp"])}.')
    lines += ['', 'These are dependent paired trials, not independent sample counts for a significance '
              'test. A zero-width empirical interval at ceiling does not establish population '
              'equivalence, zero error probability or universal validator safety.', '',
              '## Validation controls and operational history', '',
              'All **190 controls** pass: **100 enumerated valid alternatives**, **60 structurally '
              'valid semantic corruptions**, and **30 malformed-JSON controls**. Corruptions are '
              'synthetic probes excluded from live inputs. Ordinary shape schemas accepted the '
              '60 semantic corruptions; the independent oracle and contract checks rejected them. '
              'Many finite allowed choices can also be expressed with source-derived ordinary '
              '`enum`/`const` constraints. These controls do not demonstrate that new vocabulary is necessary.', '',
              'Session 1 stopped after 185 completed slots when its per-worker quota retry budget '
              'was exhausted. Session 2 increased minimum worker spacing from 10 to 20 seconds and '
              'reached 198 completed slots before workspace interruption. Session 3 retained the '
              '20-second pacing and the same frozen cases, runtime hashes and generation settings. '
              'Its first pending quota-failed slot retained its prior credential. A sanitized '
              'response observer records quota categories without provider error bodies. It stopped '
              'at 413 completed slots after exhausting its bounded quota retry allowance. '
              'Session 4 increased worker and per-provider call spacing to 30 seconds, including '
              'repairs, and saved 424 completed slots before its process could no longer be resumed '
              'under the current network policy. No new quota events were recorded in session 4. '
              'The second interruption adds a conservative upper bound of eight possibly '
              'unrecorded calls; the two interruptions together allow up to sixteen.', '',
              'Session histories preserve original configs, summaries, journal hashes and relative '
              'worker mappings. Credential pools were authorized in advance; workers did not fail '
              'over to another credential in reaction to an individual quota error. Limits need '
              'not be independent across keys. Per-worker quota retries are bounded per invocation, '
              'with 120-second waits. Model response IDs/fingerprints are retained when returned; '
              'fixed model names do not guarantee unchanged hosted weights across days.', '',
              f'The journal records **{s["providerRequestsAttempted"]} request attempts** and '
              f'**{s["returnedResponses"]} returned generations**. Additional interruption calls are '
              'unknown. The coordinator records provider client response time, validation, '
              'calculation, coordinator work and retry phases. Dispatch pacing and quota waits '
              'remain separate. Replayed initial responses are not billed again as new observed '
              'tokens or provider latency. The latest-checkpoint median can omit an earlier '
              'checkpoint’s work and is not total user-visible time. Parallel throughput, '
              'client response time and hosted inference time are different measurements. '
              '**This run does not establish a speed improvement or actual billed savings.**', '',
              '## Supported conclusions and limits', '',
              '- The pack broadens local testing beyond the previously reused arithmetic, extraction '
              'and aggregation tasks, with genuine public source records and multiple acceptable answers.',
              '- Contract decisions can be independently checked against recorded output and the '
              'declared source facts. Observed zero wrong acceptance/rejection is finite-sample evidence only.',
              '- Formatting failures and semantic relationship failures must remain separate. '
              'Prompt compactness alone cannot be assumed to improve accuracy, token use or latency.',
              '- Keep FULL available and retain COMPACT as an opt-in option. Do not change prompt defaults '
              'or weaken strict JSON validation based only on this small study.',
              '- No ordinary-schema generation arm, organically collected production prompts, '
              'independent human review, pretraining-contamination guarantee or complete physical-request '
              'record exists here. All live tasks are answerable; missing-context workflows and '
              'full Kubernetes authorization are not tested.',
              '- Simple lifecycle intervals, literal identifier matching and finite membership '
              'do not cover time zones, complex joins, normalization, wildcard authorization '
              'or all cross-field rules. Repeated records/templates within projects limit generalization.',
              '- The observed categories and controls do not yet establish that relationship failures '
              'recur broadly enough to justify a custom JSON Schema vocabulary. Ordinary schema '
              'constraints and application checks remain alternatives.', '',
              'Next, use a separately frozen, untouched set of harder application workflows '
              'and an explicit ordinary-schema comparator if the research question is validator '
              'or generation superiority. Investigate durable per-request logging before another '
              'long run. Do not tune the current pack after seeing its failures.', '',
              '## Reproduce and inspect', '',
              'See [the frozen protocol](protocol.json), [source attribution](SOURCES.md), '
              '[exposure audit](exposure.json), [input freeze](freeze.json), '
              '[machine-readable results](evidence/summary.json) and '
              '[public artifact manifest](evidence/manifest.json).', '',
              '```sh', 'python -m pip install -e \'.[dev]\'',
              'python -m heschema.confirmation_run',
              'python scripts/verify_confirmation_evidence.py',
              'python scripts/write_confirmation_report.py', '```', '',
              'These checks need no model credentials or new generation. Live re-execution '
              'requires authorized credentials and is a new run, not reconstruction of the '
              'same hosted-model responses.']
    (pack / 'REPORT.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    write_report()
