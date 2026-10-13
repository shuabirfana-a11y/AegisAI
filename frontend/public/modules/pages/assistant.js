/**
 * 智能调查工作台（/assistant）。
 * 真实模式使用 Phase 12-B 的 8 个 /api/investigations 接口；Mock 模式回放交接包的
 * 10 个历史合成测试回执（全程显示 MOCK_ONLY 标签，不冒充真实执行）。
 * 状态纪律：202 受理 ≠ 完成；COMPLETED+INCOMPLETE 是合法结果；Gate 原样展示；
 * 取消请求 ≠ 已取消；未知枚举保持原文中性展示；缺失 Artifact 不创建假节点。
 */
import { pageTitle, el, section, fields, table, message, jsonBlock, text } from '../components.js';
import { createInvestigationClient, retryDelayMs } from '../investigation-client.js';
import { createMockInvestigationClient, loadIndependentGate, MOCK_SCENARIOS } from '../investigation-mock.js';

const OVERALL = new Set(['RUNNING', 'SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS', 'INCOMPLETE', 'REVIEW_REQUIRED', 'FAILED', 'CANCELLED']);
const STAGES = new Set(['CREATED', 'PLANNING', 'INVESTIGATING', 'VERIFYING', 'ANALYZING', 'INTEGRATING', 'COMPOSING', 'COMPLETED', 'WAITING_REVIEW', 'FAILED', 'CANCELLED']);
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

/** 清空区块内容，只保留标题（不删除区块本身与消息锚点）。 */
function clearBox(box, title) {
  box.replaceChildren(el('h2', title));
}

