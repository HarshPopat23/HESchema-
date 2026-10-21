"""Public evidence must independently support the published model outcomes."""

import json
import runpy
import shutil
from pathlib import Path

import pytest

from heschema.confirmation import PACK, sha

VERIFY = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/verify_confirmation_evidence.py'))['verify']


@pytest.mark.skipif(not (PACK / 'evidence/manifest.json').exists(), reason='Live evidence not attached yet')
def test_published_evidence_is_reconstructable_without_private_traces():
    result = VERIFY()
    summary = json.loads((PACK / 'evidence/summary.json').read_text())
    assert result['verifiedResponses'] == summary['returnedResponses']
    assert result['completedSlots'] == summary['completedSlots']


@pytest.mark.skipif(not (PACK / 'evidence/manifest.json').exists(), reason='Live evidence not attached yet')
def test_recomputed_manifest_cannot_hide_false_success(tmp_path):
    pack = tmp_path / 'pack'
    shutil.copytree(PACK, pack)
    path = pack / 'evidence/responses.jsonl'
    responses = [json.loads(line) for line in path.read_text().splitlines()]
    responses[0]['correct'] = not responses[0]['correct']
    path.write_text(''.join(json.dumps(r) + '\n' for r in responses))
    manifest_path = pack / 'evidence/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['files']['responses.jsonl'] = sha(path)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='oracle judgment'):
        VERIFY(pack)
