import { pageTitle, el, section, fields, table, link, load, jsonBlock, message } from '../components.js';

export function vulnerabilities(view, { api, signal }) {
  pageTitle(view, '漏洞', '读取 /api/v1/vulnerabilities?limit=20；精确证据和确认状态请进入详情。');
  const form = el('form');
  const search = el('input', undefined, { type: 'search', 'aria-label': 'CVE / 漏洞标识符', placeholder: 'CVE / 漏洞标识符', maxlength: '150' });
  form.append(search, el('button', '查询', { type: 'submit' })); view.append(form);
  const results = section('查询结果', view);
  let generation = 0;
  function fetchList() {
    const current = ++generation;
    results.replaceChildren(el('h2', '查询结果'));
    load(results, () => api.vulnerabilities(signal, search.value.trim()), data => {
      if (current !== generation) return;
      fields(results, data, ['total', 'offset', 'limit', 'data_status', 'coverage']);
      table(results, data.items, [
        { label: '漏洞', render: row => link(row.canonical_id, '/vulnerabilities/' + encodeURIComponent(row.canonical_id || row.id)) },
        { label: '标题', key: 'title' }, { label: '等级', key: 'primary_severity' },
        { label: '记录状态', key: 'status' }, { label: '公布时间（原值）', key: 'published_at' }, { label: '更新时间（原值）', key: 'modified_at' }
      ]);
    }, signal);
  }
  form.addEventListener('submit', event => { event.preventDefault(); fetchList(); });
  fetchList();
}

export function vulnerability(view, { api, signal }, { id }) {
  pageTitle(view, id, '来源内容只作为数据展示；未确认的 POC、Patch 或版本影响不提升为确认事实。');
  const body = section('漏洞详情', view);
  load(body, () => api.vulnerability(id, signal), data => {
    fields(body, data, ['canonical_id', 'title', 'description', 'primary_severity', 'status', 'verification_status', 'published_at', 'modified_at']);
    if (data.conflicts?.length || data.claims?.some(row => row.verification_status === 'CONFLICT')) message(body, 'Conflict / 存在未解决来源冲突。请查看冲突与复核记录。', 'conflict');
    const datasets = [
      ['cvss_assessments', 'CVSS 来源断言'], ['affected_versions', '影响版本'], ['source_variants', '来源版本与确认状态'],
      ['claims', 'Claims'], ['evidence', 'Evidence'], ['pocs', 'POC 候选'], ['patches', 'Patch 候选'],
      ['known_exploitation', '已知利用'], ['conflicts', 'Conflict'], ['reviews', 'Human Review']
    ];
    for (const [key, title] of datasets) {
      const group = section(title, view);
      const rows = data[key];
      if (!Array.isArray(rows) || !rows.length) message(group, 'Empty / 当前 API 没有提供记录。', 'empty');
      else for (const row of rows) jsonBlock(group, row, row.id || row.source || title);
    }
    jsonBlock(view, data, '完整漏洞 API 字段（含日期、来源、历史与未确认状态）');
  }, signal);
}
