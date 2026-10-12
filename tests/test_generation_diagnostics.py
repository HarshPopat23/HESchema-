import asyncio

import httpx
import pytest

from heschema.cli_integration import evaluate_document_diagnostics, generated_content
from heschema.providers import Generation, Provider, ProviderError
from heschema.schema import SchemaEngine


def test_reasoning_is_not_final_and_unknown_finish_stays_unknown():
    async def check():
        transport = httpx.MockTransport(lambda r: httpx.Response(200, json={
            'model': 'test', 'message': {'content': '', 'thinking': '{"secret":1}'}, 'done': True}))
        p = Provider('ollama', model='test', interval=0, transport=transport)
        try:
            g = await p.generate([])
            assert g.text == '' and g.reasoning == '{"secret":1}'
            assert g.completion == 'empty' and g.metadata.get('finish_reason') is None
        finally:
            await p.close()
    asyncio.run(check())
    assert Generation('{}').completion == 'unknown'
    assert Generation('{}', metadata={'finish_reason': 'length'}).completion == 'truncated'


def test_cli_report_is_not_generated_document_and_nonzero_exit_can_have_output():
    engine = SchemaEngine()
    no_output = {'exitCode': 1, 'parsedJson': {'error': {'message': 'rejected'}}}
    assert generated_content(no_output) is None
    d = evaluate_document_diagnostics({}, generated_content(no_output), engine)
    assert d['stages']['json'] == 'not_evaluated' and d['jsonParseValid'] is None
    invalid = {'exitCode': 1, 'parsedJson': {'raw': 'prose {"x":1}'}}
    assert evaluate_document_diagnostics({}, generated_content(invalid), engine)['jsonParseValid'] is False
    schema_invalid = {'exitCode': 1, 'parsedJson': {'document': {'x': 'wrong'}}}
    assert evaluate_document_diagnostics({'properties': {'x': {'type': 'integer'}}}, generated_content(schema_invalid), engine)['heschemaSchemaValid'] is False
    assert generated_content({'parsedJson': {'document': None}}) == 'null'


def test_upstream_rejection_is_classified_and_body_credentials_are_absent(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://localhost')
    async def check():
        p = Provider('ollama', interval=0, transport=httpx.MockTransport(
            lambda r: httpx.Response(400, json={'error': 'API_KEY=secret-private'})))
        try:
            with pytest.raises(ProviderError) as caught:
                await p.generate([], format_schema={'type': 'object'})
            assert caught.value.code == 'request_rejected'
            assert caught.value.status == 400
            assert 'secret-private' not in str(caught.value.diagnostic())
        finally:
            await p.close()
    asyncio.run(check())


def test_cli_preview_preserves_shell_metacharacters_as_literal_arguments():
    import shlex

    from heschema.cli_integration import generate_command_previews
    prompt = "$(echo sensitive) `echo unsafe` 'quoted' $TOKEN"
    previews = generate_command_previews('a b.json', prompt, 'http://localhost', 'model $(test)', 'native_schema')
    words = shlex.split(previews['posix'])
    assert words[words.index('--ask') + 1] == prompt
    assert words[words.index('--model') + 1] == 'model $(test)'
    assert "''quoted''" in previews['powershell']


def test_cancelled_cli_process_is_terminated_and_awaited(tmp_path, monkeypatch):
    import os
    import sys

    from heschema.cli_integration import execute_cli_run
    if os.name != 'posix':
        pytest.skip('POSIX process liveness check')
    script, pidfile = tmp_path / 'blocked.py', tmp_path / 'pid.txt'
    script.write_text('import os, time\nfrom pathlib import Path\nPath(' + repr(str(pidfile)) + ').write_text(str(os.getpid()))\ntime.sleep(1000)\n')
    monkeypatch.setattr('heschema.cli_integration.resolve_cli_path', lambda: ([sys.executable, str(script)], None))
    async def check():
        task = asyncio.create_task(execute_cli_run(schema={}, prompt='test', model='test'))
        for _ in range(200):
            if pidfile.exists():
                break
            await asyncio.sleep(.01)
        assert pidfile.exists()
        pid = int(pidfile.read_text())
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    asyncio.run(check())
