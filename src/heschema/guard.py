"""Single-line drop-in Python SDK decorator and validator for HESchema contracts."""

import functools
import inspect
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .calculations import validate_with_calculations
from .contracts import Contract
from .schema import SchemaEngine

_CONTRACT_CACHE: Dict[str, Contract] = {}
_DEFAULT_ENGINE: Optional[SchemaEngine] = None


def get_default_engine() -> SchemaEngine:
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = SchemaEngine()
    return _DEFAULT_ENGINE


class ContractViolationError(ValueError):
    """Raised when an input or output violates a HESchema contract."""

    def __init__(self, message: str, errors: List[Dict[str, Any]], result: Dict[str, Any]):
        super().__init__(message)
        self.errors = errors
        self.result = result


def load_contract(contract_spec: Union[str, Path, dict, Contract]) -> Contract:
    """Load or resolve a Contract instance from a file path, dict, or existing Contract."""
    if isinstance(contract_spec, Contract):
        return contract_spec

    if isinstance(contract_spec, (str, Path)):
        resolved_path = str(Path(contract_spec).resolve())
        if resolved_path in _CONTRACT_CACHE:
            return _CONTRACT_CACHE[resolved_path]
        raw_text = Path(contract_spec).read_text(encoding="utf-8")
        data = json.loads(raw_text)
        contract = Contract(**data)
        _CONTRACT_CACHE[resolved_path] = contract
        return contract

    if isinstance(contract_spec, dict):
        contract_id = contract_spec.get("id", "")
        version = contract_spec.get("version", "")
        cache_key = f"dict:{contract_id}:{version}"
        if cache_key in _CONTRACT_CACHE and _CONTRACT_CACHE[cache_key].as_dict() == contract_spec:
            return _CONTRACT_CACHE[cache_key]
        contract = Contract(**contract_spec)
        _CONTRACT_CACHE[cache_key] = contract
        return contract

    raise TypeError(f"Expected contract path, dict, or Contract instance, got {type(contract_spec)}")


def _extract_payload(func: Callable, contract: Contract, args: tuple, kwargs: dict) -> tuple:
    """Extract and envelope arguments from function invocation matching contract expectation."""
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    arg_dict = bound.arguments

    # If the contract is a document and a single dict argument was passed directly
    if contract.outputKind == "document":
        if len(arg_dict) == 1:
            first_val = next(iter(arg_dict.values()))
            if isinstance(first_val, dict) and not (
                isinstance(contract.schema, dict)
                and "properties" in contract.schema
                and set(arg_dict.keys()).issubset(set(contract.schema.get("properties", {}).keys()))
            ):
                return first_val, bound

        return arg_dict, bound

    # If the contract is tool_envelope
    tool_name = contract.tool or func.__name__
    payload = {
        "action": "call_tool",
        "tool": tool_name,
        "arguments": arg_dict,
        "missingFields": [],
        "reason": f"Execution of {func.__name__}",
    }
    return payload, bound


def _apply_repaired_arguments(bound_args: inspect.BoundArguments, repaired_values: list, contract: Contract):
    """Apply repaired values (e.g. from calculations) back to bound arguments."""
    from .diagnostics import parts
    for item in repaired_values:
        tokens = parts(item["target"])
        if not tokens:
            continue
        first = tokens[0]
        if first in bound_args.arguments:
            if len(tokens) == 1:
                bound_args.arguments[first] = item["value"]
            else:
                curr = bound_args.arguments[first]
                for tok in tokens[1:-1]:
                    if isinstance(curr, dict):
                        curr = curr.setdefault(tok, {})
                    elif isinstance(curr, list) and tok.isdigit():
                        curr = curr[int(tok)]
                last = tokens[-1]
                if isinstance(curr, dict):
                    curr[last] = item["value"]
                elif isinstance(curr, list) and last.isdigit():
                    curr[int(last)] = item["value"]


def _prepare_payload_for_calculations(payload: dict, contract: Contract) -> dict:
    """Strip application calculation targets so the calculation engine can compute and assemble them."""
    import copy

    from .calculations import calculation_plan
    from .diagnostics import parts
    try:
        plan = calculation_plan(contract)
    except Exception:
        return payload
    if not plan:
        return payload
    cleaned = copy.deepcopy(payload)
    base = cleaned["arguments"] if (contract.outputKind == "tool_envelope" and isinstance(cleaned.get("arguments"), dict)) else cleaned
    for rule in plan:
        tokens = parts(rule["target"])
        if not tokens:
            continue
        curr = base
        for tok in tokens[:-1]:
            if isinstance(curr, dict) and tok in curr:
                curr = curr[tok]
            elif isinstance(curr, list) and tok.isdigit() and int(tok) < len(curr):
                curr = curr[int(tok)]
            else:
                curr = None
                break
        if isinstance(curr, dict):
            curr.pop(tokens[-1], None)
        elif isinstance(curr, list) and tokens[-1].isdigit():
            idx = int(tokens[-1])
            if idx < len(curr):
                curr.pop(idx)
    return cleaned


