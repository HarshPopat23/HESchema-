"""LangChain and LangGraph middleware & tool interceptor for HESchema."""

from functools import wraps
from inspect import signature
from typing import Any, Dict, Optional, Union

from ..contracts import Contract
from ..guard import ContractViolationError, guard, load_contract


class HESchemaToolInterceptor:
    """Intercepts and validates tool calls before they execute in LangChain or LangGraph."""

    def __init__(
        self,
        contracts: Dict[str, Union[str, dict, Contract]],
        on_fail: str = "repair",
        snapshot: Optional[dict] = None,
    ):
        if on_fail not in {"raise", "refuse", "repair"}:
            raise ValueError("on_fail must be raise, refuse, or repair")
        self.contracts = {name: load_contract(c) for name, c in contracts.items()}
        self.on_fail = on_fail
        self.snapshot = snapshot

    def intercept(self, tool_name: str, arguments: Any) -> dict:
        """Return validated assembled arguments, or raise before execution.

        Repair uses only declared application calculations. There is no model
        repair callback here; an unsuccessful repair fails closed. Refusal is
        converted to a result only at the execution wrapper, never into args.
        """
        contract = self.contracts.get(tool_name)
        if contract is None:
            return arguments
        res = guard.validate(arguments, contract, snapshot=self.snapshot)
        parsed = res.get("parsed")
        if res.get("accepted"):
            if contract.outputKind == "tool_envelope":
                if (isinstance(parsed, dict) and parsed.get("action") == "call_tool"
                        and parsed.get("tool") == contract.tool == tool_name):
                    parsed = parsed.get("arguments")
                else:
                    parsed = None
            if isinstance(parsed, dict):
                # The core already applied full JSON Pointers and validated this
                # assembled document. Never replay calculations independently.
                return parsed
        raise ContractViolationError(
            f"LangChain tool '{tool_name}' violated contract {contract.id}",
            errors=res.get("errors", []), result=res,
        )

    def intercept_message(self, message: Any) -> Any:
        """Inspect and intercept tool_calls in an AIMessage or message dict."""
        # Handle dict format
        if isinstance(message, dict) and "tool_calls" in message:
            for tc in message["tool_calls"]:
                tool_name = tc.get("name") or tc.get("function", {}).get("name")
                args = tc.get("args", tc.get("function", {}).get("arguments"))
                if tool_name in self.contracts:
                    repaired = self.intercept(tool_name, args)
                    if "args" in tc:
                        tc["args"] = repaired
                    if "function" in tc and "arguments" in tc["function"]:
                        tc["function"]["arguments"] = repaired
            return message

        # Handle LangChain AIMessage object with .tool_calls attribute
        if hasattr(message, "tool_calls") and isinstance(message.tool_calls, list):
            for tc in message.tool_calls:
                tool_name = tc.get("name")
                args = tc.get("args")
                if tool_name in self.contracts:
                    repaired = self.intercept(tool_name, args)
                    tc["args"] = repaired
            return message

        return message

    def __call__(self, state: Union[dict, list]) -> Union[dict, list]:
        """LangGraph node middleware callable."""
        if isinstance(state, dict):
            messages = state.get("messages", [])
            if messages:
                self.intercept_message(messages[-1])
        elif isinstance(state, list) and state:
            self.intercept_message(state[-1])
        return state


def guard_tool(tool: Any, contract: Union[str, dict, Contract], on_fail: str = "repair",
               snapshot: Optional[dict] = None) -> Any:
    """Guard sync/async tool entry points; refusal returns without execution.

    All input forms are validated. The caller still owns execution permission
    and authorization; contract acceptance alone does not authorize a side effect.
    """
    name = getattr(tool, "name", "tool")
    interceptor = HESchemaToolInterceptor({name: contract}, on_fail=on_fail, snapshot=snapshot)

    def prepare(data):
        return interceptor.intercept(name, data)

    def refusal(error):
        return {"__error__": True, "action": "refuse", "reason": str(error),
                "errors": error.errors}

    def prepare_call(original_signature, args, kwargs):
        bound = original_signature.bind(*args, **kwargs)
        bound.apply_defaults()
        first = next(iter(original_signature.parameters))
        bound.arguments[first] = prepare(bound.arguments[first])
        return bound

    def wrap_sync(original):
        original_signature = signature(original)

        @wraps(original)
        def guarded(*args, **kwargs):
            try:
                accepted = prepare_call(original_signature, args, kwargs)
            except ContractViolationError as error:
                if on_fail == "refuse":
                    return refusal(error)
                raise
            return original(*accepted.args, **accepted.kwargs)
        return guarded

    def wrap_async(original):
        original_signature = signature(original)

        @wraps(original)
        async def guarded(*args, **kwargs):
            try:
                accepted = prepare_call(original_signature, args, kwargs)
            except ContractViolationError as error:
                if on_fail == "refuse":
                    return refusal(error)
                raise
            return await original(*accepted.args, **accepted.kwargs)
        return guarded

    for method in ("invoke", "run", "ainvoke", "arun"):
        original = getattr(tool, method, None)
        if callable(original):
            setattr(tool, method, wrap_async(original) if method.startswith("a") else wrap_sync(original))
    return tool
