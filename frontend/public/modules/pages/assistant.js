/**
 * 智能调查工作台（/assistant）· 布局 / 交互 / 视觉重设计版。
 * 数据层不变：真实模式走 8 个 /api/investigations 接口；Mock 模式回放合成测试回执（全程 MOCK_ONLY）。
 * 状态纪律不变：202 受理 ≠ 完成；COMPLETED+INCOMPLETE 合法；Gate 原样展示；取消请求 ≠ 已取消；
 * 未知枚举保持原文中性展示；缺失 Artifact 不创建假节点；未启动阶段不显示。
 * 交互设计（高级交互设计 10 模式）：
 *  1 弹窗主题切换  2 面板拖拽排序  3 历史批量勾选(错峰)  4 密度滑块惯性吸附
 *  5 答案文本展开  6 阶段步骤条(spring)  7 开关联动 ripple  8 卡片弧线删除
 *  9 历史卡片堆叠滚动  10 状态标签展开筛选
 * 其中 3/8/10 与历史卡片的「移出视图 / 筛选 / 选择」均为本地视图操作，不改动后端记录。
 */
import { el, fields, table, message, text } from '../components.js';
import { createInvestigationClient, retryDelayMs, InvestigationApiError } from '../investigation-client.js';
import { createMockInvestigationClient, loadIndependentGate, MOCK_SCENARIOS } from '../investigation-mock.js';
import { openSettingsModal, rippleTo, clampText, makeSortable, createHistoryView, toneFor, toast } from '../wb-ui.js';

const OVERALL = new Set(['RUNNING', 'SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS', 'INCOMPLETE', 'REVIEW_REQUIRED', 'FAILED', 'CANCELLED']);
const TERMINAL = new Set(['SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS', 'INCOMPLETE', 'REVIEW_REQUIRED', 'FAILED', 'CANCELLED']);
const STAGES = new Set(['CREATED', 'PLANNING', 'INVESTIGATING', 'VERIFYING', 'ANALYZING', 'INTEGRATING', 'COMPOSING', 'COMPLETED', 'WAITING_REVIEW', 'FAILED', 'CANCELLED']);
const STAGE_ORDER = ['CREATED', 'PLANNING', 'INVESTIGATING', 'VERIFYING', 'ANALYZING', 'INTEGRATING', 'COMPOSING', 'COMPLETED', 'WAITING_REVIEW'];
const GATE = new Set(['PASS', 'PASS_WITH_WARNINGS', 'REPLAN_REQUIRED', 'HUMAN_REVIEW_REQUIRED', 'FAILED']);
const POLL_MS = 1000;
const POLL_LIMIT = 420;
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function codeLine(error) {
  const parts = [error.message];
  if (error.code) parts.push('error_code=' + error.code);
  if (error.requestId) parts.push('request_id=' + error.requestId);
  if (error.status) parts.push('HTTP ' + error.status);
  return parts.join(' · ');
}

/** 面板工厂：head（拖拽把手 + 标题 + MOCK_ONLY 徽章位）+ body（内容区）。 */
function panel(id, title, { sub = '', draggable = false } = {}) {
  const root = el('section', undefined, { class: 'wb-panel' });
  root.dataset.panelId = id;
  if (draggable) root.dataset.draggable = 'true';
  const head = el('div', undefined, { class: 'wb-panel-head' });
  if (draggable) {
    const drag = el('button', undefined, { class: 'wb-drag', type: 'button', 'aria-label': '拖拽调整面板顺序', title: '拖拽调整顺序' });
    drag.textContent = '⠿';
    head.append(drag);
  }
  const h2 = el('h2', title);
  head.append(h2);
  if (sub) head.append(el('span', sub, { class: 'wb-sub' }));
  const body = el('div', undefined, { class: 'wb-panel-body' });
  root.append(head, body);
  return { root, head, h2, body };
}

