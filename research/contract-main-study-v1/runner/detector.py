"""Acceptance detectors for Arms A, B, and controls C, D."""

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from jsonschema import Draft202012Validator, FormatChecker

from heschema.contracts import Contract
from heschema.context_schema import effective_schema
from heschema.rules import evaluate_rules
try:
    from .strict_parser import StrictParseError, parse_strict_json
except ImportError:
    from strict_parser import StrictParseError, parse_strict_json


@dataclass
class DetectionResult:
    accepted: bool
    parsed: Optional[Dict[str, Any]] = None
    diagnostics: List[str] = field(default_factory=list)
    failure_type: Optional[str] = None
    stage: str = "ok"

    def diagnostic_summary(self) -> str:
        return "\n".join(self.diagnostics)


def detect_acceptance(case: Dict[str, Any], raw_text: str, arm: str) -> DetectionResult:
    """Evaluates raw output against the arm's acceptance policy."""
    # 1. Strict JSON parsing
    try:
        parsed = parse_strict_json(raw_text)
    except StrictParseError as exc:
        return DetectionResult(
            accepted=False,
            parsed=None,
            diagnostics=[str(exc)],
            failure_type="formatting_or_json_parse",
            stage="json"
        )
    except Exception as exc:
        return DetectionResult(
            accepted=False,
            parsed=None,
            diagnostics=[f"Formatting/JSON parse error: {exc}"],
            failure_type="formatting_or_json_parse",
            stage="json"
        )

    contract = Contract(**case['contract'])

    # 2. Schema check
    if arm == "A":
        # Arm A checks original schema
        schema_to_check = contract.schema
    elif arm in ("B", "C", "D"):
        # Arm B, Control C, and Control D check effective projected schema
        eff_schema, _ = effective_schema(contract, case['context'])
        schema_to_check = eff_schema
    else:
        raise ValueError(f"Unknown arm: {arm}")

    validator = Draft202012Validator(schema_to_check, format_checker=FormatChecker())
    schema_errors = list(validator.iter_errors(parsed))
    if schema_errors:
        diags = []
        for err in schema_errors[:5]:
            path = "/" + "/".join(str(p) for p in err.absolute_path)
            diags.append(f"At {path or 'root'}: {err.message}")
        return DetectionResult(
            accepted=False,
            parsed=parsed,
            diagnostics=diags,
            failure_type="ordinary_schema_violation",
            stage="schema"
        )

    # 3. Relationship checks (Arm B and Control D only)
    if arm in ("B", "D") and contract.relationships:
        rule_eval = evaluate_rules(parsed, contract.relationships, case['context']['data'])
        if rule_eval['status'] != 'valid':
            diags = []
            for err in rule_eval.get('errors', []):
                rule_id = err.get('ruleId', 'unknown')
                loc = err.get('location', 'root')
                msg = err.get('message', 'relationship mismatch')
                diags.append(f"Rule [{rule_id}] at {loc}: {msg}")
            return DetectionResult(
                accepted=False,
                parsed=parsed,
                diagnostics=diags or ["Application relationship validation failed"],
                failure_type="relationship_or_association",
                stage="relationships"
            )

    return DetectionResult(
        accepted=True,
        parsed=parsed,
        diagnostics=[],
        failure_type=None,
        stage="ok"
    )
