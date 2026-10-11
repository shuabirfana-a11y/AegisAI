import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createFrontendServer } from '../server.mjs';

async function start(t, server) {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => { server.closeAllConnections(); server.close(); });
  return `http://127.0.0.1:${server.address().port}`;
}

test('static deep links serve the app while unknown files remain 404', async t => {
  const url = await start(t, createFrontendServer());
  const page = await fetch(url + '/vulnerabilities/CVE-2025-32434');
  assert.equal(page.status, 200);
  assert.match(await page.text(), /AegisAI/);
  assert.equal((await fetch(url + '/missing.js')).status, 404);
});

test('proxy preserves authorization but excludes cookies and backend cookies', async t => {
  let received;
  const upstream = http.createServer((req, res) => {
    received = req.headers;
    res.writeHead(200, { 'content-type': 'application/json', 'set-cookie': 'secret=backend' });
    res.end('{"items":[]}');
  });
  await start(t, upstream);
  const url = await start(t, createFrontendServer({ backendPort: upstream.address().port }));
  const response = await fetch(url + '/api/v1/assets', { headers: { Authorization: 'Bearer test-secret', Cookie: 'browser=secret' } });
  assert.equal(response.status, 200);
  assert.equal(received.authorization, 'Bearer test-secret');
  assert.equal(received.cookie, undefined);
  assert.equal(response.headers.get('set-cookie'), null);
});

test('local demo keeps its backend token on the server and advertises that mode to the page', async t => {
  const upstream = http.createServer((req, res) => {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ authorization: req.headers.authorization }));
  });
  await start(t, upstream);
  const url = await start(t, createFrontendServer({ backendPort: upstream.address().port, localDemoToken: 'server-only-token' }));
  const config = await fetch(url + '/client-config').then(response => response.json());
  assert.deepEqual(config, { localDemoAccess: true });
  const response = await fetch(url + '/api/v1/assets', { headers: { Authorization: 'Bearer attacker-controlled' } });
  assert.equal((await response.json()).authorization, 'Bearer server-only-token');
  assert.equal((await fetch(url + '/health').then(response => response.json())).authorization, undefined);
});

test('assistant writes reject cross-origin requests before reaching the backend', async t => {
  const url = await start(t, createFrontendServer());
  const response = await fetch(url + '/api/v1/assistant/query', { method: 'POST', headers: { Origin: 'https://attacker.invalid', 'Content-Type': 'application/json' }, body: '{}' });
  assert.equal(response.status, 403);
});

test('same-origin assistant writes preserve JSON body and HTTP conflict', async t => {
  let body = '';
  const upstream = http.createServer((req, res) => {
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => { res.writeHead(409, { 'content-type': 'application/json' }); res.end('{"detail":"conflict"}'); });
  });
  await start(t, upstream);
  const url = await start(t, createFrontendServer({ backendPort: upstream.address().port }));
  const response = await fetch(url + '/api/v1/assistant/query', { method: 'POST', headers: { Origin: url, 'Content-Type': 'application/json' }, body: '{"question":"existing data"}' });
  assert.equal(response.status, 409);
  assert.equal(body, '{"question":"existing data"}');
});

test('unavailable backend produces a clear 502 JSON error', async t => {
  const unavailable = http.createServer();
  const unavailableUrl = await start(t, unavailable);
  const port = Number(new URL(unavailableUrl).port);
  await new Promise(resolve => unavailable.close(resolve));
  const url = await start(t, createFrontendServer({ backendPort: port }));
  const response = await fetch(url + '/health');
  assert.equal(response.status, 502);
  assert.match((await response.json()).detail, /Backend/);
});

test('oversized assistant body returns a single 413 and leaves the server usable', async t => {
  const upstream = http.createServer((req, res) => req.on('end', () => { res.end('{}'); }));
  upstream.on('clientError', socket => {});
  await start(t, upstream);
  const url = await start(t, createFrontendServer({ backendPort: upstream.address().port }));
  const response = await fetch(url + '/api/v1/assistant/query', { method: 'POST', headers: { Origin: url, 'Content-Type': 'application/json' }, body: 'x'.repeat(3 * 1024 * 1024) });
  assert.equal(response.status, 413);
  assert.equal((await fetch(url + '/dashboard')).status, 200);
});