export function assistant(view, { session, signal, localDemoAccess } = {}) {
  // ---- 页面骨架 ---------------------------------------------------------
  const wb = el('div', undefined, { class: 'wb' });

  const toolbar = el('div', undefined, { class: 'wb-toolbar' });
  const crumb = el('div', undefined, { class: 'wb-crumb' });
  crumb.append(el('span', '智能调查'));
  toolbar.append(crumb, el('span', undefined, { class: 'wb-spacer' }));

  const seg = el('div', undefined, { class: 'wb-seg', role: 'group', 'aria-label': '数据模式' });
  const segReal = el('button', '真实 API', { type: 'button' });
  const segMock = el('button', 'Mock 演示', { type: 'button' });
  seg.append(segReal, segMock);
  toolbar.append(seg);

  const scenarioWrap = el('label', '场景 ');
  scenarioWrap.style.cssText = 'display:inline-flex;align-items:center;gap:.35rem;font-size:.8rem;color:var(--fg-muted)';
  const scenarioSelect = el('select', undefined, { class: 'wb-select', 'aria-label': 'Mock 场景' });
  for (const name of MOCK_SCENARIOS) scenarioSelect.append(el('option', name, { value: name }));
  scenarioWrap.append(scenarioSelect);
  toolbar.append(scenarioWrap);

  const settingsButton = el('button', '⚙ 设置', { type: 'button', class: 'wb-btn', title: '主题与信息密度' });
  settingsButton.addEventListener('click', () => openSettingsModal({}));
  toolbar.append(settingsButton);

  const mockBanner = el('p', undefined, { class: 'mock-banner', role: 'status' });

  const body = el('div', undefined, { class: 'wb-body' });
  const side = el('div', undefined, { class: 'wb-side' });
  const main = el('div', undefined, { class: 'wb-main' });
  body.append(side, main);
  wb.append(toolbar, mockBanner, body);
  view.append(wb);

  // ---- 数据模式 ---------------------------------------------------------
  const demoParam = new URLSearchParams(location.search).get('demo');
  let mode = demoParam && MOCK_SCENARIOS.includes(demoParam) ? 'mock' : 'real';
  let scenario = mode === 'mock' ? demoParam : 'PASS';
  const real = createInvestigationClient({ getToken: session.getToken, localDemoAccess });
  let mock = createMockInvestigationClient({ scenario });
  const client = () => (mode === 'mock' ? mock : real);
  let epoch = 0;
  let requestController = new AbortController();
  let historySequence = 0;
  const capture = () => ({ epoch, id: state.id, client: client(), signal: requestController.signal });
  const current = scope => scope.epoch === epoch && !signal.aborted && !scope.signal.aborted && scope.client === client() && (!scope.id || scope.id === state.id);
  function bound(scope, data, requiredRoots = ['investigation_id', 'logical_investigation_id']) {
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new InvestigationApiError('调查 API 响应格式错误。', { kind: 'invalid_response' });
    const root = scope.id || data.investigation_id;
    for (const key of requiredRoots) {
      if (typeof data[key] !== 'string' || !uuid.test(data[key])) throw new InvestigationApiError('ROOT_BINDING_MISMATCH：回执缺少合法调查 ID。', { kind: 'invalid_response', code: 'ROOT_BINDING_MISMATCH' });
    }
    for (const key of ['investigation_id', 'logical_investigation_id']) {
      if (root && data[key] !== undefined && data[key] !== root) throw new InvestigationApiError('ROOT_BINDING_MISMATCH：回执不属于当前调查。', { kind: 'invalid_response', code: 'ROOT_BINDING_MISMATCH' });
    }
    return data;
  }

  const notices = new Map();
  function setNotice(parent, key, value, kind = 'status') {
    notices.get(key)?.remove();
    const node = message(parent, value, kind);
    notices.set(key, node);
    return node;
  }
  function dropNotices(prefix) {
    for (const [key, node] of notices) if (key.startsWith(prefix)) { node.remove(); notices.delete(key); }
  }
  function syncSeg() {
    segReal.setAttribute('aria-pressed', String(mode === 'real'));
    segMock.setAttribute('aria-pressed', String(mode === 'mock'));
    scenarioWrap.hidden = mode !== 'mock';
    scenarioSelect.value = scenario;
  }
  function mockTag(p) { // MOCK_ONLY 徽章挂到面板头（可见标识，绝不省略）
    if (mode === 'mock' && !p.head.querySelector('.badge')) p.head.append(el('span', 'MOCK_ONLY', { class: 'badge' }));
  }
  function unmockTags() { for (const p of allPanels()) p.head.querySelector('.badge')?.remove(); }
  function allPanels() { return [statusPanel, stagesPanel, agentsPanel, gatePanel, answerPanel, artifactsPanel, warningsPanel, historyPanel]; }

  async function refreshBanner(scope = capture()) {
    if (!current(scope)) return;
    if (mode !== 'mock') { mockBanner.hidden = true; mockBanner.textContent = ''; return; }
    mockBanner.hidden = false;
    try {
      const info = await scope.client.info();
      if (!current(scope)) return;
      mockBanner.textContent = `Mock 演示 · 场景 ${info.scenario} · 合成测试回执（与输入无关），非真实安全情报。`;
    } catch (error) { if (current(scope)) mockBanner.textContent = 'Mock 数据加载失败：' + codeLine(error); }
  }
  async function prefillScenarioQuestion(scope = capture()) {
    const info = await scope.client.info();
    if (current(scope) && info.question) question.value = info.question;
  }

  // ---- 左栏：新建调查 -----------------------------------------------------
  const composePanel = panel('compose', '新建调查');
  side.append(composePanel.root);
  const form = el('form', undefined, { class: 'assistant-form' });

  const questionWrap = el('div'); // ripple 目标：场景切换联动预填（模式 7）
  questionWrap.style.borderRadius = 'var(--radius)';
  const questionLabel = el('label', undefined, { class: 'wb-field', for: 'inv-question' });
  questionLabel.append(el('span', '问题（1–2000 字）'));
  const question = el('textarea', undefined, { id: 'inv-question', required: '', maxlength: '2000', class: 'wb-textarea', placeholder: '例如：vLLM 0.6.0 是否受 CVE-XXXX 影响？' });
  questionLabel.append(question);
  questionWrap.append(questionLabel);
  form.append(questionWrap);

  const scopeGrid = el('div', undefined, { class: 'wb-grid-2' });
  const target = el('input', undefined, { type: 'text', maxlength: '150', placeholder: '如 CVE-2099-XXXX', 'aria-label': '目标', class: 'wb-input' });
  const assetId = el('input', undefined, { type: 'text', maxlength: '36', placeholder: '资产 UUID（可选）', 'aria-label': '资产 UUID', class: 'wb-input' });
  const componentName = el('input', undefined, { type: 'text', maxlength: '100', placeholder: '组件名，如 vllm', 'aria-label': '组件名', class: 'wb-input' });
  const componentEcosystem = el('input', undefined, { type: 'text', maxlength: '50', placeholder: '生态，如 PyPI', 'aria-label': '组件生态', class: 'wb-input' });
  const componentVersion = el('input', undefined, { type: 'text', maxlength: '50', placeholder: '版本，如 0.6.0', 'aria-label': '组件版本', class: 'wb-input' });
  for (const [node, label] of [[target, 'Target（可选）'], [assetId, '资产 UUID（可选）'], [componentName, '组件名（可选）'], [componentEcosystem, '生态（可选）'], [componentVersion, '版本（可选）']]) {
    const wrap = el('label', undefined, { class: 'wb-field' });
    wrap.append(el('span', label), node);
    scopeGrid.append(wrap);
  }
  form.append(scopeGrid);

  const optionRow = el('div', undefined, { class: 'wb-inline' });
  const runModeWrap = el('label', 'Mode', { style: 'display:inline-flex;align-items:center;gap:.35rem;font-size:.8rem;color:var(--fg-muted)' }); // ripple 目标（模式 7）
  const runMode = el('select', undefined, { class: 'wb-select', 'aria-label': '运行模式' });
  for (const value of ['auto', 'fast', 'deep']) runMode.append(el('option', value, { value }));
  runModeWrap.append(runMode);
  const realtimeLabel = el('label', undefined, { class: 'wb-switch' });
  const realtime = el('input', undefined, { type: 'checkbox' });
  realtimeLabel.append(realtime, el('span', undefined, { class: 'wb-switch-track' }), el('span', '实时信息'));
  optionRow.append(runModeWrap, realtimeLabel);
  form.append(optionRow);

  const submit = el('button', '提交调查', { type: 'submit', class: 'wb-btn wb-btn--primary' });
  const retry = el('button', '用同一幂等键重试', { type: 'button', class: 'wb-btn', hidden: '' });
  const submitRow = el('div', undefined, { class: 'wb-inline' });
  submitRow.append(submit, retry);
  form.append(submitRow);
  composePanel.body.append(form);

  const requestState = el('div', undefined, { 'aria-live': 'polite' });
  composePanel.body.append(requestState);

  // realtime ↔ mode 开关联动 ripple（模式 7）。
  realtime.addEventListener('change', () => {
    rippleTo(runModeWrap);
    toast(realtime.checked ? '需要实时信息，可能更慢。' : '不要求实时信息。');
  });

  // ---- 左栏：读取已有调查 -------------------------------------------------
  const resumePanel = panel('resume', '读取已有调查');
  side.append(resumePanel.root);
  const resumeForm = el('form', undefined, { class: 'wb-inline' });
  const resumeInput = el('input', undefined, { type: 'text', maxlength: '36', placeholder: 'Investigation UUID', 'aria-label': '已有调查 ID', class: 'wb-input' });
  resumeForm.append(resumeInput, el('button', '读取', { type: 'submit', class: 'wb-btn' }));
  resumePanel.body.append(resumeForm);

  // ---- 左栏：历史调查（模式 3/8/9/10 容器） --------------------------------
  const historyPanel = panel('history', '历史调查');
  side.append(historyPanel.root);
  setNotice(historyPanel.body, 'history:note', '只读记录；读取进入该调查，不重复提交。', 'status');
  const historyView = createHistoryView({ onOpen: openExisting });
  historyPanel.body.append(historyView.root);

  // ---- 主列：状态卡（含步骤条 · 模式 6） -----------------------------------
  const statusPanel = panel('status', '状态');
  main.append(statusPanel.root);
  const cancelButton = el('button', '请求取消', { type: 'button', class: 'wb-btn wb-btn--danger', hidden: '' });
  cancelButton.addEventListener('click', requestCancel);

  // ---- 主列：可拖拽面板（模式 2） ------------------------------------------
  const stagesPanel = panel('stages', '阶段进度', { draggable: true });
  const agentsPanel = panel('agents', 'Agent 执行', { draggable: true });
  const gatePanel = panel('gate', 'Integration Gate', { draggable: true });
  const answerPanel = panel('answer', '答案', { draggable: true });
  const artifactsPanel = panel('artifacts', 'Artifact', { draggable: true });
  const warningsPanel = panel('warnings', '警告', { draggable: true });
  main.append(stagesPanel.root, agentsPanel.root, gatePanel.root, answerPanel.root, artifactsPanel.root, warningsPanel.root);
  makeSortable(main, { storageKey: 'wb.panelOrder' });
  const panels = { status: statusPanel, stages: stagesPanel, agents: agentsPanel, gate: gatePanel, answer: answerPanel, artifacts: artifactsPanel, warnings: warningsPanel };

  function clearBody(p) { p.body.replaceChildren(); }
  function fillEmpty(p) { message(p.body, 'Empty / 尚未读取。', 'empty'); }

  // ---- 轮询状态机（规则不变） ----------------------------------------------
  const state = { id: null, lastRevision: -1, traceRevision: -1, terminal: false, polls: 0, lastStatus: null, lastStages: null, integrationId: null };
  let pollingEpoch = null;
  let timer;
  function stopPolling() { clearTimeout(timer); timer = undefined; }
  function onAbort() { stopPolling(); requestController.abort(); epoch += 1; document.removeEventListener('visibilitychange', onVisibility); }
  signal.addEventListener('abort', onAbort, { once: true });
  document.addEventListener('visibilitychange', onVisibility, { passive: true });
  function onVisibility() {
    if (document.hidden) { stopPolling(); return; }
    if (state.id && !state.terminal && !timer && pollingEpoch === null) tick();
  }
  function schedule(delay) {
    stopPolling();
    if (signal.aborted || document.hidden || state.terminal) return;
    timer = setTimeout(tick, delay);
  }

  function resetWorkbench() {
    stopPolling();
    requestController.abort();
    requestController = new AbortController();
    epoch += 1;
    pollingEpoch = null;
    Object.assign(state, { id: null, lastRevision: -1, traceRevision: -1, terminal: false, polls: 0, lastStatus: null, lastStages: null, integrationId: null });
    session.setRunId(null);
    resumeInput.value = '';
    submit.disabled = false; retry.hidden = true; cancelButton.disabled = false;
    statusPanel.root.dataset.uiState = 'EMPTY';
    cancelButton.hidden = true;
    for (const key of [...notices.keys()]) { if (key !== 'history:note') { notices.get(key).remove(); notices.delete(key); } }
    for (const p of [statusPanel, stagesPanel, agentsPanel, gatePanel, answerPanel, artifactsPanel, warningsPanel]) { clearBody(p); fillEmpty(p); }
  }

  /* 步骤条（模式 6）：只渲染已发生阶段 + 终态节点；spring 推进、当前阶段脉冲。 */
  function renderStepper(status, stages) {
    const slot = statusPanel.body.querySelector('.wb-steps');
    if (!slot) return;
    slot.replaceChildren();
    const occurred = new Set();
    if (Array.isArray(stages)) for (const s of stages) occurred.add(String(s?.stage));
    if (status?.current_stage) occurred.add(String(status.current_stage));
    const shown = STAGE_ORDER.filter(st => occurred.has(st));
    const terminal = status && TERMINAL.has(status.overall_status) ? String(status.overall_status) : null;
    const nodes = [];
    for (const st of shown) {
      const isCurrent = !terminal && status?.current_stage === st && status?.overall_status === 'RUNNING';
      nodes.push({ label: st, state: isCurrent ? 'current' : 'done' });
    }
    if (terminal) {
      const tone = { SUCCEEDED: 'terminal-ok', SUCCEEDED_WITH_WARNINGS: 'terminal-ok', INCOMPLETE: 'terminal-warn', REVIEW_REQUIRED: 'terminal-review', FAILED: 'terminal-bad', CANCELLED: 'terminal-bad' }[terminal] || 'terminal-warn';
      nodes.push({ label: terminal, state: tone });
    }
    if (!nodes.length) { // 没有任何已发生事件：不虚构进度
      const empty = el('li', undefined, { class: 'wb-step' });
      empty.append(el('div', undefined, { class: 'wb-step-dot' }), el('span', '尚无已发生阶段事件', { class: 'wb-step-label' }));
      slot.append(empty);
      return;
    }
    for (const node of nodes) {
      const li = el('li', undefined, { class: 'wb-step' });
      li.dataset.state = node.state;
      li.append(el('div', undefined, { class: 'wb-step-dot' }), el('span', node.label, { class: 'wb-step-label' }));
      slot.append(li);
    }
  }

  function renderStatus(status) {
    dropNotices('status:');
    state.lastStatus = status;
    statusPanel.root.dataset.uiState = status.overall_status === 'RUNNING'
      ? status.current_stage === 'CREATED' ? 'CREATED' : 'RUNNING'
      : ({ SUCCEEDED: 'COMPLETED', SUCCEEDED_WITH_WARNINGS: 'WARNING', INCOMPLETE: 'WARNING', REVIEW_REQUIRED: 'HUMAN_REVIEW_REQUIRED', FAILED: 'FAILED', CANCELLED: 'CANCELLED' }[status.overall_status] || 'UNKNOWN');
    clearBody(statusPanel);
    mockTag(statusPanel);
    // 状态徽章：原样展示枚举文本，颜色仅辅助（未知枚举中性色）。
    const top = el('div', undefined, { class: 'wb-status-top' });
    const pill = el('span', undefined, { class: 'wb-status-pill' });
    pill.dataset.tone = toneFor(String(status.overall_status));
    pill.textContent = text(status.overall_status);
    top.append(pill);
    if (!OVERALL.has(status.overall_status)) top.append(el('span', '未知枚举·原文', { class: 'badge' }));
    statusPanel.body.append(top);
    statusPanel.body.append(el('div', undefined, { class: 'wb-steps' }));
    renderStepper(status, state.lastStages);
    fields(statusPanel.body, status, ['current_stage', 'investigation_id', 'revision', 'created_at', 'updated_at', 'finished_at', 'error_code']);
    if (!OVERALL.has(status.overall_status)) setNotice(statusPanel.body, 'status:unknown', '未知状态枚举「' + text(status.overall_status) + '」：原文展示，不视为完成。', 'warning');
    if (status.overall_status === 'RUNNING') setNotice(statusPanel.body, 'status:running', '处理中，每秒自动刷新。', 'running');
    if (status.cancel_requested && status.overall_status === 'RUNNING') setNotice(statusPanel.body, 'status:cancel', '已请求取消，等待 CANCELLED 终态。', 'conflict');
    if (status.recovery_required) setNotice(statusPanel.body, 'status:recovery', 'recovery_required：中断后不自动续跑。', 'conflict');
    if (status.overall_status === 'INCOMPLETE') setNotice(statusPanel.body, 'status:incomplete', 'INCOMPLETE：完成但结果不完整，非成功。', 'conflict');
    if (status.overall_status === 'REVIEW_REQUIRED') setNotice(statusPanel.body, 'status:review', 'REVIEW_REQUIRED：需人工复核。', 'conflict');
    if (status.overall_status === 'FAILED') setNotice(statusPanel.body, 'status:failed', 'FAILED：调查失败。', 'error');
    if (status.overall_status === 'CANCELLED') setNotice(statusPanel.body, 'status:cancelled', 'CANCELLED：已取消。', 'conflict');
    if (Array.isArray(status.warnings)) for (const warning of status.warnings) setNotice(statusPanel.body, 'status:warn:' + text(warning), 'warning: ' + text(warning), 'warning');
    cancelButton.hidden = !(status.overall_status === 'RUNNING' && !status.cancel_requested);
    statusPanel.body.append(cancelButton);
  }

  function acceptRevision(status) {
    if (!Number.isInteger(status.revision) || status.revision < 0) throw new InvestigationApiError('状态回执缺少合法 revision。', { kind: 'invalid_response' });
    if (status.revision < state.lastRevision) return false;
    state.lastRevision = status.revision;
    return true;
  }

  function rememberGateReference(reference) {
    if (reference == null) return;
    if (typeof reference !== 'string' || !uuid.test(reference) || (state.integrationId && state.integrationId !== reference)) throw new InvestigationApiError('ROOT_BINDING_MISMATCH：Trace / Answer 的 Gate 引用不一致。', { kind: 'invalid_response', code: 'ROOT_BINDING_MISMATCH' });
    state.integrationId = reference;
  }

  function boundGate(data) {
    // Gate logical_investigation_id belongs to the internal Gate context. The HTTP
    // investigation binds it via integration_result_id in its Trace / Answer.
    bound({ id: null }, data, ['logical_investigation_id']);
    if (!state.integrationId || data.integration_id !== state.integrationId) throw new InvestigationApiError('ROOT_BINDING_MISMATCH：Gate 回执不匹配当前调查的引用。', { kind: 'invalid_response', code: 'ROOT_BINDING_MISMATCH' });
    return data;
  }

  async function tick() {
    if (!state.id || pollingEpoch === epoch || signal.aborted) return;
    const scope = capture();
    pollingEpoch = scope.epoch;
    try {
      const response = await scope.client.status(scope.id, scope.signal);
      if (!current(scope)) return;
      const status = bound(scope, response);
      if (!acceptRevision(status)) { schedule(POLL_MS); return; }
      renderStatus(status);
      await refreshTrace(status, scope);
      if (!current(scope)) return;
      if (status.overall_status === 'RUNNING') {
        state.polls += 1;
        if (state.polls < POLL_LIMIT) schedule(POLL_MS);
        else setNotice(statusPanel.body, 'status:limit', '已达轮询上限；用「读取已有调查」继续。', 'status');
      } else if (TERMINAL.has(status.overall_status)) {
        await finish(scope);
      } else {
        stopPolling();
        setNotice(statusPanel.body, 'status:unknown-paused', '未知状态，自动刷新已暂停；可再次读取，不视为已完成。', 'warning');
      }
    } catch (error) {
      if (current(scope)) handlePollError(error);
    } finally { if (pollingEpoch === scope.epoch) pollingEpoch = null; }
  }

  function handlePollError(error) {
    if (error.name === 'AbortError' || signal.aborted) return;
    const code = codeLine(error);
    if (error.status === 401) { stopPolling(); setNotice(statusPanel.body, 'status:poll', '需要有效 Bearer 凭据。' + code, 'error'); return; }
    if (error.status === 403) { stopPolling(); setNotice(statusPanel.body, 'status:poll', 'ACCESS_DENIED：资产范围不足。' + code, 'error'); return; }
    if (error.status === 404) { stopPolling(); setNotice(statusPanel.body, 'status:poll', '未找到或无权访问。' + code, 'error'); return; }
    if (error.status === 429 || error.status === 503 || (error.status === 409 && error.retryable)) {
      const delay = retryDelayMs(error);
      setNotice(statusPanel.body, 'status:poll', `服务繁忙（${code}）；${Math.round(delay / 1000)} 秒后重试。`, 'conflict');
      schedule(delay);
      return;
    }
    stopPolling();
    setNotice(statusPanel.body, 'status:poll', '读取失败，轮询已暂停；可再次读取。' + code, 'error');
  }

  async function refreshTrace(status, scope) {
    if (status.revision === state.traceRevision) return;
    try {
      const response = await scope.client.trace(scope.id, scope.signal);
      if (!current(scope)) return;
      const trace = bound(scope, response);
      if (typeof trace.revision === 'number' && trace.revision < state.traceRevision) return;
      state.traceRevision = trace.revision;
      rememberGateReference(trace.integration_result_id);
      state.lastStages = trace.stages;
      renderStepper(status, trace.stages);
      renderStages(trace);
      renderAgents(trace);
      renderWarnings(status, trace);
      try {
        const artifacts = await scope.client.artifacts(scope.id, scope.signal);
        if (!current(scope)) return;
        renderArtifacts(bound(scope, artifacts, ['investigation_id']));
      } catch (error) {
        if (current(scope) && error.name !== 'AbortError') setNotice(artifactsPanel.body, 'artifacts:error', codeLine(error), error.code === 'SNAPSHOT_BUSY' ? 'conflict' : 'error');
      }
    } catch (error) {
      if (!current(scope) || error.name === 'AbortError') return;
      if (error.code === 'SNAPSHOT_BUSY') setNotice(stagesPanel.body, 'trace:busy', 'SNAPSHOT_BUSY：根调查正在更新，按 Retry-After 稍后刷新 Trace；不修补或不忽略损坏的绑定。', 'conflict');
      else if (error.status === 404) setNotice(stagesPanel.body, 'trace:missing', 'INVESTIGATION_NOT_FOUND：' + codeLine(error), 'error');
      else setNotice(stagesPanel.body, 'trace:poll', codeLine(error), error.status === 409 ? 'conflict' : 'error');
    }
  }

  async function finish(scope) {
    if (!current(scope)) return;
    stopPolling();
    state.terminal = true;
    cancelButton.hidden = true;
    dropNotices('gate:');
    dropNotices('answer:');
    clearBody(answerPanel); mockTag(answerPanel);
    clearBody(gatePanel); mockTag(gatePanel);
    try {
      const answer = await scope.client.answer(scope.id, scope.signal);
      if (!current(scope)) return;
      bound(scope, answer, ['logical_investigation_id']);
      rememberGateReference(answer.integration_result_id);
      renderAnswer(answer);
    } catch (error) {
      if (!current(scope) || error.name === 'AbortError') return;
      if (error.code === 'RESULT_NOT_READY') setNotice(answerPanel.body, 'answer:pending', '终止但无已保存 Answer（RESULT_NOT_READY）。', 'conflict');
      else setNotice(answerPanel.body, 'answer:error', codeLine(error), 'error');
    }
    try {
      const integration = await scope.client.integration(scope.id, scope.signal);
      if (!current(scope)) return;
      renderGate(boundGate(integration));
    } catch (error) {
      if (!current(scope) || error.name === 'AbortError') return;
      if (error.code === 'RESULT_NOT_READY') setNotice(gatePanel.body, 'gate:pending', 'Gate 未就绪（RESULT_NOT_READY）。', 'conflict');
      else if (error.code === 'RESULT_UNAVAILABLE') setNotice(gatePanel.body, 'gate:unavailable', 'RESULT_UNAVAILABLE：未产生 Gate 结果。', 'conflict');
      else if (error.code === 'MOCK_GATE_NOT_INCLUDED') renderGateMockNote();
      else setNotice(gatePanel.body, 'gate:error', codeLine(error), 'error');
    }
    if (current(scope)) refreshHistory();
  }

  async function requestCancel() {
    if (!state.id) return;
    const scope = capture();
    cancelButton.disabled = true;
    try {
      const response = await scope.client.cancel(scope.id, scope.signal);
      if (!current(scope)) return;
      const status = bound(scope, response);
      if (!acceptRevision(status)) return;
      renderStatus(status);
      setNotice(statusPanel.body, 'status:cancel-sent', status.cancel_requested ? '取消请求已发出，等待终态。' : '未改变调查状态，以后端回执为准。', 'conflict');
      schedule(400);
    } catch (error) {
      if (current(scope) && error.name !== 'AbortError') setNotice(statusPanel.body, 'status:cancel-error', codeLine(error), 'error');
    } finally { if (current(scope)) cancelButton.disabled = false; }
  }

  // ---- 渲染：阶段 / Agent / Gate / 答案 / Artifact / 警告 ------------------
  function renderStages(trace) {
    dropNotices('stages:');
    clearBody(stagesPanel); mockTag(stagesPanel);
    setNotice(stagesPanel.body, 'stages:note', '已发生阶段事件（非百分比进度）。', 'status');
    if (!Array.isArray(trace.stages) || !trace.stages.length) { setNotice(stagesPanel.body, 'stages:empty', '尚无阶段事件。', 'empty'); return; }
    const list = el('ol', undefined, { class: 'timeline' });
    for (const stage of trace.stages) {
      const item = el('li');
      item.append(el('strong', text(stage.stage) + ' · ' + text(stage.status)));
      item.append(el('p', text(stage.time) + ' · ' + text(stage.agent), { class: 'hint' }));
      if (!STAGES.has(stage.stage)) item.append(el('span', '未知阶段枚举：保持原文。', { class: 'badge' }));
      list.append(item);
    }
    stagesPanel.body.append(list);
    const details = el('details');
    details.append(el('summary', '事件时间线（trace.events）'));
    const rows = (trace.events || []).map(event => ({ at: event.at, stage: event.stage, code: event.code, overall_status: event.overall_status }));
    table(details, rows, [
      { label: '时间', render: row => row.at }, { label: '阶段', render: row => row.stage },
      { label: '事件', render: row => row.code }, { label: 'overall', render: row => row.overall_status }
    ]);
    stagesPanel.body.append(details);
  }

  function renderAgents(trace) {
    dropNotices('agents:');
    clearBody(agentsPanel); mockTag(agentsPanel);
    if (trace.planner) {
      agentsPanel.body.append(el('h3', 'Planner'));
      fields(agentsPanel.body, trace.planner, ['planner_run_id', 'validation_status', 'retry_count', 'prompt_version', 'task_ids']);
    } else setNotice(agentsPanel.body, 'agents:planner', 'Planner 尚未启动。', 'empty');
    const runs = Array.isArray(trace.agent_runs) ? trace.agent_runs : [];
    if (!runs.length) { setNotice(agentsPanel.body, 'agents:runs', '尚无 Agent run。', 'empty'); return; }
    for (const run of runs) {
      const block = el('div', undefined, { class: 'run-block' });
      block.append(el('h3', 'run ' + text(run.run_id) + ' · ' + text(run.status)));
      const tasks = Object.entries(run.task_statuses || {}).map(([task, status]) => ({ task, status }));
      table(block, tasks, [{ label: 'Task', render: row => row.task }, { label: '状态', render: row => row.status }]);
      if (Array.isArray(run.tool_calls) && run.tool_calls.length) {
        table(block, run.tool_calls, [
          { label: 'Tool', render: row => row.tool }, { label: 'Task', render: row => row.task_id },
          { label: '状态', render: row => row.status }, { label: '时长 ms', render: row => row.duration_ms },
          { label: 'Evidence 数', render: row => (Array.isArray(row.evidence_ids) ? row.evidence_ids.length : 0) }
        ]);
      } else setNotice(block, 'agents:tools:' + run.run_id, '无工具摘要。', 'empty');
      const refs = (run.artifact_references || []).map(ref => ref.task_id + ' → ' + ref.artifact_id + ' (' + ref.schema_version + ')');
      if (refs.length) { block.append(el('h4', 'Artifact 引用')); for (const line of refs) block.append(el('p', line)); }
      agentsPanel.body.append(block);
    }
  }

  function renderGate(data, { independent = false } = {}) {
    const prefix = independent ? 'gate-i:' : 'gate:';
    const host = independent ? gatePanel.body.querySelector('.gate-independent') : gatePanel.body;
    if (!host) return;
    dropNotices(prefix);
    if (independent) {
      host.replaceChildren();
      host.append(el('h4', '独立 Gate 示例（不并入场景）'), el('p', 'join_with_five_demo_files=false · ' + text(data.rawNotice), { class: 'hint' }));
    }
    fields(host, data, ['status', 'integration_id', 'trace_id', 'run_id', 'created_at', 'evaluation_time', 'persistence', 'historical_snapshot']);
    if (!GATE.has(data.status)) setNotice(host, prefix + 'unknown', '未知 Gate 状态：保持原文，不归入成功。', 'warning');
    if (data.status === 'PASS_WITH_WARNINGS') setNotice(host, prefix + 'warnings', 'PASS_WITH_WARNINGS：带警告通过。', 'warning');
    if (data.status === 'REPLAN_REQUIRED') setNotice(host, prefix + 'replan', 'REPLAN_REQUIRED：需重新调查，非成功。', 'conflict');
    if (data.status === 'HUMAN_REVIEW_REQUIRED') setNotice(host, prefix + 'human', 'HUMAN_REVIEW_REQUIRED：需人工复核，非成功。', 'conflict');
    if (data.status === 'FAILED') setNotice(host, prefix + 'failed', 'FAILED：未通过。', 'error');
    if (Array.isArray(data.objective_coverage) && data.objective_coverage.length) {
      host.append(el('h4', 'Objective coverage'));
      table(host, data.objective_coverage, [
        { label: '目标', render: row => row.outcome }, { label: '结果', render: row => row.status },
        { label: '引用数', render: row => (Array.isArray(row.references) ? row.references.length : 0) }
      ]);
    }
    if (Array.isArray(data.checks) && data.checks.length) {
      host.append(el('h4', 'Checks（原样保留）'));
      table(host, data.checks, [
        { label: 'Gate', render: row => row.gate }, { label: 'Code', render: row => row.code },
        { label: '结果', render: row => row.outcome }, { label: 'Blocking', render: row => row.blocking },
        { label: '说明', render: row => row.message }
      ]);
    }
    for (const [label, values] of [['Blocking issues', data.blocking_issues], ['Replan reasons', data.replan_reasons], ['Human review reasons', data.human_review_reasons], ['Warnings', data.warnings], ['未解决事项', data.unresolved_items]]) {
      if (Array.isArray(values) && values.length) {
        host.append(el('h4', label));
        for (const value of values) host.append(el('p', text(value)));
      }
    }
  }

  function renderGateMockNote() {
    const note = el('div', undefined, { class: 'gate-mock-note' });
    note.append(el('p', 'Mock 未提供完整 Gate 回执（checks / objective_coverage 不可得）。', { class: 'message', 'data-state': 'warning' }));
    const button = el('button', '加载独立 Gate 示例', { type: 'button', class: 'wb-btn' });
    const slot = el('div', undefined, { class: 'gate-independent' });
    button.addEventListener('click', async () => {
      const scope = capture();
      button.disabled = true;
      try {
        const sample = await loadIndependentGate();
        if (!current(scope)) return;
        renderGate({ ...sample.result, rawNotice: sample.notice }, { independent: true });
      } catch (error) { if (current(scope)) slot.replaceChildren(el('p', codeLine(error))); }
    });
    note.append(button, slot);
    gatePanel.body.append(note);
  }

  function renderAnswer(answer) {
    dropNotices('answer:');
    clearBody(answerPanel); mockTag(answerPanel);
    fields(answerPanel.body, answer, ['answer_status', 'integration_status', 'answer_id', 'generated_at', 'historical_snapshot', 'fact_origin', 'explanation_provider']);
    if (answer.answer_status === 'INCOMPLETE') setNotice(answerPanel.body, 'answer:incomplete', 'INCOMPLETE：不完整，非已确认结论。', 'conflict');
    if (answer.answer_status === 'REVIEW_REQUIRED') setNotice(answerPanel.body, 'answer:review', 'REVIEW_REQUIRED：需人工复核。', 'conflict');
    if (answer.answer_status === 'CANCELLED') setNotice(answerPanel.body, 'answer:cancelled', 'CANCELLED：无完整结论。', 'conflict');
    if (answer.answer_status === 'FAILED') setNotice(answerPanel.body, 'answer:failed', 'FAILED。', 'error');
    if (answer.answer_status === 'COMPLETE_WITH_WARNINGS') setNotice(answerPanel.body, 'answer:warnings', 'COMPLETE_WITH_WARNINGS：带警告。', 'warning');
    if (answer.integration_status && !GATE.has(answer.integration_status)) setNotice(answerPanel.body, 'answer:gate-unknown', '未知 integration_status：保持原文。', 'warning');
    if (answer.summary) answerPanel.body.append(clampText(text(answer.summary))); // 模式 5：长文本展开
    if (Array.isArray(answer.key_findings) && answer.key_findings.length) {
      answerPanel.body.append(el('h4', 'Key findings'));
      for (const finding of answer.key_findings) {
        const item = el('p', undefined, { class: 'mono' });
        item.append(clampText(text(finding), { lines: 2 }));
        answerPanel.body.append(item);
      }
    }
    if (Array.isArray(answer.affected_assets) && answer.affected_assets.length) {
      answerPanel.body.append(el('h4', '受影响资产'));
      table(answerPanel.body, answer.affected_assets, [
        { label: 'Asset', render: row => row.asset_id }, { label: 'Component', render: row => row.component_id },
        { label: '部署版本', render: row => row.deployed_version }, { label: 'Provenance', render: row => row.provenance }
      ]);
    }
    const risk = answer.risk_assessment;
    if (risk) {
      answerPanel.body.append(el('h4', '风险视图'));
      fields(answerPanel.body, risk, ['risk_level', 'priority', 'affected', 'verification_status', 'asset_match_status', 'version_match_status', 'exploitation_status', 'patch_status', 'patch_applied', 'conclusion_scope']);
      if (risk.affected === null || risk.affected === undefined) setNotice(answerPanel.body, 'answer:risk-null', 'affected=null 为未知，不等于不受影响。', 'warning');
    }
    if (Array.isArray(answer.recommended_actions) && answer.recommended_actions.length) {
      answerPanel.body.append(el('h4', '建议处置'));
      table(answerPanel.body, answer.recommended_actions, [
        { label: '类型', render: row => row.action_type }, { label: '说明', render: row => row.summary },
        { label: '类别', render: row => row.category }, { label: '适用性', render: row => row.applicability },
        { label: '修复版本', render: row => row.fixed_version }, { label: '来源', render: row => row.action_provenance }
      ]);
    }
    if (Array.isArray(answer.verified_claims) && answer.verified_claims.length) {
      answerPanel.body.append(el('h4', '已核验 Claim'));
      table(answerPanel.body, answer.verified_claims, [
        { label: 'Claim', render: row => row.claim_id }, { label: '类型', render: row => row.claim_type },
        { label: '结论值', render: row => text(row.value) }, { label: '状态', render: row => row.verification_status },
        { label: 'Evidence 数', render: row => (Array.isArray(row.evidence_ids) ? row.evidence_ids.length : 0) }
      ]);
    }
    if (Array.isArray(answer.disputed_claims) && answer.disputed_claims.length) {
      answerPanel.body.append(el('h4', '争议 Claim'));
      table(answerPanel.body, answer.disputed_claims, [
        { label: 'Claim', render: row => row.claim_id }, { label: '类型', render: row => row.claim_type },
        { label: '状态', render: row => row.verification_status }, { label: '作用范围', render: row => row.scope_key },
        { label: '结论值', render: row => text(row.value) }
      ]);
    }
    if (Array.isArray(answer.citations) && answer.citations.length) {
      answerPanel.body.append(el('h4', '引用'));
      table(answerPanel.body, answer.citations, [
        { label: 'Evidence', render: row => row.evidence_id }, { label: 'Claim', render: row => row.claim_id },
        { label: '来源', render: row => row.source_id }, { label: '定位', render: row => text(row.reference?.url) + ' · ' + text(row.reference?.locator) },
        { label: 'Hash', render: row => String(row.hash || '').slice(0, 12) }
      ]);
    }
    if (Array.isArray(answer.evidence_observations) && answer.evidence_observations.length) {
      answerPanel.body.append(el('h4', 'Evidence 观察'));
      table(answerPanel.body, answer.evidence_observations, [
        { label: 'Evidence', render: row => row.evidence_id }, { label: 'Claim', render: row => row.claim_id },
        { label: '立场', render: row => row.stance }, { label: '直接性', render: row => row.directness },
        { label: '完整性', render: row => row.integrity_status }, { label: '当前有效', render: row => row.is_current }
      ]);
    }
    if (Array.isArray(answer.evidence_references) && answer.evidence_references.length) {
      answerPanel.body.append(el('h4', 'Evidence references'));
      for (const ref of answer.evidence_references) answerPanel.body.append(el('p', text(ref), { class: 'mono' }));
    }
    if (Array.isArray(answer.warnings) && answer.warnings.length) {
      answerPanel.body.append(el('h4', 'Warnings'));
      for (const warning of answer.warnings) answerPanel.body.append(el('p', text(warning)));
    }
    if (Array.isArray(answer.unresolved_items) && answer.unresolved_items.length) {
      answerPanel.body.append(el('h4', '未解决事项'));
      for (const item of answer.unresolved_items) answerPanel.body.append(el('p', text(item)));
    }
  }

  function renderArtifacts(data) {
    dropNotices('artifacts:');
    clearBody(artifactsPanel); mockTag(artifactsPanel);
    if (mode === 'mock') setNotice(artifactsPanel.body, 'artifacts:mock', data?.mock_missing || '该 Mock 场景未提供 Artifact 回执。', 'warning');
    const slots = [['investigation', 'InvestigationArtifact', 'status'], ['verification', 'VerificationArtifact', 'verification_status'], ['analysis', 'RiskAnalysisArtifact', 'risk_level']];
    for (const [key, label, statusKey] of slots) {
      const artifact = data?.[key];
      if (!artifact) { setNotice(artifactsPanel.body, 'artifacts:' + key, label + '：尚未产生。', 'empty'); continue; }
      const block = el('div', undefined, { class: 'run-block' });
      block.append(el('h3', label + ' · ' + text(artifact[statusKey])));
      fields(block, artifact, ['artifact_id', 'run_id', 'task_id', 'schema_version', statusKey, 'runtime_status', 'information_status', 'confidence', 'partial_result', 'execution_status', 'coverage_complete'].filter(key2 => artifact[key2] !== undefined));
      for (const [title, values] of [['uncertainties', artifact.uncertainties], ['warnings', artifact.warnings], ['unresolved_items', artifact.unresolved_items], ['conflicts', artifact.conflicts]]) {
        if (Array.isArray(values) && values.length) { block.append(el('h4', title)); for (const value of values) block.append(el('p', text(value))); }
      }
      const raw = el('details'); raw.append(el('summary', '原始 JSON')); raw.append(el('pre', undefined, { class: 'mono' })); raw.querySelector('pre').textContent = JSON.stringify(artifact, null, 2);
      block.append(raw);
      artifactsPanel.body.append(block);
    }
  }

  function renderWarnings(status, trace) {
    dropNotices('warnings:');
    clearBody(warningsPanel); mockTag(warningsPanel);
    const values = [
      ...(Array.isArray(status.warnings) ? status.warnings.map(item => ['status', item]) : []),
      ...(Array.isArray(trace?.warnings) ? trace.warnings.map(item => ['trace', item]) : []),
      ...(Array.isArray(trace?.unresolved_items) ? trace.unresolved_items.map(item => ['unresolved', item]) : [])
    ];
    if (!values.length) { setNotice(warningsPanel.body, 'warnings:empty', '无警告记录。', 'empty'); return; }
    table(warningsPanel.body, values, [{ label: '来源', render: row => row[0] }, { label: '内容', render: row => text(row[1]) }]);
  }

  async function refreshHistory() {
    const scope = capture();
    const sequence = ++historySequence;
    try {
      const data = await scope.client.history({ limit: 10, sort: 'created_desc' }, scope.signal);
      if (!current(scope) || sequence !== historySequence) return;
      clearBody(historyPanel); mockTag(historyPanel);
      setNotice(historyPanel.body, 'history:note', '只读记录；读取进入该调查。' + (mode === 'mock' ? '（Mock：跳到场景终态）' : ''), 'status');
      historyPanel.body.append(historyView.root);
      historyView.setItems(data.items || []);
    } catch (error) {
      if (!current(scope) || sequence !== historySequence || error.name === 'AbortError') return;
      clearBody(historyPanel);
      setNotice(historyPanel.body, 'history:error', codeLine(error) + (error.status === 401 ? '：需要有效 Bearer 凭据。' : ''), error.status === 401 ? 'error' : 'conflict');
    }
  }

  async function openExisting(row) {
    let scope = capture();
    try {
      if (mode === 'mock') {
        mock = createMockInvestigationClient({ scenario });
        resetWorkbench();
        scope = capture();
        await scope.client.openScenario(row.investigation_id);
        if (!current(scope)) return;
        const info = await scope.client.info();
        if (!current(scope)) return;
        scenario = info.scenario; syncSeg();
      }
      resumeInput.value = row.investigation_id;
      watch(row.investigation_id);
      scope = capture();
      await refreshBanner();
    } catch (error) {
      if (current(scope)) setNotice(historyPanel.body, 'history:open', codeLine(error), 'error');
    }
  }

  function watch(id) {
    resetWorkbench();
    lastSubmission = null;
    state.id = id;
    session.setRunId(id);
    resumeInput.value = id;
    setNotice(requestState, 'watch', '正在读取 ' + id.slice(0, 8) + '…（只轮询，不重复提交）', 'status');
    tick();
  }

  async function submitInvestigation(request, key) {
    resetWorkbench();
    const scope = capture();
    submit.disabled = true; retry.hidden = true;
    statusPanel.root.dataset.uiState = 'LOADING';
    setNotice(requestState, 'request', 'Loading / 正在创建调查（POST /api/investigations）…', 'loading');
    try {
      const data = await scope.client.create(request, key, scope.signal);
      if (!current(scope)) return;
      bound(scope, data, []);
      dropNotices('request');
      if (data.status === 'NEED_CONTEXT') {
        if (!Array.isArray(data.missing_fields) || !data.missing_fields.length || data.investigation_created === true) throw new InvestigationApiError('NEED_CONTEXT 回执格式错误。', { kind: 'invalid_response' });
        statusPanel.root.dataset.uiState = 'NEED_CONTEXT';
        clearBody(statusPanel);
        statusPanel.body.append(el('h3', 'NEED_CONTEXT · 需要补充信息'));
        setNotice(requestState, 'request', data.message || '请补充调查上下文；调查尚未启动。', 'warning');
        const labels = { version: '目标组件版本', asset_context: '目标资产信息', component: '目标组件名称', vulnerability_id: '目标漏洞编号' };
        for (const field of data.missing_fields) message(statusPanel.body, '请提供' + (labels[field] || text(field)) + '后继续分析。', 'warning');
        fields(statusPanel.body, data, ['investigation_created', 'execution_mode']);
        if (Array.isArray(data.next_actions)) fields(statusPanel.body, data, ['next_actions']);
        setNotice(statusPanel.body, 'status:context', '未创建调查，不进行轮询；补充后重新提交。', 'status');
        return;
      }
      bound(scope, data);
      if (typeof data.investigation_id !== 'string' || !uuid.test(data.investigation_id)) throw new InvestigationApiError('创建回执缺少有效 investigation_id；不进行轮询。', { kind: 'invalid_response' });
      const lines = [data.reused ? '幂等键命中，复用已有调查（reused=true）。' : '已受理（202），自动轮询中…'];
      if (data.is_mock) lines.push('后端模型为 Mock（is_mock=true）。');
      setNotice(requestState, 'request', lines.join(' '), 'status');
      state.id = data.investigation_id;
      scope.id = state.id;
      session.setRunId(state.id); resumeInput.value = state.id;
      acceptRevision(data);
      renderStatus(data);
      await tick();
      if (current(scope)) refreshHistory();
    } catch (error) {
      if (!current(scope) || error.name === 'AbortError') return;
      statusPanel.root.dataset.uiState = 'ERROR';
      dropNotices('request');
      setNotice(requestState, 'request', codeLine(error), 'error');
      if (error.code === 'IDEMPOTENCY_CONFLICT') setNotice(requestState, 'request:hint', '同一幂等键内容不同；仅新问题才换新键。', 'conflict');
      else if (error.status === 429 || error.status === 503) setNotice(requestState, 'request:hint', '可稍后用同一幂等键重试。', 'conflict');
      else if (error.kind === 'network' && mode === 'real') setNotice(requestState, 'request:hint', '后端不可达；可切换「Mock 演示」查看交互。', 'conflict');
      retry.hidden = !(error.kind === 'network' || error.status === 429 || error.status === 503);
      submit.disabled = false;
    } finally { if (current(scope)) submit.disabled = false; }
  }

  let lastSubmission = null;
  form.addEventListener('submit', event => {
    event.preventDefault();
    dropNotices('request');
    const trimmed = question.value.trim();
    if (!trimmed) { setNotice(requestState, 'request', '请输入问题。', 'error'); return; }
    if (trimmed.length > 2000) { setNotice(requestState, 'request', '问题必须包含 1–2000 个字符。', 'error'); return; }
    if (assetId.value.trim() && !uuid.test(assetId.value.trim())) { setNotice(requestState, 'request', '资产 UUID 格式不合法。', 'error'); return; }
    const request = { user_query: trimmed, options: { mode: runMode.value, realtime: realtime.checked } };
    const scope = {};
    if (target.value.trim()) scope.target = target.value.trim();
    if (assetId.value.trim()) scope.asset_id = assetId.value.trim();
    if (componentName.value.trim()) {
      scope.component = { name: componentName.value.trim() };
      if (componentEcosystem.value.trim()) scope.component.ecosystem = componentEcosystem.value.trim();
      if (componentVersion.value.trim()) scope.component.version = componentVersion.value.trim();
    }
    if (Object.keys(scope).length) request.asset_scope = scope;
    const key = 'frontend-' + crypto.randomUUID();
    lastSubmission = { request, key };
    submitInvestigation(request, key);
  });
  retry.addEventListener('click', event => {
    event.preventDefault();
    if (lastSubmission) submitInvestigation(lastSubmission.request, lastSubmission.key);
  });
  resumeForm.addEventListener('submit', event => {
    event.preventDefault();
    const value = resumeInput.value.trim();
    if (!uuid.test(value)) { setNotice(requestState, 'request', 'Investigation ID 必须为 UUID。', 'error'); return; }
    watch(value);
  });

  // ---- 模式 / 场景切换 -----------------------------------------------------
  async function switchMode(next) {
    if (next === mode) return;
    mode = next;
    if (mode === 'mock') mock = createMockInvestigationClient({ scenario });
    syncSeg();
    unmockTags();
    resetWorkbench();
    lastSubmission = null;
    const scope = capture();
    dropNotices('request');
    setNotice(requestState, 'request', mode === 'mock' ? 'Mock 演示：回放合成回执，不访问后端。' : '真实 API：请求 /api/investigations。', 'status');
    if (mode === 'mock') {
      try { await prefillScenarioQuestion(scope); if (current(scope)) rippleTo(questionWrap); }
      catch (error) { if (current(scope)) setNotice(requestState, 'request', codeLine(error), 'error'); }
    }
    if (!current(scope)) return;
    await refreshBanner(scope);
    if (current(scope)) refreshHistory();
  }
  segReal.addEventListener('click', () => switchMode('real'));
  segMock.addEventListener('click', () => switchMode('mock'));
  scenarioSelect.addEventListener('change', async () => {
    if (mode !== 'mock') return;
    scenario = scenarioSelect.value;
    mock = createMockInvestigationClient({ scenario });
    resetWorkbench();
    lastSubmission = null;
    const scope = capture();
    dropNotices('request');
    try {
      await prefillScenarioQuestion(scope);
      if (!current(scope)) return;
      setNotice(requestState, 'request', 'Mock 场景 ' + scenario + '，提交后回放该场景。', 'status');
      rippleTo(questionWrap); // 模式 7：切换场景 → 预填问题框 ripple 提示联动
      await refreshBanner(scope);
    } catch (error) { if (current(scope)) setNotice(requestState, 'request', codeLine(error), 'error'); }
  });

  // ---- 初始化 ---------------------------------------------------------------
  syncSeg();
  const existing = session.getRunId();
  if (existing) resumeInput.value = existing;
  for (const p of [statusPanel, stagesPanel, agentsPanel, gatePanel, answerPanel, artifactsPanel, warningsPanel]) fillEmpty(p);
  if (mode === 'mock') {
    const scope = capture();
    prefillScenarioQuestion(scope).catch(error => { if (current(scope)) setNotice(requestState, 'request', codeLine(error), 'error'); });
  }
  refreshBanner();
  refreshHistory();
  if (demoParam) setNotice(requestState, 'request', 'Mock 演示模式（?demo=' + demoParam + '）。', 'status');
}
