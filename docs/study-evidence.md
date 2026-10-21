# Durable response evidence for new studies

The earlier pilot reported one planned result that could not be verified. The
subsequent confirmation runner exposed another durability gap: a whole slot was
saved only after generation, validation and any repair finished. A process exit
could lose a returned initial answer, its usage, or a repair while leaving an
apparently resumable slot. A flushed JSONL stream alone did not protect every
write against an interrupted filesystem update.

This change prevents new study results from advancing ahead of saved evidence.
It does **not** recover historical missing responses or change historical scores.

## Ordering and files

The benchmark, controlled decoding, repair-feedback and confirmation runners now
use `request-evidence-v1`. Controlled-decoding warmups use a separate evidence
directory and are excluded from measured task totals.

1. Before calling the adapter, atomically save a request receipt with the slot,
   attempt number, random request ID and hash of the exact message list.
2. Immediately after the adapter returns, sync its exact final content, reported
   input/output token counts, model identity and permitted metadata to that
   receipt. Do this before validation, scoring, repair or progress updates.
3. Save returned repairs the same way. An explicitly replayed first answer is
   labeled `replayed`; it is not a new provider request or new token usage.
4. Verify references and response contents, then atomically commit the complete
   result under `request-evidence/results/`. A status cannot substitute for a
   missing receipt. Each result links its ledger to content-hashed receipts.
5. Append and sync `runs.jsonl`, then update progress or summaries. If interrupted
   between steps 4 and 5, restore the committed row once without model calls.

Atomic files use a same-directory temporary file, `flush`, `os.fsync` and
`os.replace`. POSIX directory entries, including newly created directories, are
also synced. Python documents the need to flush buffered file objects before
[`os.fsync`](https://docs.python.org/3.12/library/os.html#os.fsync), and the
same-filesystem replacement behavior of
[`os.replace`](https://docs.python.org/3.12/library/os.html#os.replace).
Filesystem/hardware guarantees still apply; this is not protection against disk
loss. Windows file syncing and replacement are supported, but directory syncing
is POSIX-only. Do not claim identical power-loss durability on every filesystem.

Each output directory contains:

- `request-evidence/requests/<id>.json`: started, returned, failed or replayed
  receipts. Returned final content preserves whitespace, fences and invalid JSON.
- `request-evidence/results/<id>.json`: result rows and integrity hashes.
- `evidence_schedule.json`: expected slots, including not-yet-started work.
- `evidence_report.json`: verified records, missing results, unknown requests and
  missing usage, plus observed usage from **all** saved returned receipts.
- `runs.jsonl`: the existing result format, extended with evidence references.

"Raw response" here means the adapter's exact final model content. It is not a
byte-for-byte HTTP response body. Reasoning fields, authorization headers, other
HTTP headers and provider error bodies are excluded from the receipt. Existing
private result logs may contain the adapter's reasoning field; keep run directories
private and use the scoped exporter before sharing. Request receipts store prompt
hashes, not plaintext requests or credentials.

## Missing means unknown

Run an offline check without initializing any model:

```sh
heschema evidence-audit results/my-run
```

The command writes `evidence_report.json` and exits nonzero if evidence is
incomplete or planned slots lack results. Per-row outcomes remain separate from
evidence completeness: a response can be correct while usage is unavailable.

| Recorded situation | Audit behavior |
|---|---|
| Started receipt with no saved return | `response_missing_unknown_outcome`; no inferred answer, tokens or cost |
| Saved response without a committed result | `result_missing`; preserve content/usage and stop automatic resume |
| Result committed before its log append | Restore its row once; no new generation |
| Returned answer with absent token counts | `usage_missing`; preserve `null`, disable complete-evidence comparison claims |
| Explicit provider rejection | Save sanitized failure, do not invent response content or rejected-request usage |
| Missing/deleted/corrupt receipt or result | Reject verification and stop resume before another call |
| Legacy result without receipts | `legacy_unverified`; its status or expected answer cannot prove its response |
| Planned slot not yet committed | List it under `missingResultSlots`; do not count it as measured success |

`observedReturnedUsage` includes orphaned returns and earlier attempts as well as
completed results. It excludes replayed source answers and never claims account
billing or usage of requests for which no response was saved. A known subtotal
is distinguished from an unknown total. It is not necessarily the same scope as
the paired-only token metric in a research report.

On unresolved or corrupt evidence, automatic resume fails closed. Preserve the
entire directory and inspect the audit. A saved response with no result can be
scored offline in a separately reviewed recovery, but this patch does not silently
redo evaluation or replace it with a fresh model output. A started request may
have completed remotely: neither its output nor its billing can be reconstructed
locally. Exactly-once remote execution is not guaranteed.

One process owns each output directory; its async workers use unique receipt
IDs. Multiple processes must use separate directories. Synchronous syncing adds
local overhead. Response-persistence time remains outside provider request wall
time; result commit and report writes are outside coordinator latency. No
performance improvement is claimed.

## Historical evidence and frozen studies

New configs record `evidenceVersion`. Do not resume an older directory under the
new implementation or add receipts based on its expected answers. Reproduce
old runs using their recorded commit. `scripts/resume_confirmation.py` copies
new receipts and result commits when resuming a compatible new run; runtime
hash/config guards still apply.

The frozen confirmation source data, public responses, original report and its
recording limitations remain unchanged. The archived standalone
`research/contract-main-study-v1/runner/` is preserved for historical
reproduction; it has not been silently migrated to this protocol. Legacy runs
must not be presented as having the new durability guarantees. This patch
covers the current package's four study paths, not interactive API calls.

Tests cover real abrupt subprocess exit after a returned response, interruptions
during repair, a committed result missing its log append, missing usage,
deleted/tampered evidence, truncated logs, disk-write failure, legacy rows and
provider rejections. Mock/test responses are engineering controls, not new
empirical evidence for HESchema accuracy or speed.
