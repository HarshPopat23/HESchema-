# Local experiment jobs

`JobManager` is a single-process background experiment helper. Its job dictionary,
async tasks, active-job lock and cancellation events live in that Python process.
SQLite/PostgreSQL contract/state storage does not turn these into shared queue state.

| Situation | Current behavior |
|---|---|
| Same manager/process | Tracks running jobs and enforces its per-operator active-job check |
| Cancellation | Signals/cancels that manager's local task; does not cancel remote-provider billing or roll back completed requests |
| Process restart | Does not resume queued/running tasks or recover cancellation/active-job locks |
| Completed report file remains | `get_job` may synthesize a completed record and read reports; this is report rediscovery, not durable execution recovery |
| Two API workers | Separate dictionaries/tasks/locks; no shared active-job admission or cross-worker cancellation guarantee |

In-memory job lookup checks owner identity (with the existing `operator` bypass).
Completed-report fallback constructs a record using the requesting identity; it
does not restore original owner metadata. The HTTP API is currently
[single-operator](authentication.md); this behavior must not be represented as
persisted tenant isolation. Do not expose a shared job-report directory as a
multi-tenant authorization boundary.

Run local experiments with one API worker. Stop/wait for active jobs before a
planned restart and inspect the saved study evidence before resuming experiments.
A process death can leave partial request/response evidence; a saved output file
is not proof that the whole job finished or that replay is safe. Existing evidence
rules remain applicable.

No durable scheduler is added here. Before supporting a hosted multi-worker use
case, define durable ownership, restart/reconciliation, admission, leases and
cancellation acknowledgement semantics, then test crashes, duplicate delivery,
wrong-owner access and cross-worker cancellation against real shared storage.
Build that only when an actual supported deployment requires it.
