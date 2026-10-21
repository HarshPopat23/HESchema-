"""Pydantic v2 plugin for HESchema.

Compiles Pydantic models into HESchema contracts and enforces contract validation.
"""

import copy
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

from ..contracts import Contract
from ..guard import ContractViolationError, guard

T = TypeVar("T", bound=BaseModel)


def _inline_defs(schema: dict) -> dict:
    """Inline $defs references into a self-contained schema."""
    result = copy.deepcopy(schema)
    defs = result.pop("$defs", {})
    if not defs:
        return result

    def resolve_node(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                if ref.startswith("#/$defs/"):
                    target_key = ref.split("/")[-1]
                    if target_key in defs:
                        resolved = copy.deepcopy(defs[target_key])
                        # Merge any sibling keys
                        node.pop("$ref")
                        resolved.update(node)
                        return resolve_node(resolved)
            return {k: resolve_node(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [resolve_node(x) for x in node]
        return node

    resolved = resolve_node(result)
    return resolved


def contract_from_model(
    model_cls: Type[BaseModel],
    contract_id: Optional[str] = None,
    version: str = "1.0",
    output_kind: str = "document",
    tool: Optional[str] = None,
    relationships: Optional[List[Dict[str, Any]]] = None,
    bindings: Optional[List[Dict[str, Any]]] = None,
) -> Contract:
    """Compile a Pydantic v2 BaseModel class into an authoritative HESchema Contract."""
    raw_schema = model_cls.model_json_schema()
    cleaned = _inline_defs(raw_schema)

    # Ensure additionalProperties: False on closed object schemas
    if cleaned.get("type") == "object" and "additionalProperties" not in cleaned:
        cleaned["additionalProperties"] = False

    cid = contract_id or model_cls.__name__.lower()
    tname = tool or (cid if output_kind == "tool_envelope" else None)

    # Collect relationships from class attributes if present
    rules = list(relationships or [])
    if hasattr(model_cls, "__relationships__") and isinstance(model_cls.__relationships__, list):
        rules.extend(model_cls.__relationships__)

    b_list = list(bindings or [])
    if hasattr(model_cls, "__bindings__") and isinstance(model_cls.__bindings__, list):
        b_list.extend(model_cls.__bindings__)

    return Contract(
        id=cid,
        version=version,
        schema=cleaned,
        outputKind=output_kind,
        tool=tname,
        description=model_cls.__doc__ or "",
        relationships=rules,
        bindings=b_list,
    )


def guarded_model(
    contract_id: Optional[str] = None,
    version: str = "1.0",
    output_kind: str = "document",
    on_fail: str = "raise",
    relationships: Optional[List[Dict[str, Any]]] = None,
    bindings: Optional[List[Dict[str, Any]]] = None,
):
    """Class decorator for Pydantic v2 models that binds HESchema validation to model instantiation."""

    def decorator(cls: Type[T]) -> Type[T]:
        contract = contract_from_model(
            cls,
            contract_id=contract_id,
            version=version,
            output_kind=output_kind,
            relationships=relationships,
            bindings=bindings,
        )
        cls.__contract__ = contract
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            if args:
                # If positional arguments or dict passed
                data = args[0] if isinstance(args[0], dict) else kwargs
            else:
                data = kwargs

            # Validate with HESchema guard
            validation = guard.validate(data, contract)
            if not validation.get("accepted"):
                errs = "; ".join(e.get("message", e.get("code", "error")) for e in validation.get("errors", []))
                raise ContractViolationError(
                    f"Pydantic model {cls.__name__} violates HESchema contract {contract.id}: {errs}",
                    errors=validation.get("errors", []),
                    result=validation,
                )

            # If calculations applied repaired values, merge them in
            calc_info = validation.get("calculation", {})
            if calc_info.get("status") == "applied" and calc_info.get("values"):
                for v in calc_info["values"]:
                    target_key = v["target"].lstrip("/").split("/")[0]
                    if target_key:
                        kwargs[target_key] = v["value"]

            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        cls.as_contract = classmethod(lambda c: c.__contract__)
        return cls

    return decorator
