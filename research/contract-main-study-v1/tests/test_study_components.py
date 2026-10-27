"""Unit tests for strict parser, oracle, and detectors."""

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))

from runner.detector import detect_acceptance
from runner.oracle import CorrectnessOracle, reconstruct_reference_output
from runner.strict_parser import StrictParseError, json_semantic_equal, parse_strict_json

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def cases():
    cases_path = BASE_DIR / "inputs" / "cases.json"
    return json.loads(cases_path.read_text(encoding="utf-8"))


def test_strict_parser_valid():
    text = '  {"a": 1, "b": "hello", "c": true, "d": null, "e": [1, 2]}  '
    parsed = parse_strict_json(text)
    assert parsed == {"a": 1, "b": "hello", "c": True, "d": None, "e": [1, 2]}


def test_strict_parser_rejects_markdown():
    text = '```json\n{"a": 1}\n```'
    with pytest.raises(StrictParseError):
        parse_strict_json(text)


def test_strict_parser_rejects_prose():
    text = 'Here is your JSON: {"a": 1}'
    with pytest.raises(StrictParseError):
        parse_strict_json(text)


def test_strict_parser_rejects_duplicate_keys():
    text = '{"a": 1, "a": 2}'
    with pytest.raises(StrictParseError):
        parse_strict_json(text)


def test_strict_parser_rejects_non_object():
    with pytest.raises(StrictParseError):
        parse_strict_json('[1, 2, 3]')


def test_semantic_equality():
    # Number equivalence
    assert json_semantic_equal({"a": 1.0}, {"a": 1})
    # Booleans distinct from numbers
    assert not json_semantic_equal({"a": True}, {"a": 1})
    assert not json_semantic_equal({"a": False}, {"a": 0})
    # Array order strictly preserved
    assert not json_semantic_equal({"a": [1, 2]}, {"a": [2, 1]})
    # Object key order agnostic
    assert json_semantic_equal({"a": 1, "b": 2}, {"b": 2, "a": 1})


def test_oracle_reconstruction_all_100_cases(cases):
    oracle = CorrectnessOracle()
    for c in cases:
        recon = reconstruct_reference_output(c)
        assert json_semantic_equal(recon, c['expected_output']), f"Reconstruction failed for {c['id']}"

        # Test oracle scoring on gold string
        gold_str = json.dumps(c['expected_output'])
        is_correct, parsed, err = oracle.score_response(c, gold_str)
        assert is_correct is True, f"Oracle score failed for {c['id']}: {err}"


def test_detectors_accept_all_100_gold_outputs(cases):
    for c in cases:
        gold_str = json.dumps(c['expected_output'])
        for arm in ("A", "B", "C", "D"):
            det = detect_acceptance(c, gold_str, arm)
            assert det.accepted is True, f"Arm {arm} falsely rejected gold output for {c['id']}: {det.diagnostics}"

