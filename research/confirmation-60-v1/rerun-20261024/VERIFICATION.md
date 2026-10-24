# Verification and evidence exceptions

## Passed

- 61 oracle/control tests; all 60 references, incorrect controls and alternative membership choices checked.
- Full Python suite: 1,082 passed, 10 optional skips, one dependency deprecation warning. The audit environment explicitly installed undeclared pytest-asyncio and psycopg test requirements.
- Focused Ruff checks of the new study scripts and test file.
- 12-slot engineering pilot with matching receipts, excluded from replication results.
- All 2,160 selected slot contents and usage matched their selected receipts; 2,156 slots remain in the primary matched comparison.
- Archive-only verification succeeded without individual receipt files or uncompressed rows.
- Frozen generation implementation hashes remained unchanged during inference.
- Unlazy ledger: four gates met; three runnable gates reverified, one manual PR-publication check.
- Credential-pattern scan tested with a positive control and applied to release data/code.

## Failed / excluded

- Initial clean declared install: five tests failed because async/PostgreSQL test dependencies were undeclared. They pass after explicitly installing those dependencies.
- Repository-wide Ruff: 34 pre-existing issues. GitHub's Python matrix failed at that step; other Python versions were cancelled. GitHub's Blaze job passed.
- Three derived result rows were missing despite complete provider receipts; those rows were recovered with explicit provenance.
- Two original initial receipts remained in started state. Their original rows/receipts are preserved; two slots were regenerated with at most one repair. Their whole matched group is excluded from the primary comparison. The missing-write root cause is not established.
- The original investigator summary is preserved as original-summary.json; summary.json describes the selected rows after reconciliation.

## Not established / blocked measurements

- Original missing provider receipts cannot be reconstructed as authenticated provider metadata. Replacements do not erase that loss.
- Verified billing, total physical usage for the two incomplete original returns, full user-visible latency decomposition, and real-production generalization are not established.
- The historical public-source snapshot ZIP was unavailable in this checkout; upstream bytes were not independently recaptured.
- No general accuracy or speed improvement, universal zero-error guarantee, or need for new vocabulary is claimed.

See REPORT.md, reconciliation.json, original artifacts and the physical receipt archive for the data behind these limitations.

## Publication blocked

Automatic approval review rejected public upload of raw-response archives twice. Prepared archives remain local; this draft PR contains code, summaries and hashes. Explicit user approval is required for the four payloads listed in PUBLICATION_STATUS.md. Local verification must not be confused with publicly reproducible evidence.
