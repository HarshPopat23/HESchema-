# Contract-file loading and caching

`load_contract(path)` and `guard.validate(data, path)` read the current file bytes
on each explicit call. A SHA-256 content fingerprint allows reuse of the validated
contract when the bytes are unchanged. Changes to size, modification time or
inode are not the cache authority: same-size edits with restored timestamps and
atomic file replacement are detected. File access and parsing errors propagate;
an invalid edit or deleted file never falls back silently to the old contract.

File-based loads return independent copies, so a caller modifying a returned
schema cannot poison the cached file definition. This policy concerns file
loading; passing an existing `Contract` or a dictionary retains its existing API
semantics. Cache lookup still requires reading and hashing the file; no latency
or throughput improvement is claimed. The existing process-local cache has no
new eviction policy.

## Constructed guards pin a snapshot

`@guard("contract.json")` resolves the file when the decorator is constructed.
The resulting synchronous or asynchronous wrapper, its `.contract` attribute and
its `.validate` helper keep that snapshot. Editing or deleting the file does not
silently change the rules of an already-constructed wrapper. Reconstruct the
wrapper to adopt a new contract, or use direct `guard.validate(payload, path)`
when each call must reload the path. Integrations that retain a loaded `Contract`
also need reconstruction to adopt file edits.

```python
from heschema import guard

# Resolves the current bytes each time this line executes:
result = guard.validate({"value": 2}, "contract.json")

# Resolves once, when decorated:
@guard("contract.json")
def process(value):
    return value
```

A load observes the bytes read during that call; it is not a transaction with a
later filesystem edit or execution. Writers should write a complete temporary
file and atomically replace the destination. Use immutable versioned contracts
and explicit rollout when rule changes require deployment coordination.
