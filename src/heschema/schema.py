"""Checked schema registration and bounded evaluator caches."""

import copy
import os
import subprocess
import tempfile
import threading
import time
from collections import OrderedDict
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, SchemaError

from .diagnostics import pointer, schema_error
from .jsonio import canonical, digest, loads

DIALECT = "https://json-schema.org/draft/2020-12/schema"


def schema_children(node):
    """Visit schema-valued keywords, never JSON data inside const/enum/default/examples."""
    for keyword in ('properties', 'patternProperties', '$defs', 'dependentSchemas'):
        for name, child in node.get(keyword, {}).items():
            yield (keyword, name), child
    for keyword in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
        for index, child in enumerate(node.get(keyword, [])):
            yield (keyword, index), child
    for keyword in ('items', 'contains', 'not', 'if', 'then', 'else', 'additionalProperties',
                    'unevaluatedProperties', 'unevaluatedItems', 'propertyNames', 'contentSchema'):
        if keyword in node:
            yield (keyword,), node[keyword]


def child_environment():
    """Compiler/evaluator subprocesses do not need provider keys or API tokens."""
    allowed = {"PATH", "HOME", "TMPDIR", "TMP", "TEMP", "SystemRoot", "COMSPEC", "LANG", "LC_ALL", "LD_LIBRARY_PATH"}
    return {key: value for key, value in os.environ.items() if key in allowed}


def check_schema(schema):
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError(f"Invalid JSON Schema: {exc.message}") from None
    if isinstance(schema, dict) and schema.get("$schema", DIALECT) != DIALECT:
        raise ValueError("This release accepts Draft 2020-12 only; convert other dialects explicitly")
    known_vocabularies = {'https://json-schema.org/draft/2020-12/vocab/' + name for name in
                          ('core', 'applicator', 'validation', 'unevaluated', 'meta-data', 'format-annotation', 'format-assertion', 'content')}
    if isinstance(schema, dict) and any(required and uri not in known_vocabularies for uri, required in schema.get('$vocabulary', {}).items()):
        raise ValueError('Required custom vocabulary is not implemented; use declared application rules')

    def walk(node):
        if isinstance(node, dict):
            for key in ("$ref", "$dynamicRef"):
                if key in node and not node[key].startswith("#"):
                    raise ValueError("External schema references must be bundled before registration")
            for _, child in schema_children(node):
                walk(child)

    walk(schema)


def typed_minimal(schema):
    """Preserve field meanings and required fields; remove extra validation constraints."""
    check_schema(schema)

    def simplify(node):
        if isinstance(node, bool):
            return node
        result = {k: copy.deepcopy(node[k]) for k in ("type", "description", "required") if k in node}
        if "properties" in node:
            result["properties"] = {k: simplify(v) for k, v in node["properties"].items()}
        if "items" in node:
            result["items"] = simplify(node["items"])
        return result

    if isinstance(schema, bool) or schema.get("type") != "object" or "properties" not in schema:
        raise ValueError("Automatic minimal arm requires an object with properties; supply --minimal-schema otherwise")
    return {"$schema": DIALECT, **simplify(schema)}


class BlazeWorker:
    """One Node worker, compiled templates cached in-process; no subprocess per evaluation."""

    def __init__(self):
        root = Path(__file__).resolve().parents[2]
        self.process = subprocess.Popen(
            ["node", str(root / "native/blaze-worker.mjs")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1,
            env=child_environment(),
        )
        self.lock = threading.Lock()

    def request(self, request):
        # The worker handles only local data and never receives model/API credentials.
        with self.lock:
            if self.process.poll() is not None:
                raise RuntimeError("Blaze worker unavailable; install native dependencies")
            self.process.stdin.write(canonical(request) + "\n")
            self.process.stdin.flush()
            import select
            # POSIX service support; Windows users can use the default Python engine.
            ready, _, _ = select.select([self.process.stdout], [], [], 30)
            if not ready:
                self.process.kill()
                raise TimeoutError("Blaze evaluator timed out")
            result = loads(self.process.stdout.readline())
            if "error" in result:
                raise RuntimeError(result["error"])
            return result

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)


class SchemaEngine:
    def __init__(self, backend="jsonschema", capacity=128):
        if backend not in {"jsonschema", "blaze"}:
            raise ValueError("Unknown validation backend")
        self.backend, self.capacity = backend, capacity
        self.cache = OrderedDict()
        self.schema_locations = {}
        self.lock = threading.RLock()
        self.worker = None
        self.timings = threading.local()

    def timing_snapshot(self):
        return getattr(self.timings, 'values', {}).copy()

    def timing_delta(self, before):
        return {k: v - before.get(k, 0) for k, v in self.timing_snapshot().items()}

    def register(self, schema):
        key = digest(schema)
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return key
            check_schema(schema)
            validator = Draft202012Validator(copy.deepcopy(schema), format_checker=FormatChecker())
            locations = {}
            def collect(node, path=()):
                if isinstance(node, dict):
                    locations[id(node)] = pointer(path)
                    for tokens, child in schema_children(node):
                        collect(child, (*path, *tokens))
            collect(validator.schema)
            if self.backend == "blaze":
                # This CLI compiles using native Blaze. No homemade replacement or 10x claim.
                with tempfile.TemporaryDirectory(prefix="heschema-schema-") as folder:
                    source = Path(folder) / "schema.json"
                    source.write_text(canonical(schema), encoding="utf-8")
                    completed = subprocess.run(
                        [os.getenv("JSONSCHEMA_CLI", "jsonschema"), "compile", str(source), "--fast", "--default-dialect", DIALECT],
                        capture_output=True, text=True, timeout=30, check=True, env=child_environment(),
                    )
                    template = loads(completed.stdout)
                if self.worker is None:
                    self.worker = BlazeWorker()
                self.worker.request({"op": "compile", "id": key, "template": template})
            self.cache[key] = validator
            self.schema_locations[key] = locations
            if len(self.cache) > self.capacity:
                old, _ = self.cache.popitem(last=False)
                self.schema_locations.pop(old, None)
                if self.worker:
                    self.worker.request({"op": "drop", "id": old})
            return key

    def errors(self, schema, instance):
        with self.lock:
            started = time.perf_counter()
            key = self.register(schema)
            registered = time.perf_counter()
            # Python remains an independent cross-check and enforces formats: the JS
            # Blaze port does not support Format Assertion yet. IPC costs are reported.
            native = self.worker.request({"op": "validate", "id": key, "instance": instance}) if self.worker else None
            native_done = time.perf_counter()
            errors = [schema_error(e, self.schema_locations[key]) for e in self.cache[key].iter_errors(instance)]
            if native and not native["valid"] and not errors:
                errors.append({"code": "ENGINE_DISAGREEMENT", "path": "", "instanceLocation": "", "stage": "schema", "repair": "stop", "message": "Blaze rejected an instance accepted by the reference evaluator"})
            cumulative = self.timing_snapshot()
            for name, duration in {'registrationMs': registered - started,
                                   'nativeIpcMs': native_done - registered if native is not None else 0,
                                   'pythonReferenceMs': time.perf_counter() - native_done}.items():
                cumulative[name] = cumulative.get(name, 0) + duration * 1000
            self.timings.values = cumulative
            return errors

    def close(self):
        if self.worker:
            self.worker.close()
