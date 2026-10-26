"""Structural budgets and heuristic regex screening; not a resource sandbox."""

import re

MAX_SCHEMA_DEPTH = 15
MAX_PROPERTY_COUNT = 250
MAX_PATTERN_LENGTH = 1000

# Catastrophic backtracking patterns like ((a+)+$), (a|aa)+, (.*a){x}
DANGEROUS_REGEX_PATTERNS = [
    re.compile(r'\([^)]*[\+\*]\)[*+\{]'),          # Nested quantifiers like (a+)+ or (a*)*
    re.compile(r'\([^)]*\|[^)]*\)[*+\{]'),          # Overlapping alternatives with quantifier like (a|aa)+
    re.compile(r'(\.\*|\.\+)[*+\{]'),               # Wildcard quantifier repetition like (.*)+
]


def check_regex_safety(pattern: str):
    """Ensure regex pattern is bounded in length and free from obvious catastrophic backtracking."""
    if not isinstance(pattern, str):
        return
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise ValueError(f"Schema regex exceeds maximum allowed length of {MAX_PATTERN_LENGTH} characters")
    for danger in DANGEROUS_REGEX_PATTERNS:
        if danger.search(pattern):
            raise ValueError(
                f"Schema regex '{pattern[:50]}' contains potentially catastrophic backtracking (ReDoS risk)"
            )
    try:
        re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"Invalid schema regex '{pattern[:50]}': {exc}") from None


def check_schema_complexity(schema, max_depth: int = MAX_SCHEMA_DEPTH, max_properties: int = MAX_PROPERTY_COUNT):
    """Enforce structural depth, property count, and regex safety on JSON Schemas."""
    if not isinstance(schema, dict):
        return

    prop_count = 0

    def walk(node, current_depth):
        nonlocal prop_count
        if current_depth > max_depth:
            raise ValueError(f"Schema depth {current_depth} exceeds complexity budget limit of {max_depth}")

        if not isinstance(node, dict):
            return

        # Check regex properties
        if "pattern" in node:
            check_regex_safety(node["pattern"])

        if "patternProperties" in node and isinstance(node["patternProperties"], dict):
            for pat in node["patternProperties"]:
                check_regex_safety(pat)
            # schema_children visits each pattern subschema once below.

        if "properties" in node and isinstance(node["properties"], dict):
            prop_count += len(node["properties"])
            if prop_count > max_properties:
                raise ValueError(
                    f"Total schema property count {prop_count} exceeds complexity budget limit of {max_properties}"
                )
            for prop_name, prop_schema in node["properties"].items():
                walk(prop_schema, current_depth + 1)

        # Children in applicators
        from .schema import schema_children
        for tokens, child in schema_children(node):
            if tokens[0] != "properties":
                walk(child, current_depth + 1)

    walk(schema, 1)
