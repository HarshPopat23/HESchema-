# P1 correctness and persistence boundaries

This main-targeted recovery brings the missing changes from PR #13 onto the
current main branch. PR #13 merged into the old PR #12 feature branch, so its
merged status did not establish main availability. Development extras/lint and
the later SDK/cache/policy fixes are already on main and remain intact. This
recovery does not rewrite historical model results or claim a performance improvement.

## Acceptance checks

- PostgreSQL connection, statement and transaction-commit failures propagate;
  registration does not update its cache on a failed write.
- A missing persisted row cannot count as successful registration.
- Independent processes see committed registrations through `get` and `list`;
  conflicting definitions cannot overwrite an immutable contract/version.
- Committed contracts survive a real PostgreSQL server restart.
- The original H60 runner uses the independent task oracle for all four arms,
  including valid membership alternatives and application-assembled outputs.
  Resuming old records recomputes scores from raw responses. Missing evidence
  prevents resume rather than silently trusting old scores.
- Recursive Pydantic models fail with a specific compatibility error. Repeated
  references to the same nonrecursive model remain supported.
- A fresh `pip install -e '.[dev]'` supplies async and PostgreSQL test dependencies;
  `ruff check src tests` and the full unit suite pass without new suppressions.

## PostgreSQL behavior

Selecting a PostgreSQL DSN requires a functioning database. Initialization and
writes no longer fall back silently to memory. Database exceptions reach callers;
callers must report a failure rather than a successful durable write. PostgreSQL
reads query durable storage instead of an instance's startup cache, so a worker
can see another worker's committed registrations. No automatic retry is added:
connection loss during commit can leave an uncertain outcome. Re-registering the
same immutable definition is idempotent, and callers can verify it after recovery.

The database's `(id, version)` primary key and `ON CONFLICT DO NOTHING` serialize
competing inserts. The following read checks the winning definition before the
connection context commits. SQLite and memory-only behavior remain unchanged.
Database permissions and durability configuration remain deployment responsibilities.

### Real server check

Use a disposable PostgreSQL database and set `HESCHEMA_TEST_POSTGRES_DSN` in the
environment. Do not commit credentials. Run from the repository after installing
`.[dev]`:

```bash
python scripts/check_registry_postgres.py before /tmp/registry-restart.json
# Restart that actual PostgreSQL server using its deployment's normal command.
python scripts/check_registry_postgres.py after /tmp/registry-restart.json
```

The first phase launches independent Python processes, tests different-definition
conflicts and identical-definition idempotency, and verifies reads through an
already-created registry. The second phase verifies the saved definitions after
the server restart, then removes only those test contracts. The state file contains
contract data, not the DSN. CI's `postgres-registry` job explicitly restarts its
PostgreSQL 16 service container between phases. Mocked failure-path tests are
separate and are not evidence of a real restart.

## Scoring boundaries

Detector acceptance controls repairs; independent correctness is a different
measure. The frozen H60 task oracle in `rescore_confirmation60.py` checks source
bindings and relationships independently of HESchema's detector flags, accepts
valid membership alternatives, and reconstructs eligible D calculations. This
is the existing task-specific oracle, not a universal oracle for arbitrary tasks.
Existing verified/reconciliation wrappers inherit the corrected base evaluator.
No old raw records or published results are rewritten by this patch. Resume
prints an explicit re-scoring notice; new summaries identify the independent
oracle as `independent-h60-v1`. Loading saved rows does not rewrite the JSONL.

## Pydantic compatibility

`contract_from_model` still inlines nonrecursive local `$defs`. Direct and mutual
recursion cannot be represented by that finite expansion, so conversion raises
`ValueError` naming the recursive reference. Users needing recursion can supply an
explicit bundled JSON Schema contract. This does not claim recursive Pydantic
conversion support or add a new reference-resolution engine.
