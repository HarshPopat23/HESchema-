# Publication status: raw artifacts blocked pending explicit authorization

The rerun and archive-only verification completed locally. Automatic approval review twice rejected public GitHub upload of the raw-response archive, requiring explicit permission for those exact payloads. No alternate upload route was used.

The following four prepared, credential-scanned archives are intentionally absent from this PR until authorization:

- original-receipts.jsonl.gz — original physical request/response snapshot.
- original-result-rows.jsonl.gz — original 2,157 saved rows before reconciliation.
- request-evidence.jsonl.gz — all 2,504 physical request receipts, including failures, excluded originals and replacements.
- runs.jsonl.gz — all 2,160 selected result rows after reconciliation.

They contain public-record prompts, generated final content and provider usage/metadata; credentials, headers and private-reasoning fields were excluded. Decoded message prefixes were checked against the frozen public task pack. The destination repository belongs to the requesting authenticated user. Publication nevertheless remains blocked by automatic review.

Metrics, code, protocol, hashes and missing-evidence disclosures are published for review. Independent reproduction from this PR alone remains blocked until the raw artifacts are published. The PR stays in draft. Artifact hashes describe prepared local payloads, not a claim that those payloads are already in GitHub.
