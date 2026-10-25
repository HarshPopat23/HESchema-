# P2 acceptance checks (defined before implementation)

- Loading a contract path reads current bytes on each explicit load; same-size/same-mtime rewrites, atomic replacements, deletion and invalid edits cannot silently reuse an obsolete contract.
- Already-created decorators retain an explicitly documented pinned contract. Re-decoration or direct validation reloads file content.
- Rebuilding H60 uses the repository's pinned report, validates 60 unique cases, and writes reproducible output to a chosen directory. A check mode explains historical byte/semantic differences without rewriting frozen evidence.
- Authentication documentation and OpenAPI describe one shared operator. Tests verify shared-token clients share state, forged tenant headers do not create identities, and invalid credentials fail on protected routes.
- Repository lint and focused/full tests pass; only cache, rebuilding and authentication-description scope changes are included.
