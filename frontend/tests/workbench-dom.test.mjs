import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';

const A = '11111111-1111-4111-8111-111111111111';
const B = '22222222-2222-4222-8222-222222222222';
const gateFor = id => id === A ? '33333333-3333-4333-8333-333333333333' : '44444444-4444-4444-8444-444444444444';
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const flush = async () => { for (let i = 0; i < 4; i++) await new Promise(resolve => setImmediate(resolve)); };
async function until(check) { for (let i = 0; i < 80; i++) { if (check()) return; await new Promise(resolve => setTimeout(resolve, 5)); } assert.ok(check(), 'expected page condition did not appear'); }

function fixture(id, op, overall = 'SUCCEEDED') {
  const common = { investigation_id: id, logical_investigation_id: id };
  if (op === 'status') return { ...common, current_stage: 'COMPLETED', status: 'COMPLETED', overall_status: overall, revision: 1, warnings: [] };
  if (op === 'trace') return { ...common, integration_result_id: gateFor(id), revision: 1, stages: [], runs: [], warnings: [], planner: null };
  if (op === 'artifacts') return { ...common, revision: 1, investigation: null, verification: null, analysis: null };
  if (op === 'answer') return { ...common, integration_result_id: gateFor(id), answer_status: 'COMPLETE', integration_status: 'PASS', summary: 'Answer ' + id, warnings: [], risk_assessment: { risk_level: 'HIGH', affected: true } };
  if (op === 'integration') return { integration_id: gateFor(id), logical_investigation_id: id, status: 'PASS', checks: [], warnings: [], objective_coverage: [] };
  return { ...fixture(id, 'status'), cancel_requested: false };
}

async function environment(t, handler = () => undefined, url = 'http://127.0.0.1:8769/assistant') {
  const dom = new JSDOM('<main id="view"></main>', { url, pretendToBeVisual: true });
  dom.window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  const previous = new Map();
  for (const key of ['window', 'document', 'location', 'localStorage', 'Node', 'HTMLElement', 'CustomEvent', 'requestAnimationFrame', 'cancelAnimationFrame']) {
    previous.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { configurable: true, writable: true, value: key.endsWith('AnimationFrame') ? dom.window[key].bind(dom.window) : dom.window[key] });
  }
  const controller = new AbortController();
  const calls = []; let savedRun = null;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(url, dom.window.location.href).pathname;
    calls.push({ path, options });
    const override = handler(path, options);
    if (override !== undefined) return await override;
    if (path.startsWith('/mock/')) return json(JSON.parse(await readFile(new URL('../public' + path, import.meta.url), 'utf8')));
    if (path === '/api/investigations/history') return json({ items: [], total: 0 });
    const match = path.match(/^\/api\/investigations\/([^/]+)\/([^/]+)$/);
    if (match) return json(fixture(match[1], match[2]));
    throw new Error('unexpected test request ' + path);
  };
  const view = dom.window.document.querySelector('#view');
  const session = { getToken: () => '', getRunId: () => savedRun, setRunId: id => { savedRun = id; } };
  t.after(() => {
    controller.abort(); dom.window.close(); globalThis.fetch = originalFetch;
    for (const [key, descriptor] of previous) { if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key]; }
  });
  const open = async () => { const { assistant } = await import('../public/modules/pages/assistant.js'); assistant(view, { signal: controller.signal, session, localDemoAccess: true }); await flush(); };
  const submit = () => view.querySelector('#inv-question').closest('form').dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }));
  const watch = id => { const input = view.querySelector('[aria-label="已有调查 ID"]'); input.value = id; input.form.dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true })); };
  return { dom, view, controller, session, calls, open, submit, watch, runId: () => savedRun };
}

for (const [name, data, expected] of [
  ['complete', { canonical_id: 'CVE-2099-10001', title: 'Returned title', description: 'Returned description', claims: [], evidence: [] }, 'SUCCESS'],
  ['partial/null fields', { canonical_id: 'CVE-2099-10001', title: null, description: null, claims: [null], evidence: [null], affected_versions: null }, 'WARNING'],
  ['empty', null, 'EMPTY'],
  ['warning', { canonical_id: 'CVE-2099-10001', title: 'Returned title', description: 'Returned description', warnings: ['SOURCE_DELAY'], conflicts: [] }, 'WARNING'],
  ['invalid payload', [], 'ERROR'],
]) test('vulnerability detail handles ' + name + ' without crashing', async t => {
  const env = await environment(t);
  const { vulnerability } = await import('../public/modules/pages/vulnerabilities.js');
  vulnerability(env.view, { signal: env.controller.signal, api: { vulnerability: async () => data } }, { id: 'CVE-2099-10001' });
  await flush();
  assert.doesNotMatch(env.view.textContent, /fields is not defined|Cannot read properties/);
  assert.equal(env.view.querySelector('[data-view-state]')?.dataset.viewState, expected);
  if (name === 'complete') assert.match(env.view.textContent, /Returned description/);
  if (name === 'warning') assert.match(env.view.textContent, /SOURCE_DELAY/);
});

