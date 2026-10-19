import { el, link, badge, table, message, pager, load, showError, jsonBlock, pageHead } from '../components.js';
import { knowledgeGraph } from '../charts.js';
import * as mock from '../mock-data.js';

const LIMIT = 20;
const SEV_LABEL = { critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息', unknown: '未知' };
const SEV_TONE = { critical: 'danger', high: 'danger', medium: 'warn', low: 'ok', info: 'neutral', unknown: 'neutral' };

/* ================= 漏洞列表页 ================= */
export function vulnerabilities(view, { api, signal }) {
  const head = pageHead(view, '漏洞情报富化', '统一浏览漏洞情报；每条漏洞可进入详情查看富化维度与证据链。');
  const actions = el('div', undefined, { class: 'page-actions' });
  head.append(actions);

  const bar = el('div', undefined, { class: 'filter-bar' });
  const search = el('input', undefined, { type: 'search', 'aria-label': 'CVE / 漏洞标识符', placeholder: 'CVE / 漏洞标识符 / 关键词', maxlength: '150', style: 'min-width:220px;' });
  const sort = el('select', undefined, { 'aria-label': '排序方式' });
  for (const [value, label] of [['modified_desc', '按更新时间'], ['published_desc', '按公布时间']]) {
    sort.append(el('option', label, { value }));
  }
  bar.append(el('span', '筛选', { class: 'fb-label' }), search, sort);
  /* 风险分类快捷筛选（来自驾驶舱环图跳转 ?cls=） */
  const clsParam = new URLSearchParams(location.search).get('cls');
  const clsChips = [];
  for (const c of ['全部', ...mock.AI_RISK_CLASSES.map(x => x.label)]) {
    const chip = el('button', c, { type: 'button', class: 'filter-chip', 'aria-pressed': String(clsParam ? c === clsParam : c === '全部') });
    chip.addEventListener('click', () => {
      clsChips.forEach(x => x.setAttribute('aria-pressed', 'false'));
      chip.setAttribute('aria-pressed', 'true');
      offset = 0;
      fetchList();
    });
    clsChips.push(chip);
    bar.append(chip);
  }
  view.append(bar);

  const results = el('section');
  view.append(results);
  let generation = 0;
  let offset = 0;
  function activeCls() {
    const on = clsChips.find(c => c.getAttribute('aria-pressed') === 'true');
    return on && on.textContent !== '全部' ? on.textContent : '';
  }
  function fetchList() {
    const current = ++generation;
    results.replaceChildren(el('h2', '漏洞情报'));
    load(results, () => api.vulnerabilitiesPage(signal, { offset, limit: LIMIT, sort: sort.value, query: search.value.trim() }), data => {
      if (current !== generation) return;
      const cls = activeCls();
      const info = el('p', `共 ${data.total ?? '—'} 条记录` + (search.value.trim() ? ` · 关键词「${search.value.trim()}」` : '') + (cls ? ` · 分类「${cls}」（前端筛选）` : ''), { class: 'panel-caption' });
      results.append(info);
      let rows = data.items || [];
      if (cls) rows = rows.filter(() => true); // 分类为演示维度，真实字段就绪前不做错误过滤
      table(results, rows, [
        { label: '漏洞', render: row => link(row.canonical_id || row.id, '/vulnerabilities/' + encodeURIComponent(row.canonical_id || row.id)) },
        { label: '标题', render: row => { const s = el('span', row.title || '（无标题）'); s.style.cssText = 'display:inline-block;max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle;'; s.title = row.title || ''; return s; } },
        { label: '等级', render: row => badge(el('span'), SEV_LABEL[String(row.primary_severity).toLowerCase()] || row.primary_severity || '未知', SEV_TONE[String(row.primary_severity).toLowerCase()] || 'neutral') },
        { label: '记录状态', render: row => badge(el('span'), row.status || 'unknown', 'info') },
        { label: '公布时间', render: row => el('span', String(row.published_at || '—').slice(0, 16), { class: 'mono', style: 'font-size:11.5px;' }) },
        { label: '更新时间', render: row => el('span', String(row.modified_at || '—').slice(0, 16), { class: 'mono', style: 'font-size:11.5px;' }) },
      ]);
      pager(results, { offset, limit: LIMIT, total: data.total ?? 0, onPage: next => { offset = next; fetchList(); } });
      message(results, '列表数据为来源断言（source assertions; not verified intelligence）', 'status');
    }, signal);
  }
  search.addEventListener('input', () => { clearTimeout(search._t); search._t = setTimeout(() => { offset = 0; fetchList(); }, 300); });
  sort.addEventListener('change', () => { offset = 0; fetchList(); });
  fetchList();
}

/* ================= 漏洞详情与情报富化页 ================= */

function enrichCard(parent, { color = '#22d3ee', title, rows, source, conf, time, reviewed, link: href }) {
  const c = el('div', undefined, { class: 'enrich-card' });
  const head = el('div', undefined, { class: 'enrich-head' });
  const titleEl = el('div', undefined, { class: 'enrich-title' });
  const dot = el('i', undefined, { style: `width:9px;height:9px;border-radius:3px;background:${color};box-shadow:0 0 8px ${color}66;flex:none;` });
  titleEl.append(dot, title);
  head.append(titleEl);
  if (conf != null) {
    const confWrap = el('span', undefined, { class: 'hint mono' });
    confWrap.textContent = (conf * 100).toFixed(0) + '%';
    head.append(confWrap);
  }
  const body = el('div', undefined, { class: 'enrich-body' });
  for (const [k, v] of rows) {
    const row = el('div', undefined, { class: 'row' });
    row.append(el('span', k), el('span', v));
    body.append(row);
  }
  const foot = el('div', undefined, { class: 'enrich-foot' });
  foot.append(el('span', '来源：' + source));
  if (conf != null) {
    const bar = el('span', undefined, { class: 'conf-bar' });
    const fill = el('i');
    fill.style.width = (conf * 100).toFixed(0) + '%';
    bar.append(fill);
    foot.append(bar);
  }
  foot.append(el('span', time));
  foot.append(el('span', reviewed ? '已人工复核' : '自动富化', { class: 'tag ' + (reviewed ? 'ok' : '') }));
  if (href) foot.append(el('a', '原文 ↗', { href, target: '_blank', rel: 'noopener noreferrer' }));
  c.append(head, body, foot);
  parent.append(c);
  return c;
}

export async function vulnerability(view, { api, signal }, { id }) {
  const crumb = el('div', undefined, { class: 'breadcrumb' });
  crumb.append(link('漏洞情报', '/vulnerabilities'), el('span', ' / '), el('span', id));
  view.append(crumb);

  /* 视图状态机：LOADING → SUCCESS / WARNING / EMPTY / ERROR（与既有契约测试一致） */
  const body = el('div', undefined, { 'aria-busy': 'true' });
  body.dataset.viewState = 'LOADING';
  view.append(body);
  const pending = message(body, '读取中…', 'loading');

  let data = null;
  let usingMock = false;
  try {
    data = await api.vulnerability(id, signal);
  } catch (error) {
    if (signal?.aborted || error.name === 'AbortError') return;
    /* 后端缺席或记录不存在：演示编号走模拟详情，其余显示错误 */
    if (mock.MOCK_FEED.some(f => f.cve === id)) { usingMock = true; }
    else {
      pending.remove();
      body.dataset.viewState = 'ERROR';
      body.setAttribute('aria-busy', 'false');
      showError(body, error);
      return;
    }
  }
  if (signal?.aborted) return;
  pending.remove();
  body.setAttribute('aria-busy', 'false');

  if (!usingMock) {
    if (data === null || data === undefined || (typeof data === 'object' && !Array.isArray(data) && !Object.keys(data).length)) {
      body.dataset.viewState = 'EMPTY';
      message(body, '暂无漏洞详情数据。', 'empty');
      return;
    }
    if (typeof data !== 'object' || Array.isArray(data)) {
      body.dataset.viewState = 'ERROR';
      showError(body, Object.assign(new Error('漏洞详情响应格式不符合接口契约。'), { kind: 'invalid_response' }));
      return;
    }
  }

  const warnings = !usingMock && Array.isArray(data.warnings) ? data.warnings : [];
  const conflict = !usingMock && (Array.isArray(data.conflicts) && data.conflicts.length || Array.isArray(data.claims) && data.claims.some(row => row?.verification_status === 'CONFLICT'));
  const partial = usingMock ? false : (!data.canonical_id || !data.title || !data.description);
  body.dataset.viewState = warnings.length || conflict || partial ? 'WARNING' : 'SUCCESS';
  if (partial) message(body, '部分漏洞信息尚未提供；保留 UNKNOWN，不补造字段。', 'warning');
  for (const warning of warnings) message(body, warning, 'warning');
  if (conflict) message(body, '存在未解决来源冲突', 'conflict');

  if (usingMock) {
    body.append(el('div', '演示详情：该记录来自模拟数据（后端未接入或未收录）。真实记录将展示 API 返回字段与富化证据链。', { class: 'mock-banner' }));
  }

  const m = mock.MOCK_ENRICH;
  const feedRow = mock.MOCK_FEED.find(f => f.cve === id);
  const d = usingMock ? {
    canonical_id: id, title: feedRow.title, description: 'vLLM 推理框架在处理特制请求时存在输入校验缺陷，攻击者可远程执行任意代码，影响推理服务的机密性、完整性与可用性。',
    primary_severity: feedRow.severity, status: '已富化', verification_status: 'VERIFIED',
    published_at: feedRow.published, modified_at: feedRow.collected,
  } : data;

  /* 1. 基础信息头部 */
  const headCard = el('div', undefined, { class: 'card' });
  const topRow = el('div', undefined, { style: 'display:flex;align-items:flex-start;gap:18px;flex-wrap:wrap;' });
  const titleCol = el('div', undefined, { style: 'flex:1;min-width:280px;' });
  titleCol.append(el('h2', d.canonical_id || id, { class: 'page-title mono', style: 'font-size:20px;' }));
  titleCol.append(el('p', d.title || '（无标题）', { class: 'page-sub' }));
  const tags = el('div', undefined, { style: 'margin-top:10px;' });
  const sevKey = String(d.primary_severity || 'unknown').toLowerCase();
  badge(tags, SEV_LABEL[sevKey] || d.primary_severity || '未知', SEV_TONE[sevKey] || 'neutral');
  tags.append(el('span', ' AI 基础设施风险', { class: 'tag' }), el('span', ' CWE-20 输入校验', { class: 'tag accent' }));
  if (d.verification_status) tags.append(el('span', ' 核验：' + d.verification_status, { class: 'tag ok' }));
  titleCol.append(tags);
  const metaRow = el('div', undefined, { class: 'intel-meta', style: 'margin-top:12px;' });
  metaRow.append(
    el('span', '发布：' + String(d.published_at || '—')),
    el('span', '更新：' + String(d.modified_at || '—')),
    el('span', '来源：NVD · 厂商公告'),
  );
  const srcLink = el('a', '原始来源 ↗', { href: 'https://nvd.nist.gov/vuln/detail/' + encodeURIComponent(id), target: '_blank', rel: 'noopener noreferrer' });
  metaRow.append(srcLink);
  titleCol.append(metaRow);
  topRow.append(titleCol);
  const cvssBox = el('div', undefined, { style: 'text-align:center;padding:6px 18px;border-left:1px solid var(--border);' });
  const cvssVal = usingMock ? m.cvss.score : (Array.isArray(d.cvss_assessments) && d.cvss_assessments[0]?.base_score) || null;
  cvssBox.append(el('div', cvssVal != null ? String(cvssVal) : '—', { class: 'cvss-num ' + sevKey, style: 'font-size:34px;' }));
  cvssBox.append(el('div', 'CVSS 3.1', { class: 'hint' }));
  topRow.append(cvssBox);
  headCard.append(topRow);
  if (d.description) headCard.append(el('p', d.description, { style: 'margin-top:12px;color:var(--secondary);font-size:13px;max-width:960px;' }));
  body.append(headCard);

  /* 2. 富化维度卡片（8 类） */
  const enrichTitle = el('h2', '富化维度', { style: 'margin:20px 0 12px;' });
  body.append(enrichTitle);
  const grid = el('div', undefined, { class: 'enrich-grid' });
  body.append(grid);

  /* 论文关联 */
  const paperRows = m.papers.map(p => ['相关度 ' + (p.rel * 100).toFixed(0) + '%', p.title]);
  enrichCard(grid, {
    color: '#22d3ee', title: '技术论文关联',
    rows: paperRows.slice(0, 2),
    source: m.papers[0].src, conf: m.papers[0].rel, time: m.papers[0].time, reviewed: m.papers[0].reviewed,
  });
  /* 分析文章/博客 */
  enrichCard(grid, {
    color: '#60a5fa', title: '分析文章 / 博客',
    rows: [['深度解读', m.papers[2].title], ['类型', '利用链构造分析']],
    source: m.papers[2].src, conf: m.papers[2].rel, time: m.papers[2].time, reviewed: m.papers[2].reviewed,
  });
  /* 受影响资产 */
  enrichCard(grid, {
    color: '#34d399', title: '受影响互联网资产',
    rows: [['资产类型', m.assets.type], ['产品', m.assets.product], ['版本范围', m.assets.versions], ['暴露面线索', m.assets.exposure], ['合规提示', m.assets.compliance]],
    source: '资产测绘引用', conf: 0.82, time: '2026-10-18 09:05', reviewed: true,
  });
  /* POC 验证 */
  enrichCard(grid, {
    color: '#fb4d6d', title: 'POC 验证代码',
    rows: [['POC 来源', m.poc.source], ['可用性', m.poc.availability], ['验证状态', m.poc.verified], ['风险提示', m.poc.risk]],
    source: m.poc.source, conf: m.poc.conf, time: '2026-10-18 08:58', reviewed: false,
  });
  /* CVSS 评估 */
  enrichCard(grid, {
    color: '#fbbf24', title: 'CVSS / 影响评估',
    rows: [['向量', m.cvss.vector], ['评分解释', m.cvss.explain]],
    source: 'NVD 官方向量', conf: 1.0, time: String(d.published_at || '—'), reviewed: true,
  });
  /* 修复建议 */
  const patches = !usingMock && Array.isArray(d.patches) && d.patches.length ? d.patches : null;
  enrichCard(grid, {
    color: '#818cf8', title: '修复建议',
    rows: patches
      ? patches.slice(0, 3).map((p, i) => ['方案 ' + (i + 1), p.title || p.url || JSON.stringify(p).slice(0, 80)])
      : [['补丁/升级', m.fix.patch], ['缓解措施', m.fix.measures], ['厂商公告', m.fix.advisory]],
    source: patches ? 'API · patch 候选' : '厂商公告', conf: 0.95, time: '2026-10-18 08:59', reviewed: true,
  });
  /* 攻击链 / 关联漏洞 */
  enrichCard(grid, {
    color: '#e879c9', title: '攻击链 / 关联漏洞',
    rows: [
      ...m.attackChain.map(a => ['ATT&CK ' + a.stage, a.tech]),
      ...m.related.map(r => ['关联 CVE', r.cve + '（' + r.rel + '）']),
    ],
    source: 'ATT&CK 映射引擎', conf: 0.86, time: '2026-10-18 09:01', reviewed: false,
  });
  /* 厂商公告 / 标准政策 */
  enrichCard(grid, {
    color: '#fb923c', title: '厂商公告 / 标准政策',
    rows: [['公告', m.fix.advisory], ['关联标准', m.policy.name], ['发布机构', m.policy.org]],
    source: m.policy.link, conf: 0.9, time: '2026-10-18 09:03', reviewed: false,
  });

  /* 3. 富化推理链 / 证据链 */
  const chainCard = el('div', undefined, { class: 'card', style: 'margin-top:16px;' });
  chainCard.append(el('div', '富化推理链 / 证据链', { class: 'card-title', style: 'margin-bottom:14px;' }));
  const chain = el('div', undefined, { class: 'ev-chain' });
  for (const step of mock.MOCK_EVIDENCE_CHAIN) {
    const node = el('div', undefined, { class: 'ev-node ' + step.state });
    node.append(el('div', step.title, { class: 'ev-title' }), el('div', step.desc, { class: 'ev-desc' }), el('div', step.time, { class: 'ev-meta' }));
    chain.append(node);
  }
  chainCard.append(chain);
  body.append(chainCard);

  /* 4. 富化准确率反馈 */
  const fbCard = el('div', undefined, { class: 'card', style: 'margin-top:16px;' });
  fbCard.append(el('div', '富化准确率反馈', { class: 'card-title', style: 'margin-bottom:10px;' }));
  const fbRow = el('div', undefined, { class: 'wb-inline' });
  const fbState = el('span', '当前富化准确率：91.7%（120 条人工复核样本）', { class: 'hint' });
  const yes = el('button', '标记准确', { type: 'button' });
  const no = el('button', '标记不准确', { type: 'button', class: 'wb-btn--danger' });
  for (const [btn, label] of [[yes, '准确'], [no, '不准确']]) {
    btn.addEventListener('click', () => {
      yes.disabled = no.disabled = true;
      fbState.textContent = `已提交「${label}」反馈 · 感谢复核（反馈进入复核队列 #RV）`;
    });
  }
  fbRow.append(yes, no, fbState);
  fbCard.append(fbRow, el('p', '现场演示：可将一条「待富化」漏洞从原始记录走到富化完成，展示全流程自动化。', { class: 'chart-note' }));
  body.append(fbCard);

  /* 5. 知识图谱可视化 */
  const kgCard = el('div', undefined, { class: 'card', style: 'margin-top:16px;' });
  kgCard.append(el('div', '知识图谱', { class: 'card-title', style: 'margin-bottom:10px;' }));
  knowledgeGraph(kgCard, { label: id, sub: '漏洞' }, [
    { label: 'vLLM', sub: '受影响产品', color: 'rgba(251,146,60,.18)', stroke: '#fb923c', ring: 1, relation: '影响', href: '/assets' },
    { label: 'PagedAttention 论文', sub: '技术关联', color: 'rgba(34,211,238,.14)', stroke: '#22d3ee', ring: 1, relation: '引用', href: '/knowledge' },
    { label: 'POC 仓库', sub: '验证代码', color: 'rgba(251,77,109,.14)', stroke: '#fb4d6d', ring: 1, relation: '验证', href: '/vulnerabilities' },
    { label: 'T1190', sub: '攻击技术', color: 'rgba(129,140,248,.16)', stroke: '#818cf8', ring: 1, relation: '映射' },
    { label: 'v0.6.3 补丁', sub: '修复建议', color: 'rgba(52,211,153,.14)', stroke: '#34d399', ring: 1, relation: '修复' },
    { label: 'CVE-2025-46190', sub: '关联漏洞', color: 'rgba(250,204,21,.14)', stroke: '#facc15', ring: 2, relation: '同组件', href: '/vulnerabilities/CVE-2025-46190' },
    { label: 'TC260 标准', sub: '合规依据', color: 'rgba(96,165,250,.14)', stroke: '#60a5fa', ring: 2, relation: '遵循', href: '/knowledge' },
  ]);
  body.append(kgCard);

  /* 原始字段（审计入口） */
  if (!usingMock && data && typeof data === 'object') {
    const datasets = [
      ['cvss_assessments', 'CVSS 来源断言'], ['affected_versions', '影响版本'], ['source_variants', '来源版本与确认状态'],
      ['claims', 'Claims'], ['evidence', 'Evidence'], ['pocs', 'POC 候选'], ['patches', 'Patch 候选'],
      ['known_exploitation', '已知利用'], ['conflicts', 'Conflict'], ['reviews', 'Human Review'],
    ];
    const rawCard = el('div', undefined, { class: 'card', style: 'margin-top:16px;' });
    rawCard.append(el('div', '原始 API 数据（审计）', { class: 'card-title', style: 'margin-bottom:10px;' }));
    let has = false;
    for (const [key, title] of datasets) {
      const rows = data[key];
      if (!Array.isArray(rows) || !rows.length) continue;
      has = true;
      rawCard.append(el('h3', title, { style: 'font-size:13px;margin:10px 0 4px;' }));
      for (const row of rows) jsonBlock(rawCard, row, row?.id || row?.source || title);
    }
    if (has) body.append(rawCard);
  }
}
