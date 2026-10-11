import { normalizeRun } from '../services.js';
import { auditSummary } from '../audit.js';
import { pageTitle, el, section, fields, table, link, message, showError, jsonBlock, load, text } from '../components.js';

const knownStates = new Set(['PLANNING', 'RUNNING', 'WAITING_TOOL', 'VERIFYING', 'REPLANNING', 'WAITING_REVIEW', 'COMPLETED', 'FAILED']);
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function rows(data, keys = []) {
  if (Array.isArray(data)) return data;
  for (const key of ['items', ...keys]) if (Array.isArray(data?.[key])) return data[key];
  return data && typeof data === 'object' ? [data] : [];
}

function auditTable(parent, data, keys) {
  const items = rows(data, keys);
  table(parent, items, [
    { label: '任务 / 调用', render: row => row.task_id || row.tool_name || row.id },
    { label: 'Agent / Tool', render: row => row.agent || row.tool_name },
    { label: '状态', render: row => row.status || row.state }, { label: '摘要', render: row => row.summary || row.goal || row.result_summary || row.output_summary?.status },
    { label: '依赖 / 时间 / 警告', render: row => {
      const node = el('div');
      const safe = auditSummary(row);
      jsonBlock(node, safe, '展开可审计字段'); return node;
    } }
  ]);
}

