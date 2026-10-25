"""Rebuild the frozen pack offline without touching historical evidence."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder60', ROOT / 'scripts/build_60_tasks_pack.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_checkout_rebuild_is_byte_identical_from_another_cwd(tmp_path):
    output = tmp_path / 'new-pack'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build_60_tasks_pack.py'),
                             '--output-dir', str(output)], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['caseCount'] == 60
    assert report['rebuiltSha256'] == builder.FROZEN_CASES_SHA256
    assert (output / 'cases.json').read_bytes() == (builder.TARGET_DIR / 'cases.json').read_bytes()
    assert builder.rebuild(output, check=True)['byteIdentical']


def test_changed_source_is_rejected(tmp_path):
    path = tmp_path / 'changed.md'
    path.write_bytes(builder.MD_PATH.read_bytes() + b'\nchanged\n')
    with pytest.raises(ValueError, match='Pinned H60 source hash changed'):
        builder.parse_60_tasks(path)


def test_semantic_and_byte_hash_differences_are_reported_without_overwrite(tmp_path, capsys):
    tasks = builder.parse_60_tasks()
    path = tmp_path / 'cases.json'
    path.write_text(json.dumps(tasks))
    original = path.read_bytes()
    with pytest.raises(ValueError, match='byte hash differs'):
        builder.rebuild(tmp_path, check=True)
    report = json.loads(capsys.readouterr().out)
    assert report['semanticEqual'] and not report['byteIdentical']
    with pytest.raises(ValueError, match='Refusing to replace'):
        builder.rebuild(tmp_path)
    assert path.read_bytes() == original
    tasks[0]['prompt'] += ' changed'
    path.write_text(json.dumps(tasks))
    with pytest.raises(ValueError, match='byte hash differs'):
        builder.rebuild(tmp_path, check=True)
    assert not json.loads(capsys.readouterr().out)['semanticEqual']


def test_incomplete_or_duplicate_case_inventory_is_rejected():
    tasks = builder.parse_60_tasks()
    with pytest.raises(ValueError, match='60 unique'):
        builder.validate_tasks(tasks[:-1])
    tasks[-1]['id'] = tasks[0]['id']
    with pytest.raises(ValueError, match='60 unique'):
        builder.validate_tasks(tasks)