test('vulnerability loading/error states preserve server failure', async t => {
  const env = await environment(t); const pending = deferred();
  const { vulnerability } = await import('../public/modules/pages/vulnerabilities.js');
  vulnerability(env.view, { signal: env.controller.signal, api: { vulnerability: () => pending.promise } }, { id: 'CVE-2099-10001' });
  assert.equal(env.view.querySelector('[data-view-state]')?.dataset.viewState, 'LOADING');
  pending.reject(Object.assign(new Error('SOURCE_UNAVAILABLE'), { status: 503 })); await flush();
  assert.equal(env.view.querySelector('[data-view-state]')?.dataset.viewState, 'ERROR');
  assert.match(env.view.textContent, /SOURCE_UNAVAILABLE/);
});

test('aborted vulnerability read never appends its late result', async t => {
  const env = await environment(t); const pending = deferred();
  const { vulnerability } = await import('../public/modules/pages/vulnerabilities.js');
  vulnerability(env.view, { signal: env.controller.signal, api: { vulnerability: () => pending.promise } }, { id: 'CVE-2099-10001' });
  env.controller.abort(); const original = env.view.textContent;
  pending.resolve({ title: 'LATE RESULT' }); await flush(); assert.equal(env.view.textContent, original);
});

test('NEED_CONTEXT shows missing information without acceptance, run ID or polling', async t => {
  const env = await environment(t, path => path === '/api/investigations' ? json({ status: 'NEED_CONTEXT', missing_fields: ['version', 'asset_context'], message: 'Please supply context', next_actions: ['SUPPLY_CONTEXT'], investigation_created: false, execution_mode: 'NOT_STARTED' }) : undefined);
  await env.open(); env.view.querySelector('#inv-question').value = 'Check component risk'; env.submit(); await flush();
  assert.match(env.view.textContent, /NEED_CONTEXT/); assert.match(env.view.textContent, /目标组件版本/); assert.match(env.view.textContent, /目标资产信息/);
  assert.doesNotMatch(env.view.textContent, /已受理|undefined/);
  assert.equal(env.runId(), null);
  assert.equal(env.calls.filter(c => /\/(status|trace|answer)$/.test(c.path)).length, 0);
  assert.equal(env.view.querySelector('[aria-label="已有调查 ID"]').value, '');
});

for (const [overall, mapped] of [['SUCCEEDED_WITH_WARNINGS', 'WARNING'], ['FAILED', 'FAILED'], ['REVIEW_REQUIRED', 'HUMAN_REVIEW_REQUIRED']]) test('workbench preserves status ' + overall, async t => {
  const env = await environment(t, path => path.endsWith('/status') ? json(fixture(B, 'status', overall)) : undefined);
  await env.open(); env.watch(B); await flush();
  assert.match(env.view.textContent, new RegExp(overall));
  assert.equal(env.view.querySelector('[data-ui-state]')?.dataset.uiState, mapped);
});

for (const op of ['status', 'trace', 'answer', 'artifacts', 'integration']) test('late ' + op + ' from A cannot replace B, even if network ignores abort', async t => {
  const pending = deferred();
  const env = await environment(t, path => path === '/api/investigations/' + A + '/' + op ? pending.promise : undefined);
  await env.open(); env.watch(A); await until(() => env.calls.some(c => c.path.endsWith(A + '/' + op)));
  const oldCall = env.calls.find(c => c.path.endsWith(A + '/' + op));
  env.watch(B); await until(() => env.view.textContent.includes('Answer ' + B));
  pending.resolve(json(fixture(A, op))); await flush();
  assert.equal(env.runId(), B); assert.equal(env.view.querySelector('[aria-label="已有调查 ID"]').value, B);
  assert.doesNotMatch(env.view.textContent, /Answer 11111111/);
  assert.equal(oldCall.options.signal.aborted, true);
});

test('late create cannot overwrite a newer selected investigation', async t => {
  const pending = deferred(); const env = await environment(t, path => path === '/api/investigations' ? pending.promise : undefined);
  await env.open(); env.view.querySelector('#inv-question').value = 'First request'; env.submit(); await flush();
  env.watch(B); await until(() => env.view.textContent.includes('Answer ' + B));
  pending.resolve(json({ ...fixture(A, 'status'), reused: false, is_mock: false }, 202)); await flush();
  assert.equal(env.runId(), B); assert.doesNotMatch(env.view.textContent, /已受理/);
});

test('late error from A does not add an error to B', async t => {
  const pending = deferred(); const env = await environment(t, path => path === '/api/investigations/' + A + '/status' ? pending.promise : undefined);
  await env.open(); env.watch(A); await flush(); env.watch(B);
  await until(() => env.view.textContent.includes('Answer ' + B)); pending.reject(new Error('OLD_NETWORK_FAILURE')); await flush();
  assert.doesNotMatch(env.view.textContent, /OLD_NETWORK_FAILURE|无法连接调查 API/); assert.equal(env.runId(), B);
});

