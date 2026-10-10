"""Sourcemeta JSON Schema CLI integration harness and diagnostics."""

import asyncio
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from .jsonio import canonical, loads
from .providers import ROOT
from .schema import SchemaEngine

CLI_PAIRS = {
    "C01": {
        "id": "C01",
        "title": "C01. Support ticket: required fields and enums",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Normalize this support ticket: ID TKT-0042; the user cannot sign in; severity high; priority 1; unresolved. Produce fields ticketId, summary, severity, priority, resolved. Do not add suggested fixes.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "ticketId": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Ticket ID.",
                    "pattern": "^TKT-[0-9]{4}$",
                },
                "summary": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Concise summary of the reported problem.",
                    "maxLength": 120,
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Reported severity.",
                },
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 3,
                    "description": "Reported priority: 1 is highest.",
                },
                "resolved": {
                    "type": "boolean",
                    "description": "True only if explicitly resolved.",
                },
            },
            "required": ["ticketId", "summary", "severity", "priority", "resolved"],
            "additionalProperties": False,
        },
        "expected": {
            "ticketId": "TKT-0042",
            "summary": "The user cannot sign in.",
            "severity": "high",
            "priority": 1,
            "resolved": False,
        },
        "notes": "Required fields, extra-key exclusion, enum, bounded integer and true JSON boolean. Summary wording may vary; judge its meaning manually.",
    },
    "C02": {
        "id": "C02",
        "title": "C02. Invoice: cents and derived total",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Normalize invoice INV-0008: two units at USD 12.50 per unit, no tax or discount. Produce invoiceId, currency, quantity, unitPriceMinor, totalMinor. Monetary values must be integer cents.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "invoiceId": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Invoice ID.",
                    "pattern": "^INV-[0-9]{4}$",
                },
                "currency": {
                    "type": "string",
                    "enum": ["INR", "USD", "EUR"],
                    "description": "Currency code.",
                },
                "quantity": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of units.",
                },
                "unitPriceMinor": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Price per unit in integer minor units.",
                },
                "totalMinor": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10000000,
                    "description": "Quantity multiplied by unitPriceMinor, in integer minor units.",
                },
            },
            "required": ["invoiceId", "currency", "quantity", "unitPriceMinor", "totalMinor"],
            "additionalProperties": False,
        },
        "expected": {
            "invoiceId": "INV-0008",
            "currency": "USD",
            "quantity": 2,
            "unitPriceMinor": 1250,
            "totalMinor": 2500,
        },
        "notes": "Numeric types and monetary normalization. Schema validity does not verify totalMinor = quantity * unitPriceMinor.",
    },
    "C03": {
        "id": "C03",
        "title": "C03. Nullable field: do not invent unknown facts",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Normalize customer record CUST-0003: display name Asha, marketing consent declined, age not provided. Produce customerId, displayName, marketingConsent, age. Represent the unknown age as null.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "customerId": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Customer identifier.",
                    "pattern": "^CUST-[0-9]{4}$",
                },
                "displayName": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Given display name.",
                },
                "marketingConsent": {
                    "type": "boolean",
                },
                "age": {
                    "type": ["integer", "null"],
                    "minimum": 0,
                    "maximum": 120,
                    "description": "Null when unknown; never infer an age.",
                },
            },
            "required": ["customerId", "displayName", "marketingConsent", "age"],
            "additionalProperties": False,
        },
        "expected": {
            "customerId": "CUST-0003",
            "displayName": "Asha",
            "marketingConsent": False,
            "age": None,
        },
        "notes": "Nullable required field versus a missing key, false versus the string false.",
    },
    "C04": {
        "id": "C04",
        "title": "C04. Nested order: objects and bounded array",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Normalize order ORD-0012. Customer name Asha. Ship to city Pune, country IN. Items: SKU-0007 quantity two; SKU-0042 quantity one. Produce orderId, customer (name), shipping (city, country), and items (sku, quantity). Keep the item order.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "orderId": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Order identifier.",
                    "pattern": "^ORD-[0-9]{4}$",
                },
                "customer": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Customer name.",
                        },
                    },
                    "required": ["name"],
                    "additionalProperties": False,
                },
                "shipping": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Shipping city.",
                        },
                        "country": {
                            "type": "string",
                            "enum": ["IN", "US", "GB"],
                            "description": "Country code.",
                        },
                    },
                    "required": ["city", "country"],
                    "additionalProperties": False,
                },
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "sku": {
                                "type": "string",
                                "minLength": 1,
                                "description": "SKU identifier.",
                                "pattern": "^SKU-[0-9]{4}$",
                            },
                            "quantity": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "description": "Unit count.",
                            },
                        },
                        "required": ["sku", "quantity"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["orderId", "customer", "shipping", "items"],
            "additionalProperties": False,
        },
        "expected": {
            "orderId": "ORD-0012",
            "customer": {"name": "Asha"},
            "shipping": {"city": "Pune", "country": "IN"},
            "items": [
                {"sku": "SKU-0007", "quantity": 2},
                {"sku": "SKU-0042", "quantity": 1},
            ],
        },
        "notes": "Correct nesting, item schemas and array bounds; do not flatten into extra root keys.",
    },
    "C05": {
        "id": "C05",
        "title": "C05. oneOf: exclusive contact branches — advanced probe",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Normalize a contact preference: email channel, address asha@example.org, no phone number supplied. Produce channel, email and phone; use null for the inactive phone field.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "enum": ["email", "sms"],
                    "description": "Selected contact channel.",
                },
                "email": {
                    "type": ["string", "null"],
                },
                "phone": {
                    "type": ["string", "null"],
                },
            },
            "required": ["channel", "email", "phone"],
            "additionalProperties": False,
            "oneOf": [
                {
                    "properties": {
                        "channel": {"const": "email"},
                        "email": {
                            "type": "string",
                            "pattern": r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
                        },
                        "phone": {"type": "null"},
                    },
                },
                {
                    "properties": {
                        "channel": {"const": "sms"},
                        "email": {"type": "null"},
                        "phone": {
                            "type": "string",
                            "pattern": r"^\+[1-9][0-9]{7,14}$",
                        },
                    },
                },
            ],
        },
        "expected": {
            "channel": "email",
            "email": "asha@example.org",
            "phone": None,
        },
        "notes": "Exactly one conditional branch, inactive field null. Branch const values define categories, not the example answer.",
    },
    "C06": {
        "id": "C06",
        "title": "C06. if/then/else: physical versus digital — advanced probe",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Normalize a physical delivery to Pune. There is no download link. Produce kind, downloadUrl and shippingCity; use null for the inapplicable downloadUrl.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["digital", "physical"],
                    "description": "Delivery kind.",
                },
                "downloadUrl": {
                    "type": ["string", "null"],
                },
                "shippingCity": {
                    "type": ["string", "null"],
                },
            },
            "required": ["kind", "downloadUrl", "shippingCity"],
            "additionalProperties": False,
            "if": {
                "properties": {
                    "kind": {"const": "digital"},
                },
                "required": ["kind"],
            },
            "then": {
                "properties": {
                    "downloadUrl": {
                        "type": "string",
                        "pattern": r"^https://[^\s]+$",
                    },
                    "shippingCity": {"type": "null"},
                },
            },
            "else": {
                "properties": {
                    "downloadUrl": {"type": "null"},
                    "shippingCity": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
            },
        },
        "expected": {
            "kind": "physical",
            "downloadUrl": None,
            "shippingCity": "Pune",
        },
        "notes": "Conditional requirement beyond field types. If native generation cannot enforce this vocabulary, record that limitation instead of dropping it.",
    },
    "C07": {
        "id": "C07",
        "title": "C07. Local $defs/$ref: reusable item contract — advanced probe",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Normalize stock request REQ-0005: SKU-0007, warehouse DEL, quantity 3; then SKU-0042, warehouse BLR, quantity 2. Produce requestId and items. Each item has sku, warehouse, quantity. Keep the source order.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "requestId": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Request identifier.",
                    "pattern": "^REQ-[0-9]{4}$",
                },
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 4,
                    "items": {
                        "$ref": "#/$defs/stockItem",
                    },
                },
            },
            "required": ["requestId", "items"],
            "additionalProperties": False,
            "$defs": {
                "stockItem": {
                    "type": "object",
                    "properties": {
                        "sku": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Stock keeping unit.",
                            "pattern": "^SKU-[0-9]{4}$",
                        },
                        "warehouse": {
                            "type": "string",
                            "enum": ["DEL", "MUM", "BLR"],
                            "description": "Warehouse code.",
                        },
                        "quantity": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Requested count.",
                        },
                    },
                    "required": ["sku", "warehouse", "quantity"],
                    "additionalProperties": False,
                },
            },
        },
        "expected": {
            "requestId": "REQ-0005",
            "items": [
                {"sku": "SKU-0007", "warehouse": "DEL", "quantity": 3},
                {"sku": "SKU-0042", "warehouse": "BLR", "quantity": 2},
            ],
        },
        "notes": "Local reference resolution with no network dependency.",
    },
    "C08": {
        "id": "C08",
        "title": "C08. Unique bounded tags: avoid duplicates — advanced probe",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Normalize document DOC-0006. Tags in source order: schema, llm, schema, validation. Produce documentId and tags, removing duplicates while preserving first occurrence. Only these tags are allowed: schema, llm, validation, api.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "documentId": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Document identifier.",
                    "pattern": "^DOC-[0-9]{4}$",
                },
                "tags": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 4,
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "enum": ["schema", "llm", "validation", "api"],
                        "description": "Allowed document tag.",
                    },
                },
            },
            "required": ["documentId", "tags"],
            "additionalProperties": False,
        },
        "expected": {
            "documentId": "DOC-0006",
            "tags": ["schema", "llm", "validation"],
        },
        "notes": "Enum item values and uniqueness. Exact chosen tags and order require comparison with the source.",
    },
    "C09": {
        "id": "C09",
        "title": "C09. Patterns: dates, time and string IDs",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Normalize appointment APT-0009 for 5 March 2027 at 9:05 AM in Room 007. Produce appointmentId, date, startTime, room. Keep room as the string 007, not the number 7.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "appointmentId": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Appointment identifier.",
                    "pattern": "^APT-[0-9]{4}$",
                },
                "date": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Appointment date in YYYY-MM-DD.",
                    "format": "date",
                    "pattern": r"^\d{4}-\d{2}-\d{2}$",
                },
                "startTime": {
                    "type": "string",
                    "minLength": 1,
                    "description": "24-hour HH:MM.",
                    "pattern": r"^([01][0-9]|2[0-3]):[0-5][0-9]$",
                },
                "room": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Three-digit room identifier; retain leading zeros.",
                    "pattern": "^[0-9]{3}$",
                },
            },
            "required": ["appointmentId", "date", "startTime", "room"],
            "additionalProperties": False,
        },
        "expected": {
            "appointmentId": "APT-0009",
            "date": "2027-03-05",
            "startTime": "09:05",
            "room": "007",
        },
        "notes": "String patterns and normalization. Calendar validity under format can depend on validator vocabulary policy.",
    },
    "C10": {
        "id": "C10",
        "title": "C10. Missing facts: structured clarification — advanced probe",
        "prompt": "Return exactly one JSON object without Markdown or commentary. Use only the supplied facts and preserve identifiers exactly. Prepare flight-search details from Delhi to Jaipur for two travellers. No departure date has been provided. Do not invent it. Produce action, arguments, missingFields. If any required field is missing, ask_clarification, return empty arguments, and list the missing fields. Required inputs are origin, destination, departureDate, travellers.",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["call_tool", "ask_clarification"],
                    "description": "call_tool only when all required inputs are explicitly known; otherwise ask_clarification.",
                },
                "arguments": {
                    "type": "object",
                },
                "missingFields": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "enum": ["origin", "destination", "departureDate", "travellers"],
                        "description": "Allowed missing flight fields.",
                    },
                },
            },
            "required": ["action", "arguments", "missingFields"],
            "additionalProperties": False,
            "oneOf": [
                {
                    "properties": {
                        "action": {"const": "call_tool"},
                        "arguments": {
                            "type": "object",
                            "properties": {
                                "origin": {
                                    "type": "string",
                                    "minLength": 1,
                                    "description": "Origin city.",
                                },
                                "destination": {
                                    "type": "string",
                                    "minLength": 1,
                                    "description": "Destination city.",
                                },
                                "departureDate": {
                                    "type": "string",
                                    "minLength": 1,
                                    "description": "Departure date.",
                                    "format": "date",
                                    "pattern": r"^\d{4}-\d{2}-\d{2}$",
                                },
                                "travellers": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 9,
                                    "description": "People count.",
                                },
                            },
                            "required": ["origin", "destination", "departureDate", "travellers"],
                            "additionalProperties": False,
                        },
                        "missingFields": {"maxItems": 0},
                    },
                },
                {
                    "properties": {
                        "action": {"const": "ask_clarification"},
                        "arguments": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                            "additionalProperties": False,
                        },
                        "missingFields": {"minItems": 1, "maxItems": 4},
                    },
                },
            ],
        },
        "expected": {
            "action": "ask_clarification",
            "arguments": {},
            "missingFields": ["departureDate"],
        },
        "notes": "call_tool only when all required inputs are explicitly known; otherwise ask_clarification.",
    },
}

