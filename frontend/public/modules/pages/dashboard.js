import { el, link, metricCard, statusChip, onFail, badge, severityBadge, pageHead, svgLineChart } from '../components.js';

/* 按严重度排序：critical > high > medium > low，同级按更新时间降序 */
const RANK = { critical: 5, high: 4, medium: 3, low: 2, info: 1, unknown: 0 };

/* 分页拉取漏洞列表（每页100，最多4页），用于前端聚合趋势与重点风险 */
async function fetchVulnBatch(api, signal) {
  const rows = [];
  let total = 0;
  for (let offset = 0; offset < 400; offset += 100) {
    const data = await api.vulnerabilitiesPage(signal, { offset, limit: 100, sort: 'modified_desc' });
    total = data.total ?? 0;
    rows.push(...(data.items || []));
    if (rows.length >= total || (data.items || []).length < 100) break;
  }
  return { rows, total };
}

export async function dashboard(view, { api, signal }) {
  const head = pageHead(view, '情报总览', '先看变化与影响，再判断证据是否充分。');
  const actions = el('div', undefined, { class: 'page-actions' });
  const refresh = el('button', '刷新', { type: 'button' });
  refresh.addEventListener('click', () => window.dispatchEvent(new PopStateEvent('popstate')));
  actions.append(refresh);
  head.append(actions);

  /* 服务状态：状态标签（原样展示后端返回值） */
  const chips = el('div', undefined, { class: 'status-chips' });
  view.append(chips);
  api.health(signal).then(data => {
    statusChip(chips, '应用', data.application);
    statusChip(chips, '数据库', data.database);
    statusChip(chips, '范围', data.scope);
  }).catch(onFail(() => statusChip(chips, '状态', '读取失败')));

  /* 4 张关键指标卡（带口径副标签，点击进入对应页面） */
  const grid = el('div', undefined, { class: 'metric-grid' });
  view.append(grid);
  const vulnCard = metricCard(grid, { icon: 'vulns', label: '漏洞记录', tone: '', note: '列表总数 · 未过滤', href: '/vulnerabilities' });
  const critCard = metricCard(grid, { icon: 'critical', label: '严重 / 高', tone: 'danger', note: '按漏洞-组件对计数', href: '/assets' });
  const pocCard = metricCard(grid, { icon: 'poc', label: '已确认 POC', tone: 'warn', note: '关联已确认 · 可用性未评估', href: '/assets' });
  const reviewCard = metricCard(grid, { icon: 'reviews', label: '待复核', tone: 'review', note: '复核记录 · 排除资产匹配复核', href: '/reviews' });

  api.overview(signal).then(data => {
    critCard.val.textContent = data.critical_high ?? '—';
    pocCard.val.textContent = data.confirmed_poc ?? '—';
    if (data.counts_unit) critCard.card.title = String(data.counts_unit);
  }).catch(onFail(() => { critCard.val.textContent = '×'; pocCard.val.textContent = '×'; }));
  api.reviews(signal).then(data => {
    reviewCard.val.textContent = data.total ?? '—';
  }).catch(onFail(() => { reviewCard.val.textContent = '×'; }));

  /* 双栏：左侧重点风险列表 + 右侧趋势图与组件匹配 */
  const twoCol = el('div', undefined, { class: 'two-col' });
  view.append(twoCol);
  const mainCol = el('div', undefined, { class: 'two-col-main' });
  const sideCol = el('div', undefined, { class: 'two-col-side' });
  twoCol.append(mainCol, sideCol);

  /* 值得关注的风险：严重度优先排序取前 6 */
  const riskSection = el('section');
  riskSection.append(el('h2', '值得关注的 AI 组件风险'));
  riskSection.append(el('p', '按严重度与最近更新排序', { class: 'panel-caption' }));
  const riskBody = el('div', undefined, { class: 'intel-list' });
  riskSection.append(riskBody);
  riskSection.append(el('p', undefined, { class: 'panel-foot' }));
  riskSection.lastChild.append(link('查看全部漏洞', '/vulnerabilities'));
  mainCol.append(riskSection);

  /* 近期变化：新增漏洞趋势（原生 SVG 折线图，无依赖） */
  const trendSection = el('section');
  trendSection.append(el('h2', '近期变化'));
  const trendBody = el('div', undefined, { class: 'panel-body' });
  trendSection.append(trendBody);
  sideCol.append(trendSection);

  /* 组件匹配概况（口径来自 /assets/overview，不美化） */
  const matchSection = el('section');
  matchSection.append(el('h2', '组件匹配概况'));
  const matchBody = el('div', undefined, { class: 'panel-body' });
  matchSection.append(matchBody);
  matchSection.append(el('p', undefined, { class: 'panel-foot' }));
  matchSection.lastChild.append(link('查看资产风险', '/assets'));
  sideCol.append(matchSection);

  fetchVulnBatch(api, signal).then(({ rows, total }) => {
    if (signal.aborted) return;
    vulnCard.val.textContent = total ?? '—';
    /* 重点风险列表 */
    const sorted = [...rows].sort((a, b) => (RANK[String(b.primary_severity).toLowerCase()] ?? 0) - (RANK[String(a.primary_severity).toLowerCase()] ?? 0) || String(b.modified_at || '').localeCompare(String(a.modified_at || '')));
    riskBody.replaceChildren();
    if (!sorted.length) riskBody.append(el('p', '暂无漏洞记录', { class: 'message', 'data-state': 'empty' }));
    for (const row of sorted.slice(0, 6)) {
      const item = el('div', undefined, { class: 'intel-item' });
      const info = el('div', undefined, { class: 'intel-info' });
      info.append(link(row.canonical_id || row.id, '/vulnerabilities/' + encodeURIComponent(row.canonical_id || row.id)));
      info.append(el('span', row.title, { class: 'intel-title' }));
      const meta = el('div', undefined, { class: 'intel-meta' });
      meta.append(el('span', (row.published_at || '公布时间未提供') + ' · 更新 ' + (row.modified_at || '—')));
      info.append(meta);
      const right = el('div', undefined, { class: 'intel-right' });
      severityBadge(right, row.primary_severity);
      badge(right, row.status || 'unknown', 'neutral');
      item.append(info, right);
      riskBody.append(item);
    }
    /* 趋势图：按 published_at 聚合每日新增（最近 14 天有数据的日期） */
    const counts = new Map();
    let missingDate = 0;
    for (const row of rows) {
      if (!row.published_at) { missingDate++; continue; }
      const day = String(row.published_at).slice(0, 10);
      counts.set(day, (counts.get(day) || 0) + 1);
    }
    const days = [...counts.keys()].sort().slice(-14);
    trendBody.replaceChildren();
    if (days.length < 2) {
      trendBody.append(el('p', '暂无足够带公布时间的记录，无法绘制趋势（不伪造数据）', { class: 'message', 'data-state': 'empty' }));
    } else {
      svgLineChart(trendBody, days.map(day => ({ label: day.slice(5), value: counts.get(day) })), { ariaLabel: '按公布日期聚合的新增漏洞趋势（最近14个有记录的日期）', valueUnit: ' 条' });
      const note = el('p', '按 published_at 前端聚合，仅覆盖列表分页拉取的记录' + (missingDate ? `；${missingDate} 条无公布时间未计入` : ''), { class: 'chart-note' });
      trendBody.append(note);
    }
  }).catch(onFail(error => {
    vulnCard.val.textContent = '×';
    riskBody.append(el('p', '风险列表读取失败：' + error.message, { class: 'message', 'data-state': 'error' }));
    trendBody.append(el('p', '趋势数据读取失败', { class: 'message', 'data-state': 'error' }));
  }));

  api.overview(signal).then(data => {
    if (signal.aborted) return;
    matchBody.replaceChildren();
    const summary = el('div', undefined, { class: 'match-summary' });
    summary.append(el('span', (data.assets ?? '—') + ' 资产 · ' + (data.components ?? '—') + ' 组件'));
    matchBody.append(summary);
    const rows = [
      ['受影响组件', data.affected_components, 'danger'],
      ['严重 / 高', data.critical_high, 'danger'],
      ['已确认 POC', data.confirmed_poc, 'warn'],
      ['KEV', data.kev, 'danger'],
      ['有补丁', data.patch_available, 'ok'],
      ['不确定匹配', data.uncertain_matches, 'review'],
    ];
    const list = el('div', undefined, { class: 'match-list' });
    for (const [label, value, tone] of rows) {
      const item = el('div', undefined, { class: 'match-item' });
      item.append(el('span', label));
      const right = el('span', undefined, { class: 'match-value' });
      right.textContent = value ?? '—';
      item.append(right);
      item.dataset.tone = tone;
      list.append(item);
    }
    matchBody.append(list);
    const notes = [];
    if (data.not_evaluated_components != null) notes.push('未评估组件：' + data.not_evaluated_components);
    if (data.is_demo_inventory_included) notes.push('含演示库存');
    if (data.counts_unit) notes.push(String(data.counts_unit));
    if (notes.length) matchBody.append(el('p', notes.join(' · '), { class: 'chart-note' }));
  }).catch(onFail(() => matchBody.append(el('p', '概况读取失败', { class: 'message', 'data-state': 'error' }))));

  /* 来源更新：数据源状态灯 + 最近成功时间 */
  const strip = el('section', undefined, { class: 'health-strip' });
  strip.append(el('h2', '来源更新'));
  const stripBody = el('div', undefined, { class: 'health-items' });
  strip.append(stripBody);
  strip.append(el('p', undefined, { class: 'panel-foot' }));
  strip.lastChild.append(link('查看系统页', '/system'));
  view.append(strip);
  api.sources(signal).then(data => {
    if (signal.aborted) return;
    for (const row of (data.items || []).slice(0, 8)) {
      const item = el('div', undefined, { class: 'health-item' });
      item.dataset.state = String(row.status);
      const name = el('strong', row.source_key);
      item.append(name);
      item.append(el('span', (row.last_success_at ? '最近成功 ' + String(row.last_success_at).replace('T', ' ').slice(0, 16) : '尚无成功记录'), { class: 'health-time' }));
      stripBody.append(item);
    }
    if (!stripBody.childNodes.length) stripBody.append(el('p', '暂无数据源记录', { class: 'message', 'data-state': 'empty' }));
  }).catch(onFail(() => stripBody.append(el('p', '来源状态读取失败', { class: 'message', 'data-state': 'error' }))));
}
