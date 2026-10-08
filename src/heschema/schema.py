"""Checked schema registration and bounded evaluator caches."""

import copy
import os
import subprocess
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, SchemaError

from .jsonio import canonical, digest, loads

DIALECT = "https://json-schema.org/draft/2020-12/schema"


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

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"$ref", "$dynamicRef"} and not value.startswith("#"):
                    raise ValueError("External schema references must be bundled before registration")
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

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
        self.lock = threading.RLock()
        self.worker = None

    def register(self, schema):
        key = digest(schema)
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return key
            check_schema(schema)
            validator = Draft202012Validator(copy.deepcopy(schema), format_checker=FormatChecker())
            if self.backend == "blaze":
                # This CLI compiles using native Blaze. No homemade replacement or 10x claim.
                with tempfile.TemporaryDirectory(prefix="heschema-schema-") as folder:
                    source = Path(folder) / "schema.json"
                    source.write_text(canonical(schema), encoding="utf-8")
                    completed = subprocess.run(
                        [os.getenv("JSONSCHEMA_CLI", "jsonschema"), "compile", str(source), "--fast"],
                        capture_output=True, text=True, timeout=30, check=True, env=child_environment(),
                    )
                    template = loads(completed.stdout)
                if self.worker is None:
                    self.worker = BlazeWorker()
                self.worker.request({"op": "compile", "id": key, "template": template})
            self.cache[key] = validator
            if len(self.cache) > self.capacity:
                old, _ = self.cache.popitem(last=False)
                if self.worker:
                    self.worker.request({"op": "drop", "id": old})
            return key

    def errors(self, schema, instance):
        with self.lock:
            key = self.register(schema)
            # Python remains an independent cross-check and enforces formats: the JS
            # Blaze port does not support Format Assertion yet. IPC costs are reported.
            native = self.worker.request({"op": "validate", "id": key, "instance": instance}) if self.worker else None
            errors = [{"code": "SCHEMA_INVALID", "path": "/" + "/".join(map(str, e.absolute_path)),
                       "keyword": e.validator, "message": e.message}
                      for e in self.cache[key].iter_errors(instance)]
            if native and not native["valid"] and not errors:
                errors.append({"code": "ENGINE_DISAGREEMENT", "path": "/", "message": "Blaze rejected an instance accepted by the reference evaluator"})
            return errors

    def close(self):
        if self.worker:
            self.worker.close()
