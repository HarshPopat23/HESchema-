from typing import Any, Dict, List, Optional

try:
    from .strict_parser import StrictParseError, parse_strict_json
    from .detector import DetectionResult
    from .oracle import reconstruct_reference_output, json_semantic_equal
except ImportError:
    from strict_parser import StrictParseError, parse_strict_json
    from detector import DetectionResult
    from oracle import reconstruct_reference_output, json_semantic_equal


FAILURE_TAXONOMY = [
    "formatting_or_json_parse",
    "unsupported_schema_or_provider_mode",
    "ordinary_schema_violation",
    "wrong_source_value",
    "arithmetic",
    "relationship_or_association",
    "task_misunderstanding",
    "missing_or_untrusted_context",
    "false_rejection",
    "transport_or_timeout",
    "unresolved",
]


def classify_failure(
    case: Dict[str, Any],
    raw_text: Optional[str],
    detection: Optional[DetectionResult],
    oracle_correct: bool,
    transport_error: Optional[str] = None
) -> List[str]:
    """Assigns multi-label failure categories to an attempt."""
    labels = []

    # 1. Transport failures
    if transport_error:
        labels.append("transport_or_timeout")
        labels.append("unresolved")
        return labels

    if raw_text is None or not raw_text.strip():
        labels.append("formatting_or_json_parse")
        labels.append("unresolved")
        return labels

    # 2. Parse checks
    parsed = None
    try:
        parsed = parse_strict_json(raw_text)
    except StrictParseError:
        labels.append("formatting_or_json_parse")
    except Exception:
        labels.append("formatting_or_json_parse")

    # 3. False rejection: Detector rejected, but oracle found it correct!
    if detection and not detection.accepted and oracle_correct:
        labels.append("false_rejection")

    # If oracle found it correct and detector accepted, there are no failure labels!
    if oracle_correct and detection and detection.accepted:
        return []

    # 4. Detector-derived failures
    if detection and not detection.accepted:
        if detection.failure_type == "ordinary_schema_violation":
            labels.append("ordinary_schema_violation")
        elif detection.failure_type == "relationship_or_association":
            labels.append("relationship_or_association")
        elif detection.failure_type == "formatting_or_json_parse":
            if "formatting_or_json_parse" not in labels:
                labels.append("formatting_or_json_parse")

    # 5. Semantic diagnostic if parsed
    if parsed is not None and not oracle_correct:
        expected = reconstruct_reference_output(case)
        cid = case['id']

        # Check arithmetic / sum / count fields
        arithmetic_keys = {"totalSizeBytes", "totalCapacity", "fileCount", "stationCount", "listedAuthorCount"}
        has_arithmetic_err = False
        for k in arithmetic_keys:
            if k in expected and k in parsed:
                if parsed[k] != expected[k]:
                    labels.append("arithmetic")
                    has_arithmetic_err = True
                    break

        # Check source field values vs arithmetic
        val_mismatch = False
        rel_mismatch = False
        for k, v in expected.items():
            if k not in parsed:
                labels.append("task_misunderstanding")
                break
            if k not in arithmetic_keys and not json_semantic_equal(parsed[k], v):
                val_mismatch = True

        if val_mismatch:
            labels.append("wrong_source_value")

        # Specific relationship checks for USGS coords
        if cid.startswith("USGS-"):
            if parsed.get("longitude") != expected.get("longitude") or parsed.get("latitude") != expected.get("latitude"):
                labels.append("relationship_or_association")

    if not oracle_correct and "unresolved" not in labels:
        labels.append("unresolved")

    # Multi-label deduplication while preserving taxonomy order
    return [l for l in FAILURE_TAXONOMY if l in labels]
