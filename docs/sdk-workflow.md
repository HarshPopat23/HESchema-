# One validation-to-execution SDK workflow

## Acceptance checks (defined before implementation)

- Dry-run is the default and invokes no executor, including on valid input.
- Invalid JSON, source mismatches, relationship failures, absent/unconfirmed/expired
  approval, missing required bindings, schema-only acceptance, refusal and
  clarification cause zero executor invocations.
- An explicitly enabled execution invokes one configured synchronous callback
  exactly once, with the validated assembled document or tool arguments.
- Nested/escaped-pointer data and declared calculation outputs reach the callback
  intact. Validation does not mutate caller-owned JSON, facts or contracts.
- Configuration errors and callback exceptions are visible; callbacks are never
  retried automatically. Async callbacks are outside this synchronous API's scope.
- An offline runnable example, focused tests and the full suite verify the public
  entry point without model calls or external actions.

## Public entry point

```python
from heschema import run_workflow

# contract: Contract, definition dict, or file path
# approved: trusted context-store snapshot reviewed/confirmed by the application
# model_json: whole JSON text or a JSON-compatible Python value
preview = run_workflow(contract, approved, model_json)
print(preview["status"], preview["diagnostics"])

# Opt in only at the application's authorized execution boundary:
result = run_workflow(
    contract, approved, model_json,
    dry_run=False,
    executor=save_validated_document,
)
```

`save_validated_document` is a caller-configured synchronous function taking one
object argument. It is never selected by a model-supplied function name, import,
URL or code string. For a tool-envelope contract, configure the callback for that
contract's tool; the validator enforces the declared tool name, and the callback
receives only `arguments`. A document contract passes its entire object.

| Outcome | `status` | Callback calls |
|---|---|---|
| Accepted approved object, default dry-run | `dry_run` | 0 |
| Invalid/missing approval or rejected output | `rejected` | 0 |
| Accepted refusal/clarification or schema-only validity | `rejected` | 0 |
| Accepted approved object, explicit execution | `executed` | 1 |
| Configuration, engine or callback exception | Exception propagates | 0 before callback; at most 1 callback invocation |

`validation` contains the existing detailed stage diagnostics (or `None` if
approval failed before validation). `diagnostics` also includes workflow-level
blocking reasons. `payload` is the validated assembled object when eligible;
`execution` records whether the callback was attempted and its return value.
Callback mutation does not change the diagnostic payload or caller-owned inputs.
A result need not be JSON-serializable if the callback returns an arbitrary object.

The underlying validation decision retains `executionAuthorized: false` even
when the opt-in wrapper invokes a callback. That field does not become an
application authorization token. A successful dry-run is not a reusable permit:
call `run_workflow` again for execution, which repeats validation. No separate
"execute this old report" API is provided.

## Approval requirements

The caller supplies a trusted snapshot with a nonempty string `id`, positive
integer `version`, literal `confirmed: true`, object `data`, and optional lists
`approvedPointers`/`facts`. Pointers must use RFC 6901 syntax. Verified external
facts retain the core source/version/expiry requirements. Include `contractHash`
to bind the snapshot to the specific contract; mismatch is rejected. No approval
is inferred from model output or created by this function.

In addition to core acceptance, execution requires core `success`: at least one
active approved contract binding, every required binding satisfied, original and
effective schema checks, and the declared relationships passing. This deliberately
blocks schema-only and relationship-only contracts with no active approved
bindings from this particular workflow. Fields without declared constraints are
not proved correct. Partial approval covers only the declared approved scope.

The wrapper copies the contract, snapshot and supplied value for one invocation.
It checks approval expiry initially and immediately before invoking the callback.
It cannot observe a concurrent store invalidation through that copy: applications
must re-fetch the authoritative version and enforce ownership, authorization,
expiry and idempotency at their actual transaction boundary. A supplied owner or
`confirmed` field is an attestation by the caller, not cryptographic evidence.

## Support limits

- One synchronous call; dictionary payloads from document/tool-envelope contracts.
  No dynamic dispatch, remote tool transport, streaming or async executor API.
  Coroutine, async-generator and generator callbacks are rejected before calling.
  If a nominally synchronous callback returns deferred work, a `TypeError` is
  raised after its one invocation; preceding side effects cannot be undone.
- Draft 2020-12 and the existing documented contract bindings, relationship
  kinds and validator limits. [Contracts and repair](contracts-and-repair.md) and
  [optional application calculations](contracts-and-repair.md#optional-application-calculations) describe the core scope. Calculations
  occur only for explicitly declared `compute: application` relationships;
  supply the calculation input shape with computed target fields omitted.
  The fully assembled, revalidated nested document is passed intact.
- No model request, automatic repair, normalization or retry. Invalid contract
  configuration/files and engine failures propagate rather than appearing accepted.
  A missing executor in execution mode or non-boolean `dry_run` is a configuration
  error. Executor configuration is checked even during dry-run.
- Callback exceptions propagate and are never retried. A callback may have partially
  changed external state before failing; this API offers no rollback, distributed
  transaction or exactly-once guarantee across repeated calls/processes.
- This Python boundary cannot sandbox a hostile callback or replace service
  authentication. The HTTP API remains validation-only and single-operator.
  This feature makes no new empirical accuracy, latency or security guarantee.

When no engine is supplied, the wrapper creates and closes one for validation.
A caller-supplied `SchemaEngine` can be reused; its lifecycle remains with the
caller. Contract paths reload on each workflow invocation according to
[the file-loading policy](contract-file-loading.md).

## Run the offline example

```bash
pip install -e '.[dev]'
python examples/sdk/workflow.py
pytest -q tests/test_sdk_workflow.py
```

The example exercises default dry-run, rejected source facts and one successful
explicit callback. Its callback appends to a local list only; it performs no
booking, payment, network request or other external action. Its approved context
is an explicitly labelled engineering fixture, not a real human approval record.