class Guard:
    """Decorator and validation coordinator for HESchema."""

    def __call__(
        self,
        contract: Union[str, Path, dict, Contract],
        on_fail: str = "raise",
        engine: Optional[SchemaEngine] = None,
        snapshot: Optional[dict] = None,
        provider: Optional[Any] = None,
    ):
        """Decorate a sync or async function with contract enforcement."""
        loaded_contract = load_contract(contract)
        schema_engine = engine or get_default_engine()

        def decorator(func: Callable):
            is_async = inspect.iscoroutinefunction(func)

            if is_async:
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    payload, bound = _extract_payload(func, loaded_contract, args, kwargs)
                    calc_payload = _prepare_payload_for_calculations(payload, loaded_contract)
                    snap = snapshot() if callable(snapshot) else snapshot
                    res = validate_with_calculations(
                        calc_payload,
                        schema_engine,
                        loaded_contract,
                        snap,
                    )
                    calc_info = res.get("calculation", {})
                    if calc_info.get("status") == "applied" and calc_info.get("values"):
                        _apply_repaired_arguments(bound, calc_info["values"], loaded_contract)

                    if not res.get("accepted"):
                        if on_fail == "raise":
                            err_summary = "; ".join(e.get("message", e.get("code", "error")) for e in res.get("errors", []))
                            raise ContractViolationError(
                                f"Contract violation in {func.__name__}: {err_summary}",
                                errors=res.get("errors", []),
                                result=res,
                            )
                        elif on_fail == "refuse":
                            return {
                                "action": "refuse",
                                "reason": f"Input violates contract {loaded_contract.id}",
                                "errors": res.get("errors", []),
                                "validation": res,
                            }
                        elif on_fail == "repair":
                            # If calculations could not repair and validation failed
                            err_summary = "; ".join(e.get("message", e.get("code", "error")) for e in res.get("errors", []))
                            raise ContractViolationError(
                                f"Contract violation cannot be automatically repaired in {func.__name__}: {err_summary}",
                                errors=res.get("errors", []),
                                result=res,
                            )

                    return await func(*bound.args, **bound.kwargs)

                async_wrapper.contract = loaded_contract
                async_wrapper.validate = lambda *a, **kw: self.validate(
                    _extract_payload(func, loaded_contract, a, kw)[0],
                    loaded_contract,
                    snapshot=snapshot() if callable(snapshot) else snapshot,
                    engine=schema_engine,
                )
                return async_wrapper

            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    payload, bound = _extract_payload(func, loaded_contract, args, kwargs)
                    calc_payload = _prepare_payload_for_calculations(payload, loaded_contract)
                    snap = snapshot() if callable(snapshot) else snapshot
                    res = validate_with_calculations(
                        calc_payload,
                        schema_engine,
                        loaded_contract,
                        snap,
                    )
                    calc_info = res.get("calculation", {})
                    if calc_info.get("status") == "applied" and calc_info.get("values"):
                        _apply_repaired_arguments(bound, calc_info["values"], loaded_contract)

                    if not res.get("accepted"):
                        if on_fail == "raise":
                            err_summary = "; ".join(e.get("message", e.get("code", "error")) for e in res.get("errors", []))
                            raise ContractViolationError(
                                f"Contract violation in {func.__name__}: {err_summary}",
                                errors=res.get("errors", []),
                                result=res,
                            )
                        elif on_fail == "refuse":
                            return {
                                "action": "refuse",
                                "reason": f"Input violates contract {loaded_contract.id}",
                                "errors": res.get("errors", []),
                                "validation": res,
                            }
                        elif on_fail == "repair":
                            err_summary = "; ".join(e.get("message", e.get("code", "error")) for e in res.get("errors", []))
                            raise ContractViolationError(
                                f"Contract violation cannot be automatically repaired in {func.__name__}: {err_summary}",
                                errors=res.get("errors", []),
                                result=res,
                            )

                    return func(*bound.args, **bound.kwargs)

                sync_wrapper.contract = loaded_contract
                sync_wrapper.validate = lambda *a, **kw: self.validate(
                    _extract_payload(func, loaded_contract, a, kw)[0],
                    loaded_contract,
                    snapshot=snapshot() if callable(snapshot) else snapshot,
                    engine=schema_engine,
                )
                return sync_wrapper

        return decorator

    @staticmethod
    def validate(
        data: Any,
        contract: Union[str, Path, dict, Contract],
        snapshot: Optional[dict] = None,
        engine: Optional[SchemaEngine] = None,
    ) -> Dict[str, Any]:
        """Direct 1-line validation method for raw dicts or JSON strings."""
        loaded_contract = load_contract(contract)
        schema_engine = engine or get_default_engine()
        calc_payload = _prepare_payload_for_calculations(data, loaded_contract) if isinstance(data, dict) else data
        return validate_with_calculations(calc_payload, schema_engine, loaded_contract, snapshot)


guard = Guard()
