import { pageTitle, el, section, table, link, load, jsonBlock, message, pager, fields, showError } from '../components.js';

const LIMIT = 20;

export function vulnerabilities(view, { api, signal }) {
  pageTitle(view, '漏洞', '统一浏览漏洞情报；列表状态为来源断言，非已验证情报。');
  const form = el('form');
  const search = el('input', undefined, { type: 'search', 'aria-label': 'CVE / 漏洞标识符', placeholder: 'CVE / 漏洞标识符', maxlength: '150' });
  const sort = el('select', undefined, { 'aria-label': '排序方式' });
  for (const [value, label] of [['modified_desc', '按更新时间'], ['published_desc', '按公布时间']]) {
    const option = el('option', label, { value });
    sort.append(option);
  }
  form.append(search, sort, el('button', '查询', { type: 'submit' }));
  view.append(form);
  const results = section('查询结果', view);
  let generation = 0;
  let offset = 0;
  function fetchList() {
    const current = ++generation;
    results.replaceChildren(el('h2', '查询结果'));
    load(results, () => api.vulnerabilitiesPage(signal, { offset, limit: LIMIT, sort: sort.value, query: search.value.trim() }), data => {
      if (current !== generation) return;
      const info = el('p', `共 ${data.total ?? '—'} 条记录` + (search.value.trim() ? ` · 关键词「${search.value.trim()}」` : ''), { class: 'panel-caption' });
      results.append(info);
      table(results, data.items, [
        { label: '漏洞', render: row => link(row.canonical_id, '/vulnerabilities/' + encodeURIComponent(row.canonical_id || row.id)) },
        { label: '标题', key: 'title' }, { label: '等级', key: 'primary_severity' },
        { label: '记录状态', key: 'status' }, { label: '公布时间', key: 'published_at' }, { label: '更新时间', key: 'modified_at' }
      ]);
      pager(results, { offset, limit: LIMIT, total: data.total ?? 0, onPage: next => { offset = next; fetchList(); } });
      message(results, '列表数据为来源断言（source assertions; not verified intelligence）', 'status');
    }, signal);
  }
  form.addEventListener('submit', event => { event.preventDefault(); offset = 0; fetchList(); });
  sort.addEventListener('change', () => { offset = 0; fetchList(); });
  fetchList();
}

export async function vulnerability(view, { api, signal }, { id }) {
  pageTitle(view, id);
  const body = section('漏洞详情', view);
  body.dataset.viewState = 'LOADING';
  body.setAttribute('aria-busy', 'true');
  const pending = message(body, '读取中…', 'loading');
  try {
    const data = await api.vulnerability(id, signal);
    if (signal?.aborted) return;
    pending.remove();
    if (data === null || data === undefined || typeof data === 'object' && !Array.isArray(data) && !Object.keys(data).length) {
      body.dataset.viewState = 'EMPTY';
      message(body, '暂无漏洞详情数据。', 'empty');
      return;
    }
    if (typeof data !== 'object' || Array.isArray(data)) throw new Error('漏洞详情响应格式不符合接口契约。');
    const warnings = Array.isArray(data.warnings) ? data.warnings : [];
    const conflict = Array.isArray(data.conflicts) && data.conflicts.length || Array.isArray(data.claims) && data.claims.some(row => row?.verification_status === 'CONFLICT');
    const partial = !data.canonical_id || !data.title || !data.description;
    body.dataset.viewState = warnings.length || conflict || partial ? 'WARNING' : 'SUCCESS';
    if (partial) message(body, '部分漏洞信息尚未提供；保留 UNKNOWN，不补造字段。', 'warning');
    for (const warning of warnings) message(body, warning, 'warning');
    fields(body, data, ['canonical_id', 'title', 'description', 'primary_severity', 'status', 'verification_status', 'published_at', 'modified_at']);
    if (conflict) message(body, '存在未解决来源冲突', 'conflict');
    const datasets = [
      ['cvss_assessments', 'CVSS 来源断言'], ['affected_versions', '影响版本'], ['source_variants', '来源版本与确认状态'],
      ['claims', 'Claims'], ['evidence', 'Evidence'], ['pocs', 'POC 候选'], ['patches', 'Patch 候选'],
      ['known_exploitation', '已知利用'], ['conflicts', 'Conflict'], ['reviews', 'Human Review']
    ];
    for (const [key, title] of datasets) {
      const group = section(title, view);
      const rows = data[key];
      if (!Array.isArray(rows) || !rows.length) message(group, '暂无记录', 'empty');
      else for (const row of rows) jsonBlock(group, row, row?.id || row?.source || title);
    }
    jsonBlock(view, data, '完整 API 字段');
  } catch (error) {
    if (signal?.aborted || error.name === 'AbortError') return;
    pending.remove();
    body.dataset.viewState = 'ERROR';
    showError(body, error);
  } finally {
    if (!signal?.aborted) body.setAttribute('aria-busy', 'false');
  }
}