test('late real history cannot populate a newly selected Mock mode', async t => {
  const pending = deferred(); const env = await environment(t, path => path === '/api/investigations/history' ? pending.promise : undefined);
  await env.open(); [...env.view.querySelectorAll('button')].find(b => b.textContent === 'Mock 演示').click();
  await until(() => env.view.textContent.includes('MOCK_ONLY'));
  pending.resolve(json({ items: [{ ...fixture(A, 'status'), original_question: 'OLD_REAL_HISTORY' }] })); await flush();
  assert.doesNotMatch(env.view.textContent, /OLD_REAL_HISTORY/); assert.match(env.view.textContent, /MOCK_ONLY/);
});

test('wrong status root is rejected instead of switching the selected investigation', async t => {
  const env = await environment(t, path => path.endsWith(B + '/status') ? json(fixture(A, 'status')) : undefined);
  await env.open(); env.watch(B); await flush(); assert.equal(env.runId(), B);
  assert.match(env.view.textContent, /ROOT_BINDING_MISMATCH/); assert.doesNotMatch(env.view.textContent, /Answer 11111111/);
});

test('unknown status is not presented as completed and does not read final answer', async t => {
  const env = await environment(t, path => path.endsWith(B + '/status') ? json(fixture(B, 'status', 'FUTURE_STATE')) : undefined);
  await env.open(); env.watch(B); await flush();
  assert.match(env.view.textContent, /FUTURE_STATE/);
  assert.equal(env.calls.some(c => c.path.endsWith('/answer')), false);
});

test('contradictory create roots are rejected before acceptance or polling', async t => {
  const env = await environment(t, path => path === '/api/investigations' ? json({ ...fixture(A, 'status'), logical_investigation_id: B, reused: false }, 202) : undefined);
  await env.open(); env.view.querySelector('#inv-question').value = 'Read vulnerability'; env.submit(); await flush();
  assert.match(env.view.textContent, /ROOT_BINDING_MISMATCH/);
  assert.doesNotMatch(env.view.textContent, /已受理/); assert.equal(env.runId(), null);
  assert.equal(env.calls.some(c => c.path.endsWith('/status')), false);
});

test('missing required status root is rejected instead of accepting an unbound response', async t => {
  const env = await environment(t, path => path.endsWith(B + '/status') ? json({ overall_status: 'SUCCEEDED', current_stage: 'COMPLETED', revision: 1 }) : undefined);
  await env.open(); env.watch(B); await flush();
  assert.match(env.view.textContent, /ROOT_BINDING_MISMATCH/); assert.equal(env.runId(), B);
  assert.equal(env.calls.some(c => c.path.endsWith('/answer')), false);
});

test('delayed cancellation cannot replace a newer terminal revision', async t => {
  const pending = deferred(); let polls = 0;
  const env = await environment(t, path => {
    if (path.endsWith(B + '/cancel')) return pending.promise;
    if (path.endsWith(B + '/status')) { polls += 1; return json({ ...fixture(B, 'status', polls === 1 ? 'RUNNING' : 'SUCCEEDED'), current_stage: polls === 1 ? 'PLANNING' : 'COMPLETED', revision: polls }); }
  });
  await env.open(); env.watch(B); await flush();
  [...env.view.querySelectorAll('button')].find(b => b.textContent === '请求取消').click();
  await new Promise(resolve => setTimeout(resolve, 1100)); await until(() => env.view.textContent.includes('Answer ' + B));
  pending.resolve(json({ ...fixture(B, 'status', 'RUNNING'), current_stage: 'PLANNING', revision: 1, cancel_requested: true })); await flush();
  assert.equal(env.view.querySelector('[data-ui-state]').dataset.uiState, 'COMPLETED');
  assert.doesNotMatch(env.view.querySelector('[data-panel-id="status"]').textContent, /等待终态|处理中/);
});

test('Gate internal logical ID may differ from HTTP root when its Trace reference matches', async t => {
  const env = await environment(t, path => path.endsWith(B + '/integration') ? json({ ...fixture(B, 'integration'), logical_investigation_id: A }) : undefined);
  await env.open(); env.watch(B); await until(() => env.view.querySelector('[data-panel-id="gate"]').textContent.includes('PASS'));
  assert.doesNotMatch(env.view.textContent, /ROOT_BINDING_MISMATCH/);
});

test('Gate with a different integration ID is rejected despite a matching HTTP root', async t => {
  const env = await environment(t, path => path.endsWith(B + '/integration') ? json({ ...fixture(B, 'integration'), integration_id: A }) : undefined);
  await env.open(); env.watch(B); await flush();
  assert.match(env.view.querySelector('[data-panel-id="gate"]').textContent, /ROOT_BINDING_MISMATCH/);
});