PRESETS = {
    # Canonical C01-C10 pairs
    **CLI_PAIRS,
    # Aliases for backwards compatibility
    "required_string": CLI_PAIRS["C01"],
    "enum_integer_bounds": CLI_PAIRS["C02"],
    "nested_objects_array": CLI_PAIRS["C04"],
    "one_of_conditional": CLI_PAIRS["C05"],
    "local_defs_ref": CLI_PAIRS["C07"],
}


def resolve_cli_path() -> tuple[list[str] | None, str | None]:
    """Resolve the executable command for Sourcemeta JSON Schema CLI."""
    # 1. Check explicit override HESCHEMA_LLM_CLI
    env_llm = os.getenv("HESCHEMA_LLM_CLI")
    if env_llm:
        p = Path(env_llm)
        if p.exists():
            if p.suffix == ".js":
                return ["node", str(p.resolve())], str(p.resolve())
            return [str(p.resolve())], str(p.resolve())
        which_path = shutil.which(env_llm)
        if which_path:
            return [which_path], which_path

    # 2. Check local native installation in repo
    node_bin_win = ROOT / "native/node_modules/.bin/jsonschema.cmd"
    if sys.platform == "win32" and node_bin_win.exists():
        return [str(node_bin_win.resolve())], str(node_bin_win.resolve())

    node_bin_posix = ROOT / "native/node_modules/.bin/jsonschema"
    if node_bin_posix.exists():
        return [str(node_bin_posix.resolve())], str(node_bin_posix.resolve())

    node_cli_js = ROOT / "native/node_modules/@sourcemeta/jsonschema/npm/cli.js"
    if node_cli_js.exists():
        return ["node", str(node_cli_js.resolve())], str(node_cli_js.resolve())

    # 3. Check JSONSCHEMA_CLI
    env_cli = os.getenv("JSONSCHEMA_CLI")
    if env_cli:
        p = Path(env_cli)
        if p.exists():
            return [str(p.resolve())], str(p.resolve())
        which_path = shutil.which(env_cli)
        if which_path:
            return [which_path], which_path

    # 4. Global PATH
    which_path = shutil.which("jsonschema")
    if which_path:
        return [which_path], which_path

    return None, None


