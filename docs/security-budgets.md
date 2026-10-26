# Schema budgets and regex screening

These checks are structural guards and heuristics, not a resource sandbox or a
proof that every accepted schema/regex is inexpensive.

- Schema depth counts one edge for each schema-valued child, including boolean
  schemas. The root is depth one; the default maximum is 15.
- The property budget counts entries in `properties` across syntactic schema
  occurrences; default maximum 250. Pattern-key names are screened as regexes but
  are not themselves named-property entries. Properties under each
  `patternProperties` child count once, not twice. Reusing the same Python object
  at two schema locations counts as two occurrences. The walker does not expand
  `$ref` graphs for this structural count.
- Regex strings have a default maximum length of 1000 and are checked for selected
  risky patterns and Python regex syntax. This is not complete ReDoS detection,
  nor a general proof of cross-engine regex equivalence.
- Data under `const`, `default`, `enum` and examples is not traversed as a schema.

Boundary tests demonstrate exact property/depth/regex-length limits and preservation
of screening for pattern keys. They also document the corrected duplicate traversal:
previously pattern subschemas were visited explicitly and through `schema_children`,
which could reject a schema within its declared property budget. This is an
accounting/correctness defect; no resource-exhaustion exploit was reproduced.

For untrusted deployments, separately decide request/payload size, regex/input
length, evaluation time, memory, process isolation and concurrency controls. Those
policies are not established merely by passing this walker. Do not weaken budgets
or accept arbitrary callbacks on the assumption that validation grants execution
or authorization.
