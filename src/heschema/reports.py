"""Read-only adapters for historical evidence; old results are never rewritten."""

import copy
import importlib.metadata
import platform
import subprocess
from pathlib import Path

from .jsonio import digest


def provenance():
    root = Path(__file__).resolve().parents[2]
    files = [*sorted((root / 'src/heschema').glob('*.py')), root / 'pyproject.toml', root / 'native/blaze-worker.mjs', root / 'native/package-lock.json']
    content = {str(p.relative_to(root)): p.read_text(encoding='utf-8') for p in files if p.exists()}
    try:
        revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = None
    packages = {}
    for name in ('heschema', 'jsonschema', 'httpx', 'fastapi', 'numpy', 'scipy'):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {'codeHash': digest(content), 'revision': revision, 'dependencies': packages,
            'pythonVersion': platform.python_version(), 'hardware': {'machine': platform.machine(), 'processor': platform.processor() or None},
            'backendVersion': None, 'modelDigest': None}


def adapt_report(report):
    result = copy.deepcopy(report)
    current = result.get('protocolVersion', result.get('config', {}).get('protocolVersion'))
    result['sourceProtocolVersion'] = current or 'legacy_unknown'
    if current != 2:
        result['legacyAdapter'] = {'version': '1', 'inferredEvidence': False,
                                   'notice': 'Historical metrics retain their original meanings; missing completion, context and enforcement evidence remains unknown.'}
    return result
