# Public evidence status

This commit publishes the completed report, aggregate results, protocol, study code and regression controls. It does not publish raw-response archives, credential files, local environment paths or per-request message bodies.

The selected 2,160 outputs were verified locally against saved content and usage receipts. Nine older physical receipts still have unknown terminal evidence. The primary comparison excludes all eight groups affected by interruptions or cross-session allocation. Public hashes do not recover missing responses.

`EVIDENCE_INDEX.json` fingerprints sets of local manifests, receipts and selected-result files without including their content. `FINISHED_SUMMARY.json` provides aggregates. Independent raw-response replay from the public checkout alone is therefore blocked. The private evidence archive supplied to the owner retains all saved artifacts and the historical interruptions.

The report's 1,091 passing local tests (10 optional skips, one dependency warning) describe the recorded verification environment, not unobserved remote CI. Seven study acceptance gates passed; two historical completion gates remain abandoned with reasons. The new three-session completion check passed. There are no unfinished scheduled result identities.
