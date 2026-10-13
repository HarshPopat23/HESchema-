# Collecting actual constraint needs

Use [the record schema](use-case-record.schema.json) or the GitHub issue form. Keep
whole outputs, the original schema, the desired constraint, source/context,
backend/model/version/mode, workaround, provenance, independent review status,
and publication permission. Sanitize confidential values. Permission withheld
records must not be published as raw examples.

Classify a case by what is missing:

| Category | Example | First response |
| --- | --- | --- |
| Authoring gap | Known currency must be INR | Use `const`, `enum`, or ordinary keywords |
| Provider coverage gap | Validity differs from the original schema | Probe acceptance and violations separately |
| Relationship requirement | Total must equal quantity × unit price | Compute it or use an application rule |
| Runtime context requirement | Destination must match approved Goa | Project the trusted value into the effective schema |
| Source interpretation requirement | Which account did a source document mean? | Clarify or independently verify; schema validity cannot establish it |

The included invoice record is synthetic and unreviewed. C01–C10 remain historical
pilot fixtures. Neither establishes company demand, universal keyword support,
or a recovery rate. Group paraphrases by underlying case/family. Prioritize rules
only after enough independently reviewed, permissioned cases show recurring
patterns. A vocabulary proposal is a later, separate project; required unknown
vocabularies are rejected in this release.