export function assistant(view, { session, signal, localDemoAccess } = {}) {
  pageTitle(view, '智能调查', '提交问题 → 创建调查（HTTP 202 受理 ≠ 完成）→ 每 1 秒轮询 status → 阶段 / Agent / Tool → Gate → Answer 与引用；支持取消与历史。');

  // 先解析 ?demo=，Mock 客户端从一开始就锁定该场景，避免初始横幅/回放错用 PASS 数据。
  const demoParam = new URLSearchParams(location.search).get('demo');
  let mode = demoParam && MOCK_SCENARIOS.includes(demoParam) ? 'mock' : 'real';
  let scenario = mode === 'mock' ? demoParam : 'PASS';
  const real = createInvestigationClient({ getToken: session.getToken, localDemoAccess });
  const mock = createMockInvestigationClient({ scenario });
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

  // ---- 数据模式 ----------------------------------------------------------
  const client = () => (mode === 'mock' ? mock : real);

  const controls = el('div', undefined, { class: 'workbench-controls' });
  const modeSelect = el('select', undefined, { 'aria-label': '数据模式' });
  modeSelect.append(el('option', '真实 API（/api/investigations）', { value: 'real' }), el('option', 'Mock 演示 · 合成测试回执', { value: 'mock' }));
  modeSelect.value = mode;
  const scenarioSelect = el('select', undefined, { 'aria-label': 'Mock 场景' });
  for (const name of MOCK_SCENARIOS) scenarioSelect.append(el('option', name, { value: name }));
  scenarioSelect.value = scenario;
  const scenarioLabel = el('label', 'Mock 场景'); scenarioLabel.append(scenarioSelect);
  controls.append(modeSelect, scenarioLabel);
  const mockBanner = el('p', undefined, { class: 'mock-banner', role: 'status' });
  view.append(controls, mockBanner);

  function mockTag(parent) {
    if (mode === 'mock') parent.append(el('span', 'MOCK_ONLY', { class: 'badge' }));
  }
  async function refreshBanner() {
    if (mode !== 'mock') { mockBanner.hidden = true; mockBanner.textContent = ''; return; }
    mockBanner.hidden = false;
    try {
      const info = await mock.info();
      mockBanner.textContent = `Mock 演示 · 场景 ${info.scenario} · api_status=${text(info.api_status)} · fixture_label=${text(info.fixture_label)} · `
        + '历史合成测试回执，回放固定数据且与输入内容无关；不是真实安全情报、不是在线请求。';
    } catch (error) { mockBanner.textContent = 'Mock 数据加载失败：' + codeLine(error); }
  }
  /** 用当前 Mock 场景的固定问题预填表单（回放内容与输入无关，仅为演示方便）。 */
  async function prefillScenarioQuestion() {
    const info = await mock.info();
    if (info.question) question.value = info.question;
  }

  // ---- 提交表单 ----------------------------------------------------------
  const form = el('form', undefined, { class: 'assistant-form' });
  const question = el('textarea', undefined, { id: 'inv-question', required: '', maxlength: '2000', placeholder: '例如：我的 vLLM 0.6.0 部署是否受到某 CVE 影响，如何修复？（Mock 回放与输入无关）' });
  const questionLabel = el('label', '问题（1–2000 字）'); questionLabel.append(question); form.append(questionLabel);
  const fieldRow = el('div', undefined, { class: 'field-row' });
  const target = el('input', undefined, { type: 'text', maxlength: '150', placeholder: '例如 CVE-2099-XXXX', 'aria-label': '目标' });
  const assetId = el('input', undefined, { type: 'text', maxlength: '36', placeholder: '资产 UUID（可选）', 'aria-label': '资产 UUID' });
  const componentName = el('input', undefined, { type: 'text', maxlength: '100', placeholder: '组件名，如 vllm', 'aria-label': '组件名' });
  const componentEcosystem = el('input', undefined, { type: 'text', maxlength: '50', placeholder: '生态，如 PyPI', 'aria-label': '组件生态' });
  const componentVersion = el('input', undefined, { type: 'text', maxlength: '50', placeholder: '版本，如 0.6.0', 'aria-label': '组件版本' });
  for (const [node, label] of [[target, 'Target（可选）'], [assetId, '资产 UUID（可选）'], [componentName, '组件名（可选）'], [componentEcosystem, '生态（可选）'], [componentVersion, '版本（可选）']]) {
    const wrap = el('label', label); wrap.append(node); fieldRow.append(wrap);
  }
  form.append(fieldRow);
  const optionRow = el('div', undefined, { class: 'field-row' });
  const runMode = el('select', undefined, { 'aria-label': '运行模式' });
  for (const value of ['auto', 'fast', 'deep']) runMode.append(el('option', value, { value }));
  const runModeLabel = el('label', 'Mode'); runModeLabel.append(runMode); optionRow.append(runModeLabel);
  const realtime = el('input', undefined, { type: 'checkbox' });
  const realtimeLabel = el('label', 'realtime（需要实时信息）'); realtimeLabel.prepend(realtime); optionRow.append(realtimeLabel);
  form.append(optionRow);
  const submit = el('button', '提交调查', { type: 'submit' });
  const retry = el('button', '用同一幂等键重试', { type: 'button', hidden: '' });
  form.append(submit, retry);
  view.append(form);
  const requestState = el('div', undefined, { 'aria-live': 'polite' }); view.append(requestState);

  const resumeForm = el('form');
  const resumeInput = el('input', undefined, { type: 'text', maxlength: '36', placeholder: '已有 Investigation UUID', 'aria-label': '已有调查 ID' });
  resumeForm.append(resumeInput, el('button', '读取已有调查', { type: 'submit' }), el('span', '（不重复提交，只轮询 status）', { class: 'hint' }));
  view.append(resumeForm);

  // ---- 区块 --------------------------------------------------------------
  const statusBox = section('调查状态（status）', view);
  const stagesBox = section('阶段进度（trace.stages · 已发生事件）', view);
  const agentsBox = section('Agent 执行（planner / agent_runs / tool_calls）', view);
  const gateBox = section('Integration Gate（integration）', view);
  const answerBox = section('可信答案（answer · AnswerEnvelope）', view);
  const artifactsBox = section('专业 Artifact（artifacts）', view);
  const warningsBox = section('警告与未解决事项', view);
  const historyBox = section('历史调查（history）', view);
  const boxes = [statusBox, stagesBox, agentsBox, gateBox, answerBox, artifactsBox, warningsBox, historyBox];

  const cancelButton = el('button', '请求取消', { type: 'button', hidden: '' });
  cancelButton.addEventListener('click', requestCancel);

  // ---- 轮询状态 ----------------------------------------------------------
  const state = { id: null, lastRevision: -1, traceRevision: -1, terminal: false, polls: 0 };
  let polling = false;
  let timer;
  function stopPolling() { clearTimeout(timer); timer = undefined; }
  function onAbort() { stopPolling(); document.removeEventListener('visibilitychange', onVisibility); }
  signal.addEventListener('abort', onAbort, { once: true });
  document.addEventListener('visibilitychange', onVisibility, { passive: true });
  function onVisibility() {
    if (document.hidden) { stopPolling(); return; }
    if (state.id && !state.terminal && !timer && !polling) tick();
  }
  function schedule(delay) {
    stopPolling();
    if (signal.aborted || document.hidden || state.terminal) return;
    timer = setTimeout(tick, delay);
  }

  function resetWorkbench() {
    stopPolling();
    Object.assign(state, { id: null, lastRevision: -1, traceRevision: -1, terminal: false, polls: 0 });
    cancelButton.hidden = true;
    for (const key of [...notices.keys()]) { notices.get(key).remove(); notices.delete(key); }
    for (const box of boxes) {
      const title = box.querySelector('h2')?.textContent || '';
      box.replaceChildren(el('h2', title));
      message(box, 'Empty / 尚未读取。', 'empty');
    }
  }

  function renderStatus(status) {
    dropNotices('status:');
    if (state.id !== status.investigation_id) {
      state.id = status.investigation_id;
      session.setRunId(state.id);
      resumeInput.value = state.id;
    }
    clearBox(statusBox, '调查状态（status）');
    if (mode === 'mock') {
      const head = el('div', undefined, { class: 'section-head' });
      head.append(el('span', 'status')); mockTag(head);
      statusBox.append(head);
    }
    fields(statusBox, status, ['overall_status', 'current_stage', 'investigation_id', 'revision', 'created_at', 'updated_at', 'finished_at', 'cancel_requested', 'recovery_required', 'error_code']);
    if (!OVERALL.has(status.overall_status)) setNotice(statusBox, 'status:unknown', '未知 overall_status「' + text(status.overall_status) + '」：保持原文中性展示，不视为完成。', 'warning');
    if (status.overall_status === 'RUNNING') setNotice(statusBox, 'status:running', 'RUNNING / 处理中：每 1 秒读取 status，页面隐藏时暂停；HTTP 202 受理不代表调查完成。', 'running');
    if (status.cancel_requested && status.overall_status === 'RUNNING') setNotice(statusBox, 'status:cancel', 'cancel_requested=true：已发出取消请求，等待 overall_status=CANCELLED 终态；取消成功请求不等于已经停止。', 'conflict');
    if (status.recovery_required) setNotice(statusBox, 'status:recovery', 'recovery_required=true：进程重启后该调查未完成，不会自动续跑；请手动刷新或联系负责人。', 'conflict');
    if (status.overall_status === 'INCOMPLETE') setNotice(statusBox, 'status:incomplete', 'INCOMPLETE：调查已完成但结果不完整；这是合法结果，不能渲染成成功。', 'conflict');
    if (status.overall_status === 'REVIEW_REQUIRED') setNotice(statusBox, 'status:review', 'REVIEW_REQUIRED：需要人工复核，未形成可直接采用的结论。', 'conflict');
    if (status.overall_status === 'FAILED') setNotice(statusBox, 'status:failed', 'FAILED：调查失败；保留已有警告、Trace 与错误码。', 'error');
    if (status.overall_status === 'CANCELLED') setNotice(statusBox, 'status:cancelled', 'CANCELLED：调查已取消，不产生完整结论（已完成调查不会被逆转）。', 'conflict');
    if (Array.isArray(status.warnings)) for (const warning of status.warnings) setNotice(statusBox, 'status:warn:' + text(warning), 'warning: ' + text(warning), 'warning');
    cancelButton.hidden = !(status.overall_status === 'RUNNING' && !status.cancel_requested);
    statusBox.append(cancelButton, el('span', ' 高负载时按 Retry-After 退避；revision 用于丢弃乱序旧响应。', { class: 'hint' }));
  }

  async function tick() {
    if (!state.id || polling || signal.aborted) return;
    polling = true;
    try {
      const status = await client().status(state.id, signal);
      if (signal.aborted) return;
      if (typeof status.revision === 'number' && status.revision < state.lastRevision) { schedule(POLL_MS); return; }
      state.lastRevision = status.revision;
      renderStatus(status);
      await refreshTrace(status);
      if (status.overall_status === 'RUNNING') {
        state.polls += 1;
        if (state.polls < POLL_LIMIT) schedule(POLL_MS);
        else setNotice(statusBox, 'status:limit', '已达到本次页面轮询上限；使用“读取已有调查”或切换页面后继续。', 'status');
      } else {
        await finish();
      }
    } catch (error) {
      handlePollError(error);
    } finally { polling = false; }
  }

  function handlePollError(error) {
    if (error.name === 'AbortError' || signal.aborted) return;
    const code = codeLine(error);
    if (error.status === 401) { stopPolling(); setNotice(statusBox, 'status:poll', 'AUTHENTICATION_REQUIRED：需要有效 Bearer 凭据。' + code, 'error'); return; }
    if (error.status === 403) { stopPolling(); setNotice(statusBox, 'status:poll', 'ACCESS_DENIED：请调整已授权资产范围。' + code, 'error'); return; }
    if (error.status === 404) { stopPolling(); setNotice(statusBox, 'status:poll', 'INVESTIGATION_NOT_FOUND：未找到或无权访问；不泄露其他用户存在性。' + code, 'error'); return; }
    if (error.status === 429 || error.status === 503 || (error.status === 409 && error.retryable)) {
      const delay = retryDelayMs(error);
      setNotice(statusBox, 'status:poll', `服务繁忙或结果未就绪（${code}）；${Math.round(delay / 1000)} 秒后重试。`, 'conflict');
      schedule(delay);
      return;
    }
    stopPolling();
    setNotice(statusBox, 'status:poll', '读取失败，自动轮询已暂停；保留上次快照，可再次“读取已有调查”。' + code, 'error');
  }

  async function refreshTrace(status) {
    if (status.revision === state.traceRevision) return;
    try {
      const trace = await client().trace(state.id, signal);
      if (signal.aborted || typeof trace.revision === 'number' && trace.revision < state.traceRevision) return;
      state.traceRevision = trace.revision;
      renderStages(trace);
      renderAgents(trace);
      renderWarnings(status, trace);
      try {
        renderArtifacts(await client().artifacts(state.id, signal));
      } catch (error) {
        if (!signal.aborted) setNotice(artifactsBox, 'artifacts:error', codeLine(error), error.code === 'SNAPSHOT_BUSY' ? 'conflict' : 'error');
      }
    } catch (error) {
      if (signal.aborted || error.name === 'AbortError') return;
      if (error.code === 'SNAPSHOT_BUSY') setNotice(stagesBox, 'trace:busy', 'SNAPSHOT_BUSY：根调查正在更新，按 Retry-After 稍后刷新 Trace；不修补或不忽略损坏的绑定。', 'conflict');
      else if (error.status === 404) setNotice(stagesBox, 'trace:missing', 'INVESTIGATION_NOT_FOUND：' + codeLine(error), 'error');
      else setNotice(stagesBox, 'trace:poll', codeLine(error), error.status === 409 ? 'conflict' : 'error');
    }
  }

  async function finish() {
    stopPolling();
    state.terminal = true;
    cancelButton.hidden = true;
    dropNotices('gate:');
    dropNotices('answer:');
    // 先清理到“可写状态”，失败分支的提示不会叠在旧内容或 Empty 占位之上。
    clearBox(answerBox, '可信答案（answer · AnswerEnvelope）');
    mockTag(answerBox);
    clearBox(gateBox, 'Integration Gate（integration）');
    mockTag(gateBox);
    try {
      renderAnswer(await client().answer(state.id, signal));
    } catch (error) {
      if (signal.aborted) return;
      if (error.code === 'RESULT_NOT_READY') setNotice(answerBox, 'answer:pending', '该调查已终止但没有已保存的 Answer（RESULT_NOT_READY）；不再自动轮询。', 'conflict');
      else setNotice(answerBox, 'answer:error', codeLine(error), 'error');
    }
    try {
      renderGate(await client().integration(state.id, signal));
    } catch (error) {
      if (signal.aborted) return;
      if (error.code === 'RESULT_NOT_READY') setNotice(gateBox, 'gate:pending', 'Gate 尚未就绪（RESULT_NOT_READY）：按 Retry-After 稍后查询，不继续常规轮询。', 'conflict');
      else if (error.code === 'RESULT_UNAVAILABLE') setNotice(gateBox, 'gate:unavailable', 'RESULT_UNAVAILABLE：调查已终止且未产生 Gate 结果。', 'conflict');
      else if (error.code === 'MOCK_GATE_NOT_INCLUDED') renderGateMockNote();
      else setNotice(gateBox, 'gate:error', codeLine(error), 'error');
    }
    refreshHistory();
  }

  async function requestCancel() {
    if (!state.id) return;
    cancelButton.disabled = true;
    try {
      const status = await client().cancel(state.id, signal);
      if (signal.aborted) return;
      renderStatus(status);
      setNotice(statusBox, 'status:cancel-sent', '取消请求已发出；继续轮询直到 overall_status=CANCELLED 终态。', 'conflict');
      schedule(400);
    } catch (error) {
      if (!signal.aborted && error.name !== 'AbortError') setNotice(statusBox, 'status:cancel-error', codeLine(error), 'error');
    } finally { cancelButton.disabled = false; }
  }

  // ---- 渲染：阶段 / Agent / Gate / 答案 / Artifact / 警告 / 历史 ------------
  function sectionHead(box, title) {
    clearBox(box, title);
    if (mode !== 'mock') return;
    const head = el('div', undefined, { class: 'section-head' });
    head.append(el('span', '数据来源')); mockTag(head);
    box.append(head);
  }

  function renderStages(trace) {
    dropNotices('stages:');
    sectionHead(stagesBox, '阶段进度（trace.stages · 已发生事件）');
    setNotice(stagesBox, 'stages:note', 'stages 是已发生阶段的最新事件；status 来自子 run 或真实事件 code，不是百分比进度；未启动阶段不显示。', 'status');
    if (!Array.isArray(trace.stages) || !trace.stages.length) { setNotice(stagesBox, 'stages:empty', 'Empty / 尚无阶段事件。', 'empty'); return; }
    const list = el('ol', undefined, { class: 'timeline' });
    for (const stage of trace.stages) {
      const item = el('li');
      item.append(el('strong', text(stage.stage) + ' · ' + text(stage.status)));
      const meta = el('p', '时间 ' + text(stage.time) + ' · run ' + text(stage.run_id) + ' · agent ' + text(stage.agent) + ' · artifacts ' + (Array.isArray(stage.artifact_ids) ? stage.artifact_ids.length : 0), { class: 'hint' });
      item.append(meta);
      if (!STAGES.has(stage.stage)) item.append(el('span', '未知阶段枚举：保持原文。', { class: 'badge' }));
      list.append(item);
    }
    stagesBox.append(list);
    const details = el('details');
    details.append(el('summary', '执行事件时间线（trace.events · 实际事件时间）'));
    const rows = (trace.events || []).map(event => ({ at: event.at, stage: event.stage, code: event.code, overall_status: event.overall_status }));
    table(details, rows, [
      { label: '时间', render: row => row.at }, { label: '阶段', render: row => row.stage },
      { label: '事件', render: row => row.code }, { label: 'overall', render: row => row.overall_status }
    ]);
    stagesBox.append(details);
  }

  function renderAgents(trace) {
    dropNotices('agents:');
    sectionHead(agentsBox, 'Agent 执行（planner / agent_runs / tool_calls）');
    if (trace.planner) {
      agentsBox.append(el('h3', 'Planner（独立 run ID）'));
      fields(agentsBox, trace.planner, ['planner_run_id', 'validation_status', 'retry_count', 'prompt_version', 'task_ids']);
    } else setNotice(agentsBox, 'agents:planner', 'Planner 尚未启动（无 planner 摘要）。', 'empty');
    const runs = Array.isArray(trace.agent_runs) ? trace.agent_runs : [];
    if (!runs.length) { setNotice(agentsBox, 'agents:runs', '尚无专业 Agent run；不虚构执行时间。', 'empty'); return; }
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
      } else setNotice(block, 'agents:tools:' + run.run_id, '该 run 没有已公开的工具摘要（原始参数不公开）。', 'empty');
      const refs = (run.artifact_references || []).map(ref => ref.task_id + ' → ' + ref.artifact_id + ' (' + ref.schema_version + ')');
      if (refs.length) { block.append(el('h4', 'Artifact 引用')); for (const line of refs) block.append(el('p', line)); }
      agentsBox.append(block);
    }
  }

  function renderGate(data, { independent = false } = {}) {
    const prefix = independent ? 'gate-i:' : 'gate:';
    const box = independent ? gateBox.querySelector('.gate-independent') : gateBox;
    if (!box) return;
    dropNotices(prefix);
    if (independent) {
      box.replaceChildren();
      box.append(el('h4', '独立 Gate 示例回执（不并入任何场景）'), el('p', 'join_with_five_demo_files=false · ' + text(data.rawNotice), { class: 'hint' }));
    }
    fields(box, data, ['status', 'integration_id', 'trace_id', 'run_id', 'created_at', 'evaluation_time', 'persistence', 'historical_snapshot']);
    if (!GATE.has(data.status)) setNotice(box, prefix + 'unknown', '未知 Gate 状态：保持原文，不归入成功。', 'warning');
    if (data.status === 'PASS_WITH_WARNINGS') setNotice(box, prefix + 'warnings', 'PASS_WITH_WARNINGS：带警告通过；请阅读 warnings 与未解决事项。', 'warning');
    if (data.status === 'REPLAN_REQUIRED') setNotice(box, prefix + 'replan', 'REPLAN_REQUIRED：Gate 要求重新调查；不能渲染成安全或成功结论。', 'conflict');
    if (data.status === 'HUMAN_REVIEW_REQUIRED') setNotice(box, prefix + 'human', 'HUMAN_REVIEW_REQUIRED：需要人工复核；不能渲染成安全或成功结论。', 'conflict');
    if (data.status === 'FAILED') setNotice(box, prefix + 'failed', 'FAILED：Gate 未通过。', 'error');
    if (Array.isArray(data.objective_coverage) && data.objective_coverage.length) {
      box.append(el('h4', 'Objective coverage'));
      table(box, data.objective_coverage, [
        { label: '目标', render: row => row.outcome }, { label: '结果', render: row => row.status },
        { label: '引用数', render: row => (Array.isArray(row.references) ? row.references.length : 0) }
      ]);
    }
    if (Array.isArray(data.checks) && data.checks.length) {
      box.append(el('h4', 'Checks（原样保留，不重新计算）'));
      table(box, data.checks, [
        { label: 'Gate', render: row => row.gate }, { label: 'Code', render: row => row.code },
        { label: '结果', render: row => row.outcome }, { label: 'Blocking', render: row => row.blocking },
        { label: '说明', render: row => row.message }
      ]);
    }
    for (const [label, values] of [['Blocking issues', data.blocking_issues], ['Replan reasons', data.replan_reasons], ['Human review reasons', data.human_review_reasons], ['Warnings', data.warnings], ['未解决事项', data.unresolved_items]]) {
      if (Array.isArray(values) && values.length) {
        box.append(el('h4', label));
        for (const value of values) box.append(el('p', text(value)));
      }
    }
  }

  function renderGateMockNote() {
    const note = el('div', undefined, { class: 'gate-mock-note' });
    note.append(el('p', 'MOCK 只提供 Trace/Answer 中的 Gate 状态与引用；未提供完整 Gate 回执（checks / objective_coverage 在 Mock 中不可得）。', { class: 'message', 'data-state': 'warning' }));
    const button = el('button', '加载独立 Gate 示例回执（不属于当前调查）', { type: 'button' });
    const slot = el('div', undefined, { class: 'gate-independent' });
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        const sample = await loadIndependentGate();
        renderGate({ ...sample.result, rawNotice: sample.notice }, { independent: true });
      } catch (error) { slot.replaceChildren(el('p', codeLine(error))); }
    });
    note.append(button, slot);
    gateBox.append(note);
  }

  function renderAnswer(answer) {
    dropNotices('answer:');
    sectionHead(answerBox, '可信答案（answer · AnswerEnvelope）');
    fields(answerBox, answer, ['answer_status', 'integration_status', 'answer_id', 'generated_at', 'historical_snapshot', 'fact_origin', 'explanation_provider']);
    if (answer.answer_status === 'INCOMPLETE') setNotice(answerBox, 'answer:incomplete', 'answer_status=INCOMPLETE：答案不完整；不能当作已确认结论。', 'conflict');
    if (answer.answer_status === 'REVIEW_REQUIRED') setNotice(answerBox, 'answer:review', 'answer_status=REVIEW_REQUIRED：需要人工复核。', 'conflict');
    if (answer.answer_status === 'CANCELLED') setNotice(answerBox, 'answer:cancelled', 'answer_status=CANCELLED：调查取消，无完整结论。', 'conflict');
    if (answer.answer_status === 'FAILED') setNotice(answerBox, 'answer:failed', 'answer_status=FAILED。', 'error');
    if (answer.answer_status === 'COMPLETE_WITH_WARNINGS') setNotice(answerBox, 'answer:warnings', 'COMPLETE_WITH_WARNINGS：答案带警告。', 'warning');
    if (answer.integration_status && !GATE.has(answer.integration_status)) setNotice(answerBox, 'answer:gate-unknown', '未知 integration_status：保持原文。', 'warning');
    if (answer.summary) answerBox.append(el('p', text(answer.summary)));
    if (Array.isArray(answer.key_findings) && answer.key_findings.length) {
      answerBox.append(el('h4', 'Key findings'));
      for (const finding of answer.key_findings) answerBox.append(el('p', text(finding), { class: 'mono' }));
    }
    if (Array.isArray(answer.affected_assets) && answer.affected_assets.length) {
      answerBox.append(el('h4', '受影响资产（用户库存，不是扫描结果）'));
      table(answerBox, answer.affected_assets, [
        { label: 'Asset', render: row => row.asset_id }, { label: 'Component', render: row => row.component_id },
        { label: '部署版本', render: row => row.deployed_version }, { label: 'Provenance', render: row => row.provenance }
      ]);
    }
    const risk = answer.risk_assessment;
    if (risk) {
      answerBox.append(el('h4', '风险视图（RiskView）'));
      fields(answerBox, risk, ['risk_level', 'priority', 'affected', 'verification_status', 'asset_match_status', 'version_match_status', 'exploitation_status', 'patch_status', 'patch_applied', 'conclusion_scope']);
      if (risk.affected === null || risk.affected === undefined) setNotice(answerBox, 'answer:risk-null', 'affected=null 表示未知，不等于“不受影响”；priority 为 REVIEW_REQUIRED 时需人工复核。', 'warning');
    }
    if (Array.isArray(answer.recommended_actions) && answer.recommended_actions.length) {
      answerBox.append(el('h4', '建议处置（补丁存在 ≠ 资产已修复）'));
      table(answerBox, answer.recommended_actions, [
        { label: '类型', render: row => row.action_type }, { label: '说明', render: row => row.summary },
        { label: '类别', render: row => row.category }, { label: '适用性', render: row => row.applicability },
        { label: '修复版本', render: row => row.fixed_version }, { label: '来源', render: row => row.action_provenance }
      ]);
    }
    if (Array.isArray(answer.verified_claims) && answer.verified_claims.length) {
      answerBox.append(el('h4', '已核验 Claim（CONFIRMED）'));
      table(answerBox, answer.verified_claims, [
        { label: 'Claim', render: row => row.claim_id }, { label: '类型', render: row => row.claim_type },
        { label: '结论值', render: row => text(row.value) }, { label: '状态', render: row => row.verification_status },
        { label: 'Evidence 数', render: row => (Array.isArray(row.evidence_ids) ? row.evidence_ids.length : 0) }
      ]);
    }
    if (Array.isArray(answer.disputed_claims) && answer.disputed_claims.length) {
      answerBox.append(el('h4', '争议 Claim（不能当作已确认事实）'));
      table(answerBox, answer.disputed_claims, [
        { label: 'Claim', render: row => row.claim_id }, { label: '类型', render: row => row.claim_type },
        { label: '状态', render: row => row.verification_status }, { label: '作用范围', render: row => row.scope_key },
        { label: '结论值', render: row => text(row.value) }
      ]);
    }
    if (Array.isArray(answer.citations) && answer.citations.length) {
      answerBox.append(el('h4', '引用（外部内容按文本显示，不打开链接）'));
      table(answerBox, answer.citations, [
        { label: 'Evidence', render: row => row.evidence_id }, { label: 'Claim', render: row => row.claim_id },
        { label: '来源', render: row => row.source_id }, { label: '定位', render: row => text(row.reference?.url) + ' · ' + text(row.reference?.locator) },
        { label: 'Hash', render: row => String(row.hash || '').slice(0, 12) }
      ]);
    }
    if (Array.isArray(answer.evidence_observations) && answer.evidence_observations.length) {
      answerBox.append(el('h4', 'Evidence 观察（支持/反对/中立）'));
      table(answerBox, answer.evidence_observations, [
        { label: 'Evidence', render: row => row.evidence_id }, { label: 'Claim', render: row => row.claim_id },
        { label: '立场', render: row => row.stance }, { label: '直接性', render: row => row.directness },
        { label: '完整性', render: row => row.integrity_status }, { label: '当前有效', render: row => row.is_current }
      ]);
    }
    if (Array.isArray(answer.evidence_references) && answer.evidence_references.length) {
      answerBox.append(el('h4', 'Evidence references'));
      for (const ref of answer.evidence_references) answerBox.append(el('p', text(ref), { class: 'mono' }));
    }
    if (Array.isArray(answer.warnings) && answer.warnings.length) {
      answerBox.append(el('h4', 'Answer warnings'));
      for (const warning of answer.warnings) answerBox.append(el('p', text(warning)));
    }
    if (Array.isArray(answer.unresolved_items) && answer.unresolved_items.length) {
      answerBox.append(el('h4', '未解决事项'));
      for (const item of answer.unresolved_items) answerBox.append(el('p', text(item)));
    }
    answerBox.append(el('p', '事实来自冻结 Gate 上下文与确定性模板；本页不新增事实。', { class: 'hint' }));
  }

  function renderArtifacts(data) {
    dropNotices('artifacts:');
    sectionHead(artifactsBox, '专业 Artifact（artifacts）');
    if (mode === 'mock') setNotice(artifactsBox, 'artifacts:mock', data?.mock_missing || '该 Mock 场景未提供 Artifact 回执。', 'warning');
    const slots = [['investigation', 'InvestigationArtifact', 'status'], ['verification', 'VerificationArtifact', 'verification_status'], ['analysis', 'RiskAnalysisArtifact', 'risk_level']];
    for (const [key, label, statusKey] of slots) {
      const artifact = data?.[key];
      if (!artifact) { setNotice(artifactsBox, 'artifacts:' + key, label + '：null —— 尚未产生或该阶段没有执行；不创建假节点或假结果。', 'empty'); continue; }
      const block = el('div', undefined, { class: 'run-block' });
      block.append(el('h3', label + ' · ' + text(artifact[statusKey])));
      fields(block, artifact, ['artifact_id', 'run_id', 'task_id', 'schema_version', statusKey, 'runtime_status', 'information_status', 'confidence', 'partial_result', 'execution_status', 'coverage_complete'].filter(key2 => artifact[key2] !== undefined));
      for (const [title, values] of [['uncertainties', artifact.uncertainties], ['warnings', artifact.warnings], ['unresolved_items', artifact.unresolved_items], ['conflicts', artifact.conflicts]]) {
        if (Array.isArray(values) && values.length) { block.append(el('h4', title)); for (const value of values) block.append(el('p', text(value))); }
      }
      jsonBlock(block, artifact, 'Artifact 公共投影（脱敏）');
      artifactsBox.append(block);
    }
  }

  function renderWarnings(status, trace) {
    dropNotices('warnings:');
    clearBox(warningsBox, '警告与未解决事项');
    mockTag(warningsBox);
    const values = [
      ...(Array.isArray(status.warnings) ? status.warnings.map(item => ['status', item]) : []),
      ...(Array.isArray(trace?.warnings) ? trace.warnings.map(item => ['trace', item]) : []),
      ...(Array.isArray(trace?.unresolved_items) ? trace.unresolved_items.map(item => ['unresolved', item]) : [])
    ];
    if (!values.length) { setNotice(warningsBox, 'warnings:empty', '后端没有返回警告字段；这不代表结果完整或已经确认。', 'empty'); return; }
    table(warningsBox, values, [{ label: '来源', render: row => row[0] }, { label: '内容', render: row => text(row[1]) }]);
  }

  async function refreshHistory() {
    try {
      const data = await client().history({ limit: 10, sort: 'created_desc' }, signal);
      if (signal.aborted) return;
      clearBox(historyBox, '历史调查（history）');
      mockTag(historyBox);
      setNotice(historyBox, 'history:note', '只读已保存记录；点击“读取”进入该调查，不重新提交。' + (mode === 'mock' ? ' Mock 模式会跳到该场景终态。' : ''), 'status');
      table(historyBox, data.items || [], [
        { label: '更新时间', render: row => row.updated_at }, { label: '问题', render: row => String(row.original_question || '').slice(0, 60) },
        { label: '阶段', render: row => row.current_stage }, { label: '结果', render: row => row.overall_status },
        { label: '错误码', render: row => row.error_code }, { label: '操作', render: row => {
          const button = el('button', '读取', { type: 'button' });
          button.addEventListener('click', () => openExisting(row));
          return button;
        } }
      ]);
    } catch (error) {
      if (signal.aborted || error.name === 'AbortError') return;
      clearBox(historyBox, '历史调查（history）');
      setNotice(historyBox, 'history:error', codeLine(error) + (error.status === 401 ? '：需要有效 Bearer 凭据。' : ''), error.status === 401 ? 'error' : 'conflict');
    }
  }

  async function openExisting(row) {
    try {
      if (client().isMock) await mock.openScenario(row.investigation_id);
      resumeInput.value = row.investigation_id;
      watch(row.investigation_id);
      await refreshBanner();
    } catch (error) {
      setNotice(historyBox, 'history:open', codeLine(error), 'error');
    }
  }

  function watch(id) {
    resetWorkbench();
    state.id = id;
    session.setRunId(id);
    resumeInput.value = id;
    setNotice(requestState, 'watch', '正在读取调查 ' + id + '（只轮询 status，不重复提交）。', 'status');
    tick();
  }

  async function submitInvestigation(request, key) {
    resetWorkbench();
    submit.disabled = true; retry.hidden = true;
    setNotice(requestState, 'request', 'Loading / 正在创建调查（POST /api/investigations）…', 'loading');
    try {
      const data = await client().create(request, key, signal);
      if (signal.aborted) return;
      dropNotices('request');
      const lines = [data.reused ? '幂等键命中：复用已有调查（reused=true），返回当前真实阶段。' : '已受理（HTTP 202）：根记录已保存；不代表调查完成，继续轮询 status。'];
      if (data.is_mock) lines.push('后端模型为 Mock（model_provider=' + text(data.model_provider) + '，is_mock=true）。');
      setNotice(requestState, 'request', lines.join(' '), 'status');
      state.id = data.investigation_id;
      session.setRunId(state.id); resumeInput.value = state.id;
      renderStatus(data);
      await tick();
      refreshHistory();
    } catch (error) {
      if (signal.aborted) return;
      dropNotices('request');
      setNotice(requestState, 'request', codeLine(error), 'error');
      if (error.code === 'IDEMPOTENCY_CONFLICT') setNotice(requestState, 'request:hint', '同一幂等键的请求内容不同（IDEMPOTENCY_CONFLICT）；更换键仅用于新的问题，不能无脑重试。', 'conflict');
      else if (error.status === 429 || error.status === 503) setNotice(requestState, 'request:hint', '可稍后用同一幂等键重试：“' + key + '”（ACK 超时不等于根一定没有保存）。', 'conflict');
      else if (error.kind === 'network' && mode === 'real') setNotice(requestState, 'request:hint', '本机未启动后端（8769 → 8000 不可达）时，可手动切换“Mock 演示”查看交互；Mock 为合成数据，不是真实执行。', 'conflict');
      retry.hidden = !(error.kind === 'network' || error.status === 429 || error.status === 503);
      submit.disabled = false;
    } finally { submit.disabled = false; }
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

  modeSelect.addEventListener('change', async () => {
    mode = modeSelect.value;
    scenarioLabel.hidden = mode !== 'mock';
    resetWorkbench();
    dropNotices('request');
    setNotice(requestState, 'request', mode === 'mock' ? '已切换到 Mock 演示：回放历史合成测试回执，不访问后端。' : '已切换到真实 API：请求 8769 同源代理 /api/investigations。', 'status');
    if (mode === 'mock') {
      try { await prefillScenarioQuestion(); }
      catch (error) { setNotice(requestState, 'request', codeLine(error), 'error'); }
    }
    await refreshBanner();
    refreshHistory();
  });
  scenarioSelect.addEventListener('change', async () => {
    scenario = scenarioSelect.value;
    dropNotices('request');
    try {
      await mock.setScenario(scenario);
      await prefillScenarioQuestion();
      resetWorkbench();
      setNotice(requestState, 'request', '已切换到 Mock 场景 ' + scenario + '：提交后按 1 秒回放该场景终态。', 'status');
      await refreshBanner();
    } catch (error) { setNotice(requestState, 'request', codeLine(error), 'error'); }
  });

  // ---- 初始化 ------------------------------------------------------------
  scenarioLabel.hidden = mode !== 'mock';
  const existing = session.getRunId();
  if (existing) resumeInput.value = existing;
  for (const box of boxes) if (!box.children.length) message(box, 'Empty / 尚未读取。', 'empty');
  if (mode === 'mock') prefillScenarioQuestion().catch(error => setNotice(requestState, 'request', codeLine(error), 'error'));
  refreshBanner();
  refreshHistory();
  if (demoParam) setNotice(requestState, 'request', '通过 ?demo=' + demoParam + ' 进入 Mock 演示；提交后按 1 秒回放该场景。', 'status');
}