# SDK adapter support matrix

These are distinct interfaces, not interchangeable execution/approval guarantees.
The installed versions used in CI provide the tested envelope; this is not a
promise of compatibility with every Pydantic or LangChain release.

| Interface | Approved context | Acceptance / rejection | Calculations and handoff | Execution scope |
|---|---|---|---|---|
| `run_workflow` | Trusted confirmed snapshot required; active bindings required for execution | Blocks rejection, controls and schema-only outcomes; default dry-run | Declared application calculations; complete validated object/arguments copied to callback | One explicit synchronous object callback; no automatic retries/transactions |
| `guard.validate` | Optional snapshot | Returns core diagnostics; accepted control/schema-only responses are possible | Supports declared calculations; inspect parsed assembled output | No function execution |
| `@guard` | Snapshot or callable snapshot | `raise`, `refuse`, `repair`; invalid policy rejected at construction; validation exceptions may propagate | Applies supported calculated fields to bound function arguments | Sync/async functions; acceptance is not a business authorization decision |
| `contract_from_model` | Emits declarations; does not obtain approval | Converts nonrecursive Pydantic v2 schemas; cycles fail clearly | Contract construction only | None |
| `@guarded_model` | No snapshot parameter; required bindings without evidence cannot succeed | Document models only; `raise` / `repair` only; rejects before Pydantic initialization | Hands the core's complete parsed/assembled document to the original initializer | Wrapped direct keyword construction only; not an external-action gate |
| LangChain interceptor / wrapped tool | Snapshot supported by documented integration methods | Registered tools checked; controls are not executable; unknown tools are outside registered scope | Complete validated assembled arguments | Mutable duck-typed tool methods; not universal BaseTool/Pydantic wrapper compatibility |

For `guarded_model`, both supported policy names use only declared deterministic
calculations. Neither invokes a model for repair. `refuse` cannot return an
arbitrary refusal document from a model constructor and is rejected explicitly,
as are tool-envelope models and positional input. Supply nested model data as
JSON-compatible dictionaries; arbitrary already-constructed BaseModel objects
are not part of this adapter's input contract. Pydantic may apply its own declared
normalization/defaults after HESchema validates the JSON representation; custom
validators/post-init hooks remain developer code, not a sandbox.

`guarded_model` coverage is for direct keyword construction through its wrapped
`__init__`. It does not certify every Pydantic entry point: `model_construct`,
copy/update, serialization, custom validators and other bypasses are not an
execution or authorization boundary.

A nested calculation target such as `/invoice/total` or
`/invoice/a~1b~0c` must preserve the entire invoice and its sibling fields. The
Pydantic adapter now delegates assembly to the core and forwards the result,
rather than replaying the first pointer segment. The independent regression
checks cover nested/escaped targets, sibling retention, input immutability and
rejection before model post-init.

Use [the workflow](sdk-workflow.md) for approved facts → diagnostics → dry-run →
explicit callback. Use [the LangChain boundary](langchain-execution.md) only within
its documented registration/mutability limits. Contracts, Python callbacks,
Pydantic validators and approval sources are trusted application inputs.