export function assistant(view, { api, session, signal }) {
  pageTitle(view, 'Assistant', '提问 → 后端选择 Fast / Deep → 可审计任务摘要 → Evidence → 结果与不确定性。');
  const form = el('form', undefined, { class: 'assistant-form' });
  const question = el('textarea', undefined, { id: 'question', required: '', maxlength: '2000', placeholder: '输入安全问题；答案只使用实际后端返回的数据。' });
  const questionLabel = el('label', 'Question'); questionLabel.append(question); form.append(questionLabel);
  const asset = el('input', undefined, { type: 'text', placeholder: '可选资产 UUID', 'aria-label': '可选资产 UUID', maxlength: '36' });
  const assetLabel = el('label', 'Asset ID（可选）'); assetLabel.append(asset); form.append(assetLabel);
  const target = el('input', undefined, { type: 'text', placeholder: '可选 CVE / 目标组件', 'aria-label': '可选目标', maxlength: '150' });
  const targetLabel = el('label', 'Target（可选）'); targetLabel.append(target); form.append(targetLabel);
  const mode = el('select', undefined, { 'aria-label': '运行模式' });
  for (const value of ['auto', 'fast', 'deep']) mode.append(el('option', value, { value }));
  const modeLabel = el('label', 'Mode'); modeLabel.append(mode); form.append(modeLabel);
  const submit = el('button', '提交问题', { type: 'submit' });
  const retry = el('button', '重试同一请求', { type: 'button', hidden: '' });
  form.append(submit, retry); view.append(form);
  const requestState = el('div', undefined, { 'aria-live': 'polite' }); view.append(requestState);
  const statusBox = section('Run Status', view);
  const refresh = el('button', '刷新当前运行', { type: 'button' });
  const resumeForm = el('form');
  const runInput = el('input', undefined, { type: 'text', 'aria-label': '已有 Run ID', placeholder: '已有 Run UUID', maxlength: '36' });
  resumeForm.append(runInput, el('button', '读取运行', { type: 'submit' })); view.append(resumeForm, refresh);
  const tasksBox = section('Task Trace · 任务摘要', view);
  const traceBox = section('Task Trace · 工具调用摘要', view);
  const resultBox = section('Result', view);
  const evidenceBox = section('Evidence', view);
  const vulnsBox = section('Related Vulnerabilities', view);
  const assetsBox = section('Related Assets', view);
  const warningsBox = section('Warnings / Uncertainty', view);
  for (const node of [statusBox, tasksBox, traceBox, resultBox, evidenceBox, vulnsBox, assetsBox, warningsBox]) message(node, 'Empty / 尚未读取运行。', 'empty');
  let runId = session.getRunId();
  let lastPayload = null;
  let timer;
  let polling = false;
  let polls = 0;
  signal.addEventListener('abort', () => clearTimeout(timer), { once: true });

  function clearSection(node, title) { node.replaceChildren(el('h2', title)); }

  function renderRelated(parent, values, kind) {
    if (!Array.isArray(values) || !values.length) { message(parent, 'Empty / 后端未提供关联记录。', 'empty'); return; }
    for (const row of values) {
      const object = typeof row === 'object' && row !== null;
      const id = object ? kind === 'vuln' ? row.canonical_id || row.vulnerability_id || row.id : row.asset_id || row.id : row;
      const label = object ? row.canonical_id || row.name || row.asset_name || id : row;
      if (!id) { jsonBlock(parent, row, '关联记录'); continue; }
      const item = el('p');
      item.append(link(label, kind === 'vuln' ? '/vulnerabilities/' + encodeURIComponent(id) : '/assets?asset=' + encodeURIComponent(id)));
      if (object) jsonBlock(item, row, '关联字段');
      parent.append(item);
    }
  }

  function renderEvidence(values) {
    if (!Array.isArray(values) || !values.length) { message(evidenceBox, 'Empty / 后端未提供 Evidence Reference。', 'empty'); return; }
    for (const ref of values) {
      const id = typeof ref === 'object' && ref !== null ? ref.evidence_id || ref.id : ref;
      const item = el('div'); item.append(el('p', text(ref)));
      if (typeof id === 'string' && uuid.test(id)) {
        const button = el('button', '展开 Evidence ' + id, { type: 'button' });
        const detail = el('div');
        button.addEventListener('click', () => {
          button.disabled = true;
          load(detail, () => api.evidence(id, signal), data => jsonBlock(detail, data, 'Evidence 原始字段、来源、定位符与确认状态'), signal);
        });
        item.append(button, detail);
      }
      evidenceBox.append(item);
    }
  }

  function showRun(data) {
    const run = normalizeRun(data);
    clearSection(statusBox, 'Run Status');
    fields(statusBox, run, ['run_id', 'trace_id', 'status', 'route']);
    if (!knownStates.has(run.status)) message(statusBox, '后端返回未知状态；未将其视为完成。', 'error');
    if (run.shouldPoll) message(statusBox, 'Agent Running / 正在执行；每 2 秒读取一次执行摘要。', 'running');
    if (run.status === 'WAITING_REVIEW') message(statusBox, 'WAITING_REVIEW / 需要人工复核。自动轮询已停止，可以手动刷新。', 'conflict');
    if (run.status === 'FAILED') message(statusBox, 'FAILED / 后端运行失败；保留警告与任务摘要。', 'error');
    for (const [node, title] of [[resultBox, 'Result'], [evidenceBox, 'Evidence'], [vulnsBox, 'Related Vulnerabilities'], [assetsBox, 'Related Assets'], [warningsBox, 'Warnings / Uncertainty']]) clearSection(node, title);
    const result = run.result;
    if (result === undefined || result === null) message(resultBox, 'Empty / 当前运行尚无最终结果。', 'empty');
    else if (typeof result === 'string') resultBox.append(el('p', result));
    else {
      for (const key of ['conclusion', 'summary', 'answer', 'uncertainty']) if (typeof result[key] === 'string') resultBox.append(el('p', result[key]));
      const details = el('details', undefined, { open: '' });
      details.append(el('summary', '后端结果（结构化字段）'), el('pre', JSON.stringify(result, null, 2))); resultBox.append(details);
    }
    renderEvidence(result?.evidence_refs || result?.evidence || run.evidence_refs || []);
    renderRelated(vulnsBox, result?.related_vulnerabilities || result?.vulnerabilities || run.related_vulnerabilities || [], 'vuln');
    renderRelated(assetsBox, result?.related_assets || result?.assets || run.related_assets || [], 'asset');
    const warnings = [...run.warnings, ...(Array.isArray(result?.warnings) ? result.warnings : []), ...(Array.isArray(result?.unresolved) ? result.unresolved : [])];
    if (warnings.length) for (const warning of warnings) message(warningsBox, text(warning), 'warning');
    else message(warningsBox, '后端没有返回警告字段；这不代表结果完整或已经确认。', 'empty');
    return run;
  }

  async function poll() {
    if (!runId || signal.aborted || polling) return;
    clearTimeout(timer); polling = true;
    try {
      const run = showRun(await api.run(runId, signal));
      submit.disabled = run.shouldPoll;
      const reads = await Promise.allSettled([api.tasks(runId, signal), api.trace(runId, signal)]);
      if (signal.aborted) return;
      clearSection(tasksBox, 'Task Trace · 任务摘要'); clearSection(traceBox, 'Task Trace · 工具调用摘要');
      for (let index = 0; index < reads.length; index++) {
        const box = index ? traceBox : tasksBox;
        if (reads[index].status === 'fulfilled') {
          auditTable(box, reads[index].value, index ? ['trace', 'tool_calls'] : ['tasks']);
          if (index && Array.isArray(reads[index].value?.events)) {
            box.append(el('h3', '执行事件'));
            auditTable(box, reads[index].value.events, []);
          }
        }
        else showError(box, reads[index].reason);
      }
      polls += 1;
      if (run.shouldPoll && polls < 90) timer = setTimeout(poll, 2000);
      else if (run.shouldPoll) message(statusBox, '已达到本次页面轮询上限。运行 ID 保留；使用“刷新当前运行”继续查询。');
    } catch (error) {
      if (!signal.aborted) { showError(statusBox, error); submit.disabled = false; }
    } finally { polling = false; }
  }

  async function start(payload) {
    clearTimeout(timer); requestState.replaceChildren();
    submit.disabled = true; retry.hidden = true;
    const pending = message(requestState, 'Loading / 正在提交问题…', 'loading');
    try {
      const data = await api.startRun(payload, signal);
      if (signal.aborted) return;
      pending.remove();
      if (!data?.run_id) throw new Error('Assistant API 未返回 run_id。');
      runId = data.run_id; session.setRunId(runId); runInput.value = runId; polls = 0;
      message(requestState, '已提交；request_key: ' + payload.request_key);
      showRun(data);
      await poll();
    } catch (error) {
      pending.remove();
      if (!signal.aborted) {
        showError(requestState, error);
        retry.hidden = !['network', 'server'].includes(error.kind);
        submit.disabled = false;
      }
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!question.value.trim()) { requestState.replaceChildren(); message(requestState, '请输入问题。', 'error'); return; }
    if (asset.value.trim() && !uuid.test(asset.value.trim())) { requestState.replaceChildren(); message(requestState, 'Asset ID 必须为 UUID。', 'error'); return; }
    lastPayload = { question: question.value.trim(), mode: mode.value, request_key: crypto.randomUUID(), realtime: false };
    if (asset.value.trim()) lastPayload.asset_id = asset.value.trim();
    if (target.value.trim()) lastPayload.target = target.value.trim();
    start(lastPayload);
  });
  retry.addEventListener('click', () => { if (lastPayload) start(lastPayload); });
  refresh.addEventListener('click', () => { polls = 0; poll(); });
  resumeForm.addEventListener('submit', event => {
    event.preventDefault();
    if (!uuid.test(runInput.value.trim())) { showError(statusBox, new Error('Run ID 必须为 UUID。')); return; }
    runId = runInput.value.trim(); session.setRunId(runId); polls = 0; poll();
  });
  if (runId) { runInput.value = runId; poll(); }
}
