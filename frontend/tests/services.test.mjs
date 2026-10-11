import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createApi, ApiError, normalizeRun } from '../public/modules/services.js';
import { createSession } from '../public/modules/state.js';

async function fixture(t, handle) {
  const server = http.createServer(handle);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => { server.closeAllConnections(); server.close(); });
  return `http://127.0.0.1:${server.address().port}`;
}

test('protected reads fail before network access when the memory token is absent', async () => {
  const api = createApi({ getToken: () => '' });
  await assert.rejects(api.request('/api/v1/assets', { protected: true }), error => error instanceof ApiError && error.kind === 'auth');
});

test('local demo access uses the same-origin proxy without exposing its backend token', async t => {
  let authorization;
  const base = await fixture(t, (req, res) => {
    authorization = req.headers.authorization;
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end('{"items":[],"total":0}');
  });
  const api = createApi({ localDemoAccess: true, fetchImpl: (path, options) => fetch(base + path, options) });
  assert.equal((await api.assets()).total, 0);
  assert.equal(authorization, undefined);
});

test('memory session stores a trimmed token and clears it without browser storage', () => {
  const session = createSession();
  session.setToken('  test-secret  ');
  assert.equal(session.getToken(), 'test-secret');
  session.setToken('');
  assert.equal(session.getToken(), '');
});

test('protected request forwards the token in the header and receives actual JSON', async t => {
  let received;
  const base = await fixture(t, (req, res) => {
    received = { url: req.url, authorization: req.headers.authorization };
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ items: [{ id: 'a', name: 'existing asset' }], total: 1 }));
  });
  const api = createApi({ getToken: () => 'test-secret', fetchImpl: (path, options) => fetch(base + path, options) });
  const data = await api.request('/api/v1/assets', { protected: true });
  assert.equal(data.items[0].name, 'existing asset');
  assert.deepEqual(received, { url: '/api/v1/assets', authorization: 'Bearer test-secret' });
});

test('409 is exposed as conflict with the backend detail and never becomes empty success', async t => {
  const base = await fixture(t, (req, res) => {
    res.writeHead(409, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ detail: 'request_key already used for a different question' }));
  });
  const api = createApi({ fetchImpl: (path, options) => fetch(base + path, options) });
  await assert.rejects(api.request('/api/v1/assistant/query', { method: 'POST', body: { question: 'changed' } }), error => error.kind === 'conflict' && error.status === 409 && error.message.includes('request_key'));
});

test('malformed successful API responses are explicit errors', async t => {
  const base = await fixture(t, (req, res) => { res.writeHead(200); res.end('<html>not JSON</html>'); });
  const api = createApi({ fetchImpl: (path, options) => fetch(base + path, options) });
  await assert.rejects(api.request('/health'), error => error.kind === 'invalid_response');
});

test('API client rejects absolute paths before forwarding credentials', async () => {
  const api = createApi({ getToken: () => 'test-secret' });
  await assert.rejects(api.request('https://example.invalid/api', { protected: true }), error => error.kind === 'invalid_request');
});

test('run normalization preserves conflict, unknown states and result evidence without inventing completion', () => {
  const run = normalizeRun({ run_id: 'r', trace_id: 't', status: 'WAITING_REVIEW', result: { evidence_refs: ['e'] }, warnings: ['Conflict'] });
  assert.equal(run.status, 'WAITING_REVIEW');
  assert.equal(run.shouldPoll, false);
  assert.deepEqual(run.result.evidence_refs, ['e']);
  assert.equal(normalizeRun({ status: 'VERIFYING' }).shouldPoll, true);
  assert.equal(normalizeRun({ status: 'NEW_SERVER_STATE' }).status, 'NEW_SERVER_STATE');
  assert.equal(normalizeRun({ status: 'NEW_SERVER_STATE' }).shouldPoll, false);
});

test('a list endpoint with missing items is an API schema error rather than an empty record set', async t => {
  const base = await fixture(t, (req, res) => { res.writeHead(200, { 'content-type': 'application/json' }); res.end('{"total":0}'); });
  const api = createApi({ fetchImpl: (path, options) => fetch(base + path, options) });
  await assert.rejects(api.vulnerabilities(), error => error.kind === 'invalid_response');
});

test('assistant question length is capped at the backend limit before a write is sent', async () => {
  let calls = 0;
  const api = createApi({ getToken: () => 'test-secret', fetchImpl: async () => { calls++; return { ok: true, json: async () => ({ run_id: 'accepted' }) }; } });
  await assert.rejects(api.startRun({ question: 'x'.repeat(2001), mode: 'auto', request_key: 'test-key', realtime: false }), error => error.kind === 'validation');
  assert.equal(calls, 0);
  assert.equal((await api.startRun({ question: 'x'.repeat(2000), mode: 'auto', request_key: 'test-key', realtime: false })).run_id, 'accepted');
});