async def probe_cli_support() -> dict[str, Any]:
    """Probe installed CLI version and verify llm command support."""
    cmd_prefix, resolved_target = resolve_cli_path()
    if not cmd_prefix:
        return {
            "available": False,
            "version": None,
            "llm_supported": False,
            "executable": None,
            "message": "CLI executable not found. Install @sourcemeta/jsonschema in native/ or set HESCHEMA_LLM_CLI.",
        }

    # Probe version
    version_str = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_prefix,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        if proc.returncode == 0:
            version_str = stdout.decode("utf-8", errors="replace").strip()
    except Exception as exc:
        return {
            "available": False,
            "version": None,
            "llm_supported": False,
            "executable": resolved_target,
            "message": f"Failed to execute CLI: {exc}",
        }

    # Probe llm command support
    llm_supported = False
    try:
        proc_help = await asyncio.create_subprocess_exec(
            *cmd_prefix,
            "help",
            "llm",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_h, stderr_h = await asyncio.wait_for(proc_help.communicate(), timeout=10.0)
        out_text = stdout_h.decode("utf-8", errors="replace")
        if proc_help.returncode == 0 and "Ask a model for a document" in out_text:
            llm_supported = True
    except Exception:
        llm_supported = False

    return {
        "available": True,
        "version": version_str or "unknown",
        "llm_supported": llm_supported,
        "executable": resolved_target,
        "message": "CLI available with llm command support." if llm_supported else "CLI found, but lacks llm command (version < 17.2). Setup Required.",
    }


async def probe_ollama_status() -> dict[str, Any]:
    """Probe Ollama connectivity and retrieve list of installed models."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                return {
                    "reachable": True,
                    "baseUrl": base_url,
                    "models": models,
                    "message": f"Connected to Ollama ({len(models)} model(s) available).",
                }
            return {
                "reachable": False,
                "baseUrl": base_url,
                "models": [],
                "message": f"Ollama HTTP {resp.status_code} at {base_url}.",
            }
    except Exception as exc:
        return {
            "reachable": False,
            "baseUrl": base_url,
            "models": [],
            "message": f"Cannot connect to Ollama at {base_url}: {exc}",
        }


def generate_command_previews(
    schema_path: str,
    prompt: str,
    url: str,
    model: str,
    mode: str,
    max_tokens: int = 1024,
    temperature: float | None = None,
    seed: int | None = None,
    has_token: bool = False,
) -> dict[str, str]:
    """Generate reproducible CLI command previews for POSIX and PowerShell."""
    header_flag_posix = ' --header "Authorization: Bearer $HESCHEMA_API_TOKEN"' if has_token else ""
    header_flag_pwsh = ' --header "Authorization: Bearer $env:HESCHEMA_API_TOKEN"' if has_token else ""

    params = [f"--param /max_tokens={max_tokens}"]
    if mode == "prompt_only":
        params.append("--param /heschema_mode=prompt_only")
        params.append("--param /response_format/json_schema/strict=false")
    if temperature is not None:
        params.append(f"--param /temperature={temperature}")
    if seed is not None:
        params.append(f"--param /seed={seed}")

    param_str = " ".join(params)

    # Shell quoting for prompt
    safe_prompt_posix = prompt.replace('"', '\\"')
    safe_prompt_pwsh = prompt.replace('"', '`"')

    posix_cmd = f'jsonschema llm {schema_path} --ask "{safe_prompt_posix}" --url {url} --model "{model}" {param_str}{header_flag_posix} --json'
    pwsh_cmd = f'& jsonschema llm {schema_path} --ask "{safe_prompt_pwsh}" --url {url} --model "{model}" {param_str}{header_flag_pwsh} --json'

    return {"posix": posix_cmd, "powershell": pwsh_cmd}


async def execute_cli_run(
    schema: dict[str, Any],
    prompt: str,
    model: str,
    mode: str = "native_schema",
    max_tokens: int = 1024,
    temperature: float | None = None,
    seed: int | None = None,
    loopback_url: str = "http://127.0.0.1:8000/v1/chat/completions",
    timeout: float = 180.0,
) -> dict[str, Any]:
    """Run the real installed Sourcemeta CLI as a child subprocess without blocking the asyncio loop."""
    cmd_prefix, _ = resolve_cli_path()
    if not cmd_prefix:
        raise RuntimeError("Sourcemeta JSON Schema CLI executable not found. Setup required.")

    # Write schema to a unique temporary file
    temp_dir = tempfile.mkdtemp(prefix="heschema_cli_")
    schema_file = Path(temp_dir) / "schema.json"
    schema_file.write_text(canonical(schema), encoding="utf-8")

    argv = list(cmd_prefix) + [
        "llm",
        str(schema_file.resolve()),
        "--default-dialect",
        "https://json-schema.org/draft/2020-12/schema",
        "--ask",
        prompt,
        "--url",
        loopback_url,
        "--model",
        model,
        "--json",
        "--timeout",
        str(int(timeout)),
        "--param",
        f"/max_tokens={max_tokens}",
    ]

    if mode == "prompt_only":
        argv.extend([
            "--param",
            "/heschema_mode=prompt_only",
            "--param",
            "/response_format/json_schema/strict=false",
        ])

    if temperature is not None:
        argv.extend(["--param", f"/temperature={temperature}"])
    if seed is not None:
        argv.extend(["--param", f"/seed={seed}"])

    token = os.getenv("HESCHEMA_API_TOKEN", "")
    if token:
        argv.extend(["--header", f"Authorization: Bearer {token}"])

    start_time = time.perf_counter()
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        stdout_str = stdout_bytes.decode("utf-8", errors="replace")
        stderr_str = stderr_bytes.decode("utf-8", errors="replace")

        # Redact token if it somehow appeared in output
        if token:
            stdout_str = stdout_str.replace(token, "[REDACTED_TOKEN]")
            stderr_str = stderr_str.replace(token, "[REDACTED_TOKEN]")

        parsed_json = None
        json_valid = False
        try:
            parsed_json = loads(stdout_str)
            json_valid = True
        except Exception:
            json_valid = False

        return {
            "exitCode": proc.returncode,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "elapsedMs": round(elapsed_ms, 2),
            "parsedJson": parsed_json,
            "jsonValid": json_valid,
            "cliRunSuccess": proc.returncode == 0,
        }
    except asyncio.TimeoutError:
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
        raise TimeoutError(f"Sourcemeta CLI timed out after {timeout} seconds.") from None
    finally:
        # Clean up temporary directory and schema file
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def evaluate_document_diagnostics(
    schema: dict[str, Any],
    raw_content: str,
    engine: SchemaEngine,
) -> dict[str, Any]:
    """Independent diagnostic separation between raw output, json parsing, schema conformance, and semantic correctness."""
    parsed_instance = None
    json_parse_valid = False
    parse_error = None

    try:
        parsed_instance = loads(raw_content)
        json_parse_valid = True
    except Exception as exc:
        parse_error = str(exc)

    schema_errors = []
    schema_valid = False
    if json_parse_valid:
        try:
            schema_errors = engine.errors(schema, parsed_instance)
            schema_valid = len(schema_errors) == 0
        except Exception as exc:
            schema_errors = [{"code": "VALIDATION_FAILED", "path": "/", "message": str(exc)}]

    return {
        "jsonParseValid": json_parse_valid,
        "jsonParseError": parse_error,
        "parsedInstance": parsed_instance,
        "heschemaSchemaValid": schema_valid,
        "schemaErrors": schema_errors,
        "engineUsed": engine.backend,
        "semanticCorrectness": "Not checked",  # Explicit: No ground truth available in arbitrary schema testing
    }
