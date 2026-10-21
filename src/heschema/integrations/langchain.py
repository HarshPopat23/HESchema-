"""LangChain and LangGraph middleware & tool interceptor for HESchema."""

import copy
from typing import Any, Callable, Dict, List, Optional, Union

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
        self.contracts = {name: load_contract(c) for name, c in contracts.items()}
        self.on_fail = on_fail
        self.snapshot = snapshot

    def intercept(self, tool_name: str, arguments: dict) -> dict:
        """Validate and repair arguments for a specific tool call."""
        contract = self.contracts.get(tool_name)
        if not contract:
            return arguments

        res = guard.validate(arguments, contract, snapshot=self.snapshot)
        if res.get("accepted"):
            # Check if calculation repaired any arguments
            calc_info = res.get("calculation", {})
            if calc_info.get("status") == "applied" and calc_info.get("values"):
                repaired = copy.deepcopy(arguments)
                for item in calc_info["values"]:
                    key = item["target"].lstrip("/").split("/")[0]
                    repaired[key] = item["value"]
                return repaired
            return arguments

        # Failed validation
        if self.on_fail == "raise":
            err_summary = "; ".join(e.get("message", e.get("code", "error")) for e in res.get("errors", []))
            raise ContractViolationError(
                f"LangChain tool '{tool_name}' violated contract {contract.id}: {err_summary}",
                errors=res.get("errors", []),
                result=res,
            )
        elif self.on_fail == "refuse":
            return {
                "__error__": True,
                "action": "refuse",
                "reason": f"Tool arguments for '{tool_name}' violated contract {contract.id}",
                "errors": res.get("errors", []),
            }

        return arguments

    def intercept_message(self, message: Any) -> Any:
        """Inspect and intercept tool_calls in an AIMessage or message dict."""
        # Handle dict format
        if isinstance(message, dict) and "tool_calls" in message:
            for tc in message["tool_calls"]:
                tool_name = tc.get("name") or tc.get("function", {}).get("name")
                args = tc.get("args") or tc.get("function", {}).get("arguments")
                if isinstance(args, dict) and tool_name in self.contracts:
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
                if isinstance(args, dict) and tool_name in self.contracts:
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


def guard_tool(tool: Any, contract: Union[str, dict, Contract], on_fail: str = "repair") -> Any:
    """Wrap a LangChain BaseTool so that tool invocation is guarded by HESchema."""
    loaded_contract = load_contract(contract)
    interceptor = HESchemaToolInterceptor({getattr(tool, "name", "tool"): loaded_contract}, on_fail=on_fail)

    # Wrap invoke/run
    original_invoke = getattr(tool, "invoke", None)
    if original_invoke:
        def guarded_invoke(input_data, *args, **kwargs):
            if isinstance(input_data, dict):
                input_data = interceptor.intercept(getattr(tool, "name", "tool"), input_data)
            return original_invoke(input_data, *args, **kwargs)

        tool.invoke = guarded_invoke

    original_run = getattr(tool, "run", None)
    if original_run:
        def guarded_run(tool_input, *args, **kwargs):
            if isinstance(tool_input, dict):
                tool_input = interceptor.intercept(getattr(tool, "name", "tool"), tool_input)
            return original_run(tool_input, *args, **kwargs)

        tool.run = guarded_run

    return tool
