# Authentication and operator boundary

The current FastAPI service is a **single-operator prototype**. It does not issue
per-user credentials, map tenant IDs, or provide multi-tenant API isolation.
Shared database support and owner columns do not establish authenticated tenants.

| Server configuration | Protected-route behavior | Store identity |
|---|---|---|
| `HESCHEMA_API_TOKEN` configured | Require the matching bearer credential | `operator` |
| Token absent or empty | No credential required | `local-operator` |

All clients using the configured token act as the same operator. They can access
each other's state and jobs within that shared scope. `X-Tenant-ID`, `X-User-ID`
and similar caller-supplied labels do not select an identity. Confirmation records
an operator action; it does not independently authenticate a human approver or
attest to the source facts.

REST workflow, state, contract, generation and job routes use the operator
dependency. `/v1/chat/completions` separately enforces the same token and supplies
the same identity while retaining its OpenAI-compatible error envelope. OpenAPI
now describes this shared-token policy explicitly; its bearer security scheme
alone does not mean authentication is enabled on a tokenless server.

The existing `/health`, `/metrics`, `/v1/models`, documentation/OpenAPI and
frontend assets are public. Configuring a token does not protect every route.
Do not interpret CORS, client headers or a validation `PASS` as authorization for
external tool execution.

## Deployment and future scope

The CLI defaults to localhost and rejects non-loopback binding without a token.
Direct ASGI factory deployment does not supply that CLI check; keep tokenless
instances local. Use TLS and control access to public operational endpoints when
deploying behind a proxy. A reverse proxy's per-user login does not create isolated
backend tenants if every request still uses the same backend token.

Library storage methods accept owner strings and enforce owner/version predicates,
but a library caller must obtain that identity from a trusted source. API clients
cannot establish it merely by choosing an owner string. No tenant-isolation
implementation is added here: it is a product/security design decision requiring
trusted identity mapping, scoped state/contracts/jobs, authorization and isolation
tests across every relevant endpoint before claiming support.
