import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { spawn } from 'node:child_process';
import { readFile, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import { JSDOM, VirtualConsole } from 'jsdom';

const root = fileURLToPath(new URL('../', import.meta.url));
let server, base, folder;
const delay = () => new Promise(resolve => setTimeout(resolve, 20));
async function until(condition) {
  const deadline = Date.now() + 10000;
  while (!condition()) { if (Date.now() > deadline) throw new Error('UI condition timed out'); await delay(); }
}
before(async () => {
  folder = await mkdtemp(tmpdir() + '/heschema-ui-');
  const listener = createServer();
  await new Promise(resolve => listener.listen(0, '127.0.0.1', resolve));
  const port = listener.address().port;
  await new Promise(resolve => listener.close(resolve));
  base = 'http://127.0.0.1:' + port;
  server = spawn(process.env.HESCHEMA_PYTHON || 'python', ['-m', 'uvicorn', 'heschema.api:create_app', '--factory', '--host', '127.0.0.1', '--port', String(port)], {
    cwd: root, env: { ...process.env, HESCHEMA_DB: folder + '/state.sqlite', HESCHEMA_API_TOKEN: '', HESCHEMA_ENGINE: 'jsonschema' }, stdio: 'ignore'
  });
  let ready = false;
  for (let i = 0; i < 400; i++) {
    try { if ((await fetch(base + '/health')).ok) { ready = true; break; } } catch {}
    await delay();
  }
  assert.ok(ready, 'API should start');
});
after(async () => {
  if (server && server.exitCode === null) {
    const exited = new Promise(resolve => server.once('exit', resolve));
    server.kill('SIGTERM'); await exited;
  }
  await rm(folder, { recursive: true, force: true });
});
async function page(example) {
  const html = await readFile(root + 'frontend/index.html', 'utf8');
  const app = await readFile(root + 'frontend/app.js', 'utf8');
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', error => { if (!error.message.includes('navigation')) errors.push(error); });
  const dom = new JSDOM(html, { url: base, runScripts: 'outside-only', virtualConsole });
  await new Promise(resolve => dom.window.addEventListener('load', resolve, { once: true }));
  dom.window.fetch = (url, options) => fetch(new URL(url, base), options);
  dom.window.alert = message => { throw new Error(message); };
  const downloads = [];
  dom.window.URL.createObjectURL = blob => { downloads.push(blob); return 'blob:offline'; };
  dom.window.URL.revokeObjectURL = () => {};
  dom.window.eval(app);
  dom.window.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
  const get = id => dom.window.document.getElementById(id);
  get('contract-example').value = example;
  get('tab-btn-contracts').click();
  await until(() => get('contract-definition').value.includes('-demo'));
  async function click(name) {
    const button = get('contract-' + name);
    button.click();
    await until(() => !button.disabled);
  }
  return { dom, get, click, errors, downloads };
}

test('invoice flow separates original schema, approved inputs and arithmetic; changed proposals need reapproval', async () => {
  const p = await page('invoice');
  try {
    await p.click('register');
    await p.click('validate');
    assert.match(p.get('contract-decision').textContent, /NEEDS_CONTEXT/);
    await p.click('create-context');
    await p.click('validate');
    assert.match(p.get('contract-error').textContent, /Unconfirmed/);
    await p.click('confirm');
    await p.click('validate');
    const record = JSON.parse(p.get('contract-record').textContent);
    assert.equal(record.stages.originalSchema, 'valid');
    assert.equal(record.stages.relationships, 'invalid');
    assert.equal(record.errors[0].expected, 2500);
    await p.click('good');
    await p.click('validate');
    assert.match(p.get('contract-decision').textContent, /^PASS/);
    await p.click('download');
    assert.equal(p.downloads.length, 1);
    p.get('contract-context').value = JSON.stringify({ data: { quantity: 3, unitPriceMinor: 1250 }, approvedPointers: ['/quantity', '/unitPriceMinor'] });
    await p.click('validate');
    assert.match(p.get('contract-error').textContent, /proposal changed/);
    await p.click('invalidate');
    assert.match(p.get('contract-decision').textContent, /stale/);
    assert.deepEqual(p.errors, []);
  } finally { p.dom.window.close(); }
});

test('custom tool destination can be registered without DOMAINS edits and approval invalidation blocks validation', async () => {
  const p = await page('trip');
  try {
    await p.click('register'); await p.click('create-context'); await p.click('confirm'); await p.click('validate');
    assert.match(p.get('contract-decision').textContent, /^FAIL/);
    assert.equal(JSON.parse(p.get('contract-record').textContent).stages.context, 'invalid');
    await p.click('good'); await p.click('validate');
    assert.match(p.get('contract-decision').textContent, /^PASS/);
    await p.click('invalidate'); await p.click('validate');
    assert.match(p.get('contract-error').textContent, /Unconfirmed/);
    assert.deepEqual(p.errors, []);
  } finally { p.dom.window.close(); }
});

test('contract generation selects full or compact and retains the choice in evidence', async () => {
  const p = await page('trip');
  try {
    await p.click('register'); await p.click('create-context'); await p.click('confirm');
    assert.equal(p.get('contract-prompt-style').value, 'full');
    const requests = [];
    p.dom.window.fetch = (url, options) => {
      if (url === '/contracts/generate') requests.push(JSON.parse(options.body));
      return fetch(new URL(url, base), options);
    };
    for (const style of ['full', 'compact']) {
      p.get('contract-prompt-style').value = style;
      await p.click('generate');
      assert.ok(p.get('contract-error').classList.contains('hidden'));
      assert.equal(requests.at(-1).promptStyle, style);
      const record = JSON.parse(p.get('contract-record').textContent);
      assert.equal(record.promptStyle, style);
      assert.equal(record.executionAuthorized, false);
      assert.equal(record.clientTiming.scope, 'browser_request_to_parsed_response');
      assert.ok(record.clientTiming.totalMs >= 0);
      assert.equal(record.timing.scope, 'contract_generation_handler');
      assert.equal(record.repair.timing.scope, 'repair_coordinator');
      assert.equal(record.validation.result, 'REFUSED'); // The offline provider never executes tools.
      assert.match(p.get('contract-stages').textContent, new RegExp('promptStyle' + style));
    }
    assert.deepEqual(p.errors, []);
  } finally { p.dom.window.close(); }
});

test('browser measures its own response-ready time and keeps failed-request evidence', async () => {
  const p = await page('trip');
  try {
    await p.click('register'); await p.click('create-context'); await p.click('confirm');
    let now = 1000, fail = false;
    p.dom.window.performance.now = () => now;
    p.dom.window.fetch = (url, options) => {
      if (url === '/contracts/generate') {
        now += 75; // Constructed browser clock control; not a speed measurement.
        if (fail) return Promise.reject(new Error('test connection failure'));
      }
      return fetch(new URL(url, base), options);
    };
    await p.click('generate');
    const record = JSON.parse(p.get('contract-record').textContent);
    assert.equal(record.clientTiming.totalMs, 75);
    assert.match(p.get('contract-stages').textContent, /browserResponseReady75.0 ms/);
    assert.match(p.get('contract-stages').textContent, /providerResponseMs/);
    await p.click('download');
    assert.equal(p.downloads.length, 1);
    fail = true;
    await p.click('generate');
    const failed = JSON.parse(p.get('contract-record').textContent);
    assert.equal(failed.outcome, 'request_failed');
    assert.equal(failed.clientTiming.totalMs, 75);
    assert.equal(failed.validation, undefined);
    assert.match(p.get('contract-error').textContent, /test connection failure/);
    assert.match(p.get('contract-decision').textContent, /no validation decision/);
    await p.click('download');
    assert.equal(p.downloads.length, 2);
    assert.deepEqual(p.errors, []);
  } finally { p.dom.window.close(); }
});

test('per-relationship calculation selection is registered and surfaced in generation evidence', async () => {
  const p = await page('invoice');
  try {
    const contract = JSON.parse(p.get('contract-definition').value);
    contract.id = 'invoice-application-calc-ui';
    contract.relationships[0].compute = 'application';
    p.get('contract-definition').value = JSON.stringify(contract);
    await p.click('register'); await p.click('create-context'); await p.click('confirm');
    await p.click('generate');
    assert.ok(p.get('contract-error').classList.contains('hidden'));
    const record = JSON.parse(p.get('contract-record').textContent);
    // The offline mock returns a tool refusal, not valid invoice inputs.
    assert.equal(record.validation.calculation.status, 'blocked');
    assert.equal(record.modelOutput, record.output);
    assert.equal(record.validation.accepted, false);
    assert.match(p.get('contract-stages').textContent, /applicationCalculationsblocked/);
    assert.deepEqual(p.errors, []);
  } finally { p.dom.window.close(); }
});
