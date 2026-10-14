import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createInvestigationClient, InvestigationApiError, retryDelayMs } from '../public/modules/investigation-client.js';
import { createMockInvestigationClient, loadMockSources, loadIndependentGate, MOCK_SCENARIOS } from '../public/modules/investigation-mock.js';

const mockRoot = fileURLToPath(new URL('../public/mock/', import.meta.url));

/** 浏览器 fetch 的等价物：直接从 public/mock 读取静态回执。 */
async function mockFetch(path) {
  const name = String(path).split('/').pop();
  const body = await readFile(mockRoot + name, 'utf8');
  return { ok: true, status: 200, json: async () => JSON.parse(body) };
}

async function fixture(t, handle) {
  const server = http.createServer(handle);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => { server.closeAllConnections(); server.close(); });
  return `http://127.0.0.1:${server.address().port}`;
}

function jsonResponse(res, status, value, headers = {}) {
  res.writeHead(status, { 'content-type': 'application/json', ...headers });
  res.end(JSON.stringify(value));
}

async function replayToTerminal(client) {
  const created = await client.create({ user_query: '回放测试' }, 'test-key');
  let status = created;
  for (let i = 0; i < 40 && status.overall_status === 'RUNNING'; i++) status = await client.status(created.investigation_id);
  return { created, status };
}

// ---- 真实客户端（传输层） --------------------------------------------------

test('create posts the stable idempotency key and keeps 202 as accepted rather than finished', async t => {
  let received;
  const base = await fixture(t, (req, res) => {
    received = { method: req.method, url: req.url, key: req.headers['idempotency-key'] };
    jsonResponse(res, 202, { investigation_id: 'abc', overall_status: 'RUNNING', revision: 0 }, { location: '/api/investigations/abc', 'retry-after': '1' });
  });
  const client = createInvestigationClient({ fetchImpl: (path, options) => fetch(base + path, options) });
  const data = await client.create({ user_query: '  vLLM 是否受影响？  ' }, 'frontend-stable-key');
  assert.deepEqual(received, { method: 'POST', url: '/api/investigations', key: 'frontend-stable-key' });
  assert.equal(data.overall_status, 'RUNNING');
});

test('create validates question length and idempotency key before any network call', async () => {
  let calls = 0;
  const client = createInvestigationClient({ fetchImpl: async () => { calls++; throw new Error('must not be called'); } });
  assert.throws(() => client.create({ user_query: '   ' }, 'k'), error => error.kind === 'invalid_request');
  assert.throws(() => client.create({ user_query: 'x'.repeat(2001) }, 'k'), error => error.kind === 'invalid_request');
  assert.throws(() => client.create({ user_query: 'ok' }, ''), error => error.kind === 'invalid_request');
  assert.equal(calls, 0);
});

test('http failures preserve error_code, request_id, retryability and Retry-After', async t => {
  const base = await fixture(t, (req, res) => {
    jsonResponse(res, 409, { error_code: 'RESULT_NOT_READY', message: '尚未产生该结果', request_id: 'req-1', retryable: true }, { 'retry-after': '2' });
  });
  const client = createInvestigationClient({ fetchImpl: (path, options) => fetch(base + path, options) });
  await assert.rejects(client.status('some-id'), error => error instanceof InvestigationApiError
    && error.status === 409 && error.code === 'RESULT_NOT_READY' && error.requestId === 'req-1'
    && error.retryable === true && error.retryAfter === 2);
});

test('retryDelayMs uses Retry-After with a one second floor', () => {
  assert.equal(retryDelayMs(new InvestigationApiError('busy', { retryAfter: 3 })), 3000);
  assert.equal(retryDelayMs(new InvestigationApiError('busy')), 1000);
});

test('network failures and non-JSON responses are explicit, never silent success', async t => {
  const offline = createInvestigationClient({ fetchImpl: async () => { throw new TypeError('fetch failed'); } });
  await assert.rejects(offline.status('x'), error => error.kind === 'network' && error.status === 0);
  const base = await fixture(t, (req, res) => { res.writeHead(200); res.end('<html>not JSON</html>'); });
  const client = createInvestigationClient({ fetchImpl: (path, options) => fetch(base + path, options) });
  await assert.rejects(client.trace('x'), error => error.kind === 'invalid_response');
});

test('history forwards filters as query parameters', async t => {
  let url;
  const base = await fixture(t, (req, res) => { url = req.url; jsonResponse(res, 200, { items: [], total: 0 }); });
  const client = createInvestigationClient({ fetchImpl: (path, options) => fetch(base + path, options) });
  await client.history({ limit: 10, sort: 'created_desc' });
  assert.equal(url, '/api/investigations/history?limit=10&sort=created_desc');
});

test('bearer token is attached unless local demo access is enabled', async t => {
  const seen = [];
  const base = await fixture(t, (req, res) => { seen.push(req.headers.authorization || null); jsonResponse(res, 200, {}); });
  const authed = createInvestigationClient({ getToken: () => 'tok', fetchImpl: (path, options) => fetch(base + path, options) });
  await authed.status('i');
  const demo = createInvestigationClient({ getToken: () => 'tok', localDemoAccess: true, fetchImpl: (path, options) => fetch(base + path, options) });
  await demo.status('i');
  assert.deepEqual(seen, ['Bearer tok', null]);
});

// ---- Mock 驱动（状态回放） -------------------------------------------------

test('mock replay reaches the recorded terminal status for every scenario', async () => {
  for (const name of MOCK_SCENARIOS) {
    const client = createMockInvestigationClient({ scenario: name, fetchImpl: mockFetch });
    const sources = await loadMockSources({ scenario: name, fetchImpl: mockFetch });
    const { created, status } = await replayToTerminal(client, name);
    if (sources.trace.events.length > 0) assert.equal(created.overall_status, 'RUNNING', name);
    assert.notEqual(status.overall_status, 'RUNNING', name);
    assert.equal(status.overall_status, sources.status.overall_status, name);
    assert.equal(status.investigation_id, sources.status.logical_investigation_id, name);
  }
});

