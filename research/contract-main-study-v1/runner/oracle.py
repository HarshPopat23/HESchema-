"""Independent correctness oracle for HESchema Main Study.

Reconstructs expected outputs from frozen source projections independently
of HESchema's PASS/FAIL result, and evaluates candidate objects strictly.
"""

from typing import Any, Dict, Optional, Tuple

try:
    from .strict_parser import StrictParseError, json_semantic_equal, parse_strict_json
except ImportError:
    from strict_parser import StrictParseError, json_semantic_equal, parse_strict_json


def reconstruct_reference_output(case: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically reconstructs the ground-truth output from the frozen case context data."""
    cid = case['id']
    data = case['context']['data']

    if cid.startswith('WF-'):
        files = data['files']
        return {
            "workflowName": data['workflowName'],
            "files": files,
            "fileCount": len(files),
            "totalSizeBytes": sum(f['sizeInBytes'] for f in files)
        }
    elif cid.startswith('USGS-'):
        feat = data['feature']
        props = feat.get('properties', {})
        coords = feat.get('geometry', {}).get('coordinates', [None, None, None])
        return {
            "eventId": feat.get('id'),
            "magnitude": props.get('mag'),
            "place": props.get('place'),
            "timeUnixMs": props.get('time'),
            "eventType": props.get('type'),
            "tsunami": props.get('tsunami'),
            "alert": props.get('alert'),
            "longitude": coords[0],
            "latitude": coords[1],
            "depthKm": coords[2]
        }
    elif cid.startswith('GBFS-'):
        stations = data['stations']
        return {
            "stations": stations,
            "stationCount": len(stations),
            "totalCapacity": sum(s['capacity'] for s in stations)
        }
    elif cid.startswith('CR-'):
        work = data['work']
        authors = work.get('author')
        res = {
            "doi": work.get('DOI'),
            "titles": work.get('title', []),
            "publisher": work.get('publisher'),
            "workType": work.get('type'),
        }
        if authors is not None:
            res["authors"] = authors
            res["listedAuthorCount"] = len(authors)
        else:
            res["listedAuthorCount"] = 0
        return res
    elif cid.startswith('PYPI-'):
        files = data['files']
        return {
            "project": data['project'],
            "version": data['version'],
            "files": files,
            "fileCount": len(files),
            "totalSizeBytes": sum(f['size'] for f in files)
        }
    else:
        raise ValueError(f"Unknown case family or ID: {cid}")


class CorrectnessOracle:
    """Evaluates raw model text against reconstructed reference output."""

    def __init__(self, gold_by_id: Optional[Dict[str, Any]] = None):
        self.gold_by_id = gold_by_id or {}

    def score_response(self, case: Dict[str, Any], raw_text: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Scores a raw completion.
        
        Returns:
            (is_correct, parsed_json_or_none, failure_reason)
        """
        # 1. Strict parsing
        try:
            parsed = parse_strict_json(raw_text)
        except StrictParseError as exc:
            return False, None, exc.code
        except Exception:
            return False, None, "formatting_or_json_parse"

        # 2. Reference reconstruction
        cid = case['id']
        expected = self.gold_by_id.get(cid)
        if expected is None:
            expected = reconstruct_reference_output(case)

        # 3. Semantic comparison
        is_correct = json_semantic_equal(parsed, expected)
        if not is_correct:
            return False, parsed, "oracle_semantic_mismatch"

        return True, parsed, None
