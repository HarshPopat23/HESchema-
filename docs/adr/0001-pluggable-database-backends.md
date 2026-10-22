# ADR-0001: Pluggable Database Backends (SQLite & PostgreSQL) for Distributed Multi-Pod Scaling

**Date**: 2026-10-22
**Status**: accepted
**Deciders**: JHSchema Engineering Team

## Context

JHSchema originally relied exclusively on local SQLite databases (`state.sqlite3`) for `StateStore` and `ContractRegistry`.
While SQLite with Write-Ahead Logging (WAL) and `busy_timeout = 5000` provides fast single-node operations with zero reader blocking, it creates operational bottlenecks in enterprise deployments:
1. Scaling across multiple Kubernetes pods or serverless containers causes fragmented state across separate local pod filesystems.
2. Horizontal scaling required either sticky load-balancer routing or networked file systems (NFS/EFS) which suffer from file-lock latency and POSIX advisory lock fragility under high concurrency.
3. Teams running in Google Kubernetes Engine (GKE), Amazon EKS, or Cloud Run require a centralized, horizontally scalable transactional state layer.

## Decision

We introduce a pluggable dual-backend architecture for `StateStore` and `ContractRegistry`:
1. **URI-Driven Factory Pattern:** `StateStore` and `ContractRegistry` inspect the connection target.
   - If the target starts with `postgresql://` or `postgres://`, they instantiate `PostgresStateStore` / `PostgresContractRegistry` powered by `psycopg` (v3).
   - If the target is a filesystem path or `sqlite://`, they instantiate the high-performance `SQLiteStateStore` (with WAL and busy timeout).
2. **Environment Variable Configuration:** The API service (`create_app`) discovers the database via:
   `HESCHEMA_DATABASE_URL` -> `HESCHEMA_DB` -> default fallback (`data/state.sqlite3`).
3. **Optimistic Concurrency & Transactional Parity:**
   Both backends implement identical state versioning semantics:
   - `confirm`: Atomic conditional update on `(id, owner, version)` asserting exactly 1 modified row.
   - `replace`: Atomic conditional increment `version = version + 1, confirmed = false` asserting exactly 1 modified row.
   - Context approvals, facts, and invalidations maintain identical RFC 6901 pointer checks.

## Alternatives Considered

### Alternative 1: Distributed SQLite via LiteFS / rqlite
- **Pros**: Retains SQLite query engine.
- **Cons**: Adds operational sidecar complexity, requires FUSE mounts, and complicates cloud-managed database integration.
- **Why not**: Enterprise users overwhelmingly standardise on managed PostgreSQL (AWS RDS/Aurora, GCP Cloud SQL, Supabase, Neon).

### Alternative 2: Heavy ORM (SQLAlchemy / Tortoise-ORM)
- **Pros**: Abstract database dialects.
- **Cons**: Substantial memory overhead, slower initialization, and redundant abstraction given JHSchema's concise relational schema (only 3 tables: `states`, `contexts`, `contracts`).
- **Why not**: Lightweight, high-performance native drivers (`sqlite3` and `psycopg`) maintain zero-overhead execution and exact transactional guarantees.

## Consequences

### Positive
- **Multi-Pod Horizontal Scaling**: Multiple JHSchema instances can run concurrently behind a standard round-robin ingress/load balancer sharing the same PostgreSQL cluster.
- **Full Backward Compatibility**: 100% compatibility with local dev environments, tests, and single-node setups using SQLite.
- **Zero Lock Thrashing**: Relies on PostgreSQL row-level locks (MVCC) without file-level locks.

### Negative
- PostgreSQL deployments require network access and credentials to a Postgres database.
