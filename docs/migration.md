# Protocol 2 migration

Baseline: `sourcemeta-cli-integration` at f36d3ef, based on main 35571f7.
Python baseline: 555 passed, 6 optional native tests skipped. Native baseline:
6 passed with the repository's npm packages. Ruff and JavaScript syntax passed.
No inference requests were made.

Existing domain/state endpoints and schema-richness report fields remain supported.
New contract endpoints and controlled experiments use protocolVersion 2. Stage
states are valid, invalid, not_evaluated, needs_context, and unknown. An absent
output maps to null legacy JSON/schema booleans, never a successful check.
`jsonValid` in a CLI run remains the legacy stdout-report parsing flag;
`reportJsonValid` is its explicit replacement. `generatedContent` and diagnostics
refer only to a report's explicit document/raw field, including on nonzero exit.
Missing finish metadata now remains null. Reasoning is separate from final content.

New benchmark configurations include protocol fields in their resume fingerprint.
Use a fresh directory for protocol 2; historical files are not modified.
`adapt_report` offers a labeled read-only view of older reports. Existing benchmark
repair default remains two; runtime and controlled first-pass experiments default
to zero. A validation decision never grants execution permission.
