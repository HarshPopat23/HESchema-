# LangChain/LangGraph execution boundary

`HESchemaToolInterceptor` validates registered tool calls and returns the core
validator's parsed, assembled arguments. It does not independently replay
calculation records or treat an accepted refusal/clarification as executable.
Unknown tool names are outside the interceptor's registered scope.

`guard_tool(tool, contract, on_fail="repair", snapshot=None)` wraps available
`invoke`, `run`, `ainvoke` and `arun` entry points on mutable, duck-typed tool
objects. Signatures are preserved for positional/keyword argument binding.
All input forms reach validation; a non-dictionary input is not a bypass.
Only a validated dictionary is delivered. A serialized JSON object can be
parsed and validated; malformed input cannot reach the tool.

| Policy | Accepted arguments | Rejected arguments |
|---|---|---|
| `raise` | Invoke with the validated document | Raise `ContractViolationError`; do not invoke |
| `repair` (default) | Apply supported declared calculations, then invoke only after full acceptance | Raise if deterministic calculation/validation cannot produce accepted arguments; do not invoke |
| `refuse` | Invoke with the validated document | Wrapper returns refusal diagnostics; do not invoke |

No LLM repair callback or automatic model retry is configured by this adapter.
Unsupported failure policies raise `ValueError` during setup, before wrapping.
Interception used directly or as message middleware raises on rejection for all
policies, including `refuse`: inserting a refusal object into executable tool
arguments would not stop a downstream executor. Applications may catch the
exception to report refusal, but must not execute the rejected call afterward.
This is an intentional correction to the previous unsafe fall-through behavior.

Nested calculation targets and escaped JSON Pointer names use the exact
assembled document already validated by the core. Caller input is not mutated.
Array-index calculation targets and overlapping/dependent calculations retain
the core's existing compatibility restrictions; this adapter does not extend them.
A tool-envelope contract must describe a `call_tool` for the registered tool;
refusal and clarification envelopes do not invoke it.

Supply approved context through `snapshot` when the contract requires it.
Contract acceptance is separate from permission to act: the application still
owns authorization and side effects. These lightweight wrappers do not certify
compatibility with every LangChain release, immutable/Pydantic tool object or
custom dispatch path; use an appropriate framework adapter for unsupported
objects and do not bypass validation to accommodate them.