test('mock terminal statuses keep INCOMPLETE, REVIEW_REQUIRED and CANCELLED honest', async () => {
  const expectations = {
    REPLAN_REQUIRED: 'INCOMPLETE',
    HUMAN_REVIEW_REQUIRED: 'REVIEW_REQUIRED',
    CANCELLED: 'CANCELLED',
    FAILED: 'FAILED',
    PASS: 'SUCCEEDED'
  };
  for (const [name, expected] of Object.entries(expectations)) {
    const client = createMockInvestigationClient({ scenario: name, fetchImpl: mockFetch });
    const { status } = await replayToTerminal(client, name);
    assert.equal(status.overall_status, expected, name);
  }
});

test('mock revisions increase monotonically so stale responses can be discarded', async () => {
  const client = createMockInvestigationClient({ scenario: 'PASS', fetchImpl: mockFetch });
  const created = await client.create({ user_query: 'q' }, 'k');
  let last = created.revision;
  for (let i = 0; i < 12; i++) {
    const status = await client.status(created.investigation_id);
    assert.ok(status.revision >= last);
    last = status.revision;
    if (status.overall_status !== 'RUNNING') break;
  }
});

test('mock cancel becomes CANCELLED only after the terminal snapshot arrives', async () => {
  const client = createMockInvestigationClient({ scenario: 'PASS', fetchImpl: mockFetch });
  const created = await client.create({ user_query: 'q' }, 'k');
  await client.status(created.investigation_id);
  const ack = await client.cancel(created.investigation_id);
  assert.equal(ack.cancel_requested, true);
  assert.equal(ack.overall_status, 'RUNNING');
  let status = ack;
  for (let i = 0; i < 5 && status.overall_status === 'RUNNING'; i++) status = await client.status(created.investigation_id);
  assert.equal(status.overall_status, 'CANCELLED');
  assert.equal(status.cancel_requested, true);
});

test('mock keeps the answer unready during replay and never fabricates a gate receipt', async () => {
  const client = createMockInvestigationClient({ scenario: 'PASS', fetchImpl: mockFetch });
  const created = await client.create({ user_query: 'q' }, 'k');
  await assert.rejects(client.answer(created.investigation_id), error => error.code === 'RESULT_NOT_READY' && error.retryable === true);
  await assert.rejects(client.integration(created.investigation_id), error => error.code === 'MOCK_GATE_NOT_INCLUDED');
});

test('mock reports missing artifacts instead of inventing nodes', async () => {
  const client = createMockInvestigationClient({ scenario: 'PASS', fetchImpl: mockFetch });
  const created = await client.create({ user_query: 'q' }, 'k');
  const artifacts = await client.artifacts(created.investigation_id);
  assert.equal(artifacts.investigation, null);
  assert.equal(artifacts.verification, null);
  assert.equal(artifacts.analysis, null);
  assert.equal(typeof artifacts.mock_missing, 'string');
});

test('openScenario jumps to a stored terminal record with a readable answer', async () => {
  const client = createMockInvestigationClient({ scenario: 'PASS', fetchImpl: mockFetch });
  const sources = await loadMockSources({ scenario: 'HUMAN_REVIEW_REQUIRED', fetchImpl: mockFetch });
  const id = sources.status.logical_investigation_id;
  await client.openScenario(id);
  const status = await client.status(id);
  assert.equal(status.overall_status, 'REVIEW_REQUIRED');
  const answer = await client.answer(id);
  assert.equal(answer.integration_status, sources.answer.integration_status);
  assert.equal(answer.mock_scenario, 'HUMAN_REVIEW_REQUIRED');
});

test('mock refuses foreign investigation ids and unknown scenarios', async () => {
  const client = createMockInvestigationClient({ scenario: 'PASS', fetchImpl: mockFetch });
  await assert.rejects(client.status('11111111-1111-4111-8111-111111111111'), error => error.status === 404 && error.code === 'INVESTIGATION_NOT_FOUND');
  await assert.rejects(client.setScenario('NOT_A_SCENARIO'), error => error.kind === 'invalid_request');
});

test('mock history filters by terminal status without mixing scenarios', async () => {
  const client = createMockInvestigationClient({ scenario: 'PASS', fetchImpl: mockFetch });
  const page = await client.history({ status: 'CANCELLED', limit: 100 });
  assert.ok(page.items.length >= 1);
  assert.ok(page.items.every(item => item.overall_status === 'CANCELLED'));
  assert.equal(page.status_filter, 'CANCELLED');
});

test('mock refuses to join fixtures whose root investigation ids disagree', async () => {
  const fetchImpl = async path => {
    const name = String(path).split('/').pop();
    const body = JSON.parse(await readFile(mockRoot + name, 'utf8'));
    if (name === 'answer-demo.json') body.scenarios.PASS.logical_investigation_id = '00000000-0000-4000-8000-000000000000';
    return { ok: true, status: 200, json: async () => body };
  };
  await assert.rejects(loadMockSources({ scenario: 'PASS', fetchImpl, basePath: '/broken-fixtures' }),
    error => error.kind === 'invalid_response' && /不一致/.test(error.message));
});

test('the independent gate sample is loadable and joins no scenario', async () => {
  const sample = await loadIndependentGate({ fetchImpl: mockFetch });
  assert.equal(sample.joinWithScenario, false);
  assert.equal(typeof sample.result.status, 'string');
  assert.ok(sample.result.status.length > 0);
});