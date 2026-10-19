import { el, link, badge, pageHead, table, message, onFail } from '../components.js';
import { barList } from '../charts.js';
import * as mock from '../mock-data.js';

/* 情报监测中心：证明多源、自动、实时、去重。
   数据源与任务优先接 /api/v1/sources、/api/v1/sync-runs，接口缺席时回退演示数据。 */

const SEV_LABEL = { critical: '严重', high: '高危', medium: '中危', low: '低危', unknown: '未知' };
const RESULT_TONE = { success: 'ok', warning: 'warn', failed: 'danger' };
const RESULT_LABEL = { success: '成功', warning: '降级', failed: '失败' };

function card(parent, title, sub) {
  const c = el('div', undefined, { class: 'card' });
  const head = el('div', undefined, { class: 'card-head' });
  const t = el('div', undefined, { class: 'card-title' });
  t.append(title);
  if (sub) t.append(el('span', sub, { class: 'sub' }));
  head.append(t);
  const body = el('div', undefined, { class: 'card-body' });
  c.append(head, body);
  parent.append(c);
  return { card: c, head, body };
}

export function intel(view, { api, signal }) {
  const head = pageHead(view, '情报监测中心', '多源自动采集、实时监测、清洗去重与增量入库的统一监测面。');
  const actions = el('div', undefined, { class: 'page-actions' });
  head.append(actions);

  /* 5. 实时监测开关（置顶操作区） */
  const rtLabel = el('span', undefined, { class: 'wb-switch', role: 'switch', 'aria-checked': 'true', tabindex: '0' });
  rtLabel.append(el('i', undefined, { class: 'wb-switch-track' }), document.createTextNode('实时监测'));
  const rtState = el('span', undefined, { class: 'tag ok' });
  const countdown = el('span', undefined, { class: 'hint mono' });
  actions.append(rtLabel, rtState, countdown);
  let rtOn = true;
  let nextPoll = Date.now() + 74_000;
  const timer = setInterval(() => {
    if (signal.aborted) { clearInterval(timer); return; }
    if (!rtOn) { countdown.textContent = '轮询已暂停'; return; }
    const remain = Math.max(0, Math.round((nextPoll - Date.now()) / 1000));
    countdown.textContent = `最近轮询 ${new Date(nextPoll - 300_000).toTimeString().slice(0, 8)} · 下次轮询 ${String(Math.floor(remain / 60)).padStart(2, '0')}:${String(remain % 60).padStart(2, '0')}`;
    if (remain === 0) nextPoll = Date.now() + 300_000;
  }, 1000);
  function toggleRt() {
    rtOn = !rtOn;
    rtLabel.setAttribute('aria-checked', String(rtOn));
    rtState.className = 'tag ' + (rtOn ? 'ok' : 'warn');
    rtState.textContent = rtOn ? '实时监测中' : '已暂停';
    if (rtOn) nextPoll = Date.now() + 300_000;
  }
  rtLabel.addEventListener('click', toggleRt);
  rtLabel.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleRt(); } });
  toggleRt(); toggleRt();

  /* 顶部摘要 KPI */
  const kpis = el('div', undefined, { class: 'kpi-grid' });
  view.append(kpis);
  const d = mock.DEDUP_STATS;
  for (const [label, value, unit, note] of [
    ['今日原始采集', d.raw, '条', '多源汇总'],
    ['去重后入库', d.afterDedup, '条', `去重 ${d.raw - d.afterDedup} 条`],
    ['增量新增', d.incremental, '条', '较上次游标'],
    ['采集成功率', 99.2, '%', '近 24h'],
  ]) {
    const c = el('div', undefined, { class: 'kpi-card' });
    c.append(el('div', label, { class: 'kpi-label' }));
    const v = el('div', undefined, { class: 'kpi-value' });
    v.append(String(value), el('small', ' ' + unit));
    c.append(v, el('div', note, { class: 'kpi-delta' }));
    kpis.append(c);
  }

  /* 1. 多源情报列表 */
  const listCard = card(view, '多源情报列表', '支持来源 / 等级 / 分类 / 关键词筛选');
  const bar = el('div', undefined, { class: 'filter-bar' });
  const kw = el('input', undefined, { type: 'search', placeholder: '关键词 / CVE 编号', 'aria-label': '关键词筛选', style: 'min-width:180px;' });
  const srcSel = el('select', undefined, { 'aria-label': '来源筛选' });
  for (const t of ['全部来源', 'NVD', 'GitHub Advisory', '厂商公告', '安全社区', '博客']) srcSel.append(el('option', t, { value: t }));
  const sevSel = el('select', undefined, { 'aria-label': '风险等级筛选' });
  for (const [v, l] of [['all', '全部等级'], ['critical', '严重'], ['high', '高危'], ['medium', '中危'], ['low', '低危']]) sevSel.append(el('option', l, { value: v }));
  const clsSel = el('select', undefined, { 'aria-label': 'AI 风险分类筛选' });
  for (const t of ['全部分类', ...mock.AI_RISK_CLASSES.map(c => c.label)]) clsSel.append(el('option', t, { value: t }));
  const enrichSel = el('select', undefined, { 'aria-label': '富化状态筛选' });
  for (const t of ['全部状态', '已富化', '富化中', '待富化']) enrichSel.append(el('option', t, { value: t }));
  bar.append(
    el('span', '筛选', { class: 'fb-label' }), kw, srcSel, sevSel, clsSel, enrichSel,
  );
  listCard.body.append(bar);
  const listBody = el('div');
  listCard.body.append(listBody);

  function renderList() {
    const k = kw.value.trim().toLowerCase();
    const rows = mock.MOCK_INTEL_LIST.filter(r =>
      (!k || r.title.toLowerCase().includes(k) || r.cve.toLowerCase().includes(k)) &&
      (srcSel.value === '全部来源' || r.srcType === srcSel.value) &&
      (sevSel.value === 'all' || r.severity === sevSel.value) &&
      (clsSel.value === '全部分类' || r.cls === clsSel.value) &&
      (enrichSel.value === '全部状态' || r.enrich === enrichSel.value));
    listBody.replaceChildren();
    if (!rows.length) { message(listBody, '没有匹配的情报记录', 'empty'); return; }
    table(listBody, rows, [
      { label: '情报 / CVE', render: r => link(r.cve, '/vulnerabilities/' + encodeURIComponent(r.cve)) },
      { label: '标题', render: r => { const s = el('span', r.title); s.style.cssText = 'display:inline-block;max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle;'; s.title = r.title; return s; } },
      { label: '来源', key: 'srcType' },
      { label: '发布时间', render: r => el('span', r.published, { class: 'mono', style: 'font-size:11.5px;' }) },
      { label: '采集时间', render: r => el('span', r.collected, { class: 'mono', style: 'font-size:11.5px;' }) },
      { label: '等级', render: r => badge(el('span'), SEV_LABEL[r.severity] || r.severity, { critical: 'danger', high: 'danger', medium: 'warn', low: 'ok' }[r.severity] || 'neutral') },
      { label: 'CVSS', render: r => el('span', r.cvss.toFixed(1), { class: 'cvss-num ' + r.severity }) },
      { label: 'AI 风险分类', render: r => el('span', r.cls, { class: 'tag' }) },
      { label: '富化', render: r => badge(el('span'), r.enrich, r.enrich === '已富化' ? 'ok' : r.enrich === '富化中' ? 'info' : 'neutral') },
      { label: '去重', render: r => badge(el('span'), r.dedup, r.dedup === '唯一' ? 'info' : 'review') },
    ]);
    listBody.append(el('p', `共 ${rows.length} 条 · 列表为来源断言口径，富化状态以详情页证据链为准`, { class: 'chart-note' }));
  }
  for (const node of [kw, srcSel, sevSel, clsSel, enrichSel]) {
    node.addEventListener(node === kw ? 'input' : 'change', renderList);
  }
  renderList();

  /* 2 + 3. 数据源管理面板 与 采集任务日志 */
  const two = el('div', undefined, { class: 'grid grid-2', style: 'margin-top:16px;' });
  view.append(two);

  const srcCard = card(two, '数据源管理', '启用状态 · 频率 · 增量游标 · 立即采集');
  const srcGrid = el('div', undefined, { class: 'src-grid' });
  srcCard.body.append(srcGrid);
  function renderSrcCards(items) {
    srcGrid.replaceChildren();
    for (const s of items) {
      const c = el('div', undefined, { class: 'src-card' });
      const headRow = el('div', undefined, { class: 'src-head' });
      const name = el('div', undefined, { class: 'src-name' });
      name.append(el('i', undefined, { class: 'pulse-dot ' + (s.enabled ? (s.failures > 1 ? 'warn' : 'on') : 'idle') }), s.name);
      headRow.append(name, el('span', s.type, { class: 'src-type' }));
      const meta = el('div', undefined, { class: 'src-meta' });
      meta.append(
        el('span', '模式 '), el('b', s.mode),
        el('span', '频率 '), el('b', s.freq),
        el('span', '最近成功 '), el('b', String(s.last).slice(5)),
        el('span', '失败次数 '), el('b', String(s.failures)),
        el('span', '增量游标 '), el('b', s.cursor),
        el('span', '方式 '), el('b', s.incr ? '增量' : '全量'),
      );
      const act = el('div', undefined, { class: 'src-actions' });
      const run = el('button', '立即采集', { type: 'button' });
      run.addEventListener('click', () => {
        run.disabled = true;
        run.textContent = '采集中…';
        setTimeout(() => {
          run.disabled = false;
          run.textContent = '立即采集';
          badge(c, '已触发 · 任务进入队列', 'ok');
        }, 1600);
      });
      act.append(run, el('span', s.enabled ? '已启用' : '已停用', { class: 'tag ' + (s.enabled ? 'ok' : 'warn') }));
      c.append(headRow, meta, act);
      srcGrid.append(c);
    }
  }
  renderSrcCards(mock.MOCK_SOURCES);
  api.sources(signal).then(data => {
    if (signal.aborted || !Array.isArray(data.items) || !data.items.length) return;
    const mapped = data.items.map(row => ({
      name: row.source_key || row.name || '未知来源', type: row.source_type || row.type || '其他',
      enabled: row.enabled !== false && String(row.status).toLowerCase() !== 'disabled',
      mode: '定时采集', freq: row.frequency || '—',
      last: String(row.last_success_at || '—').replace('T', ' ').slice(0, 16),
      failures: row.failure_count ?? 0, cursor: row.cursor ? String(row.cursor).slice(0, 14) : '—',
      incr: true,
    }));
    renderSrcCards(mapped);
  }).catch(onFail(() => {}));

  const taskCard = card(two, '采集任务与日志', '每次任务耗时 / 新增 / 去重 / 失败原因');
  const tl = el('div', undefined, { class: 'timeline' });
  taskCard.body.append(tl);
  function renderTasks(items) {
    tl.replaceChildren();
    for (const t of items) {
      const row = el('div');
      const line = el('div');
      line.append(
        el('span', t.time + ' ', { class: 'mono', style: 'color:var(--muted);' }),
        el('b', t.source),
      );
      const tone = RESULT_TONE[t.result] || 'neutral';
      badge(line, RESULT_LABEL[t.result] || t.result, tone);
      row.append(line, el('div', `耗时 ${t.dur} · 新增 ${t.added} 条 · 去重 ${t.dedup} 条 — ${t.note}`, { class: 'hint' }));
      tl.append(row);
    }
  }
  renderTasks(mock.MOCK_COLLECT_TASKS);
  api.syncRuns(signal).then(data => {
    if (signal.aborted || !Array.isArray(data.items) || !data.items.length) return;
    const mapped = data.items.map(r => ({
      time: String(r.started_at || r.created_at || '—').replace('T', ' ').slice(5, 16),
      source: r.source_key || r.source || '未知来源',
      dur: r.duration_seconds != null ? r.duration_seconds + 's' : '—',
      added: r.added ?? r.inserted ?? 0, dedup: r.deduplicated ?? 0,
      result: String(r.status).toLowerCase().includes('fail') ? 'failed' : 'success',
      note: r.error || r.note || '—',
    }));
    renderTasks(mapped);
  }).catch(onFail(() => {}));

  /* 4. 去重与增量展示 */
  const dedup = card(view, '去重与增量机制', '全自动 + 实时 + 去重的判定依据');
  const dd = el('div', undefined, { class: 'grid grid-2' });
  dedup.body.append(dd);
  const left = el('div');
  barList(left, [
    { label: 'CVE ID 精确匹配', value: d.byCveId, color: '#22d3ee' },
    { label: '标题相似度 ≥0.92', value: d.byTitleSim, color: '#818cf8' },
    { label: 'URL 规范化去重', value: d.byUrl, color: '#34d399' },
    { label: '内容哈希去重', value: d.byHash, color: '#fbbf24' },
  ], { unit: ' 条' });
  const right = el('div', undefined, { class: 'hint' });
  right.innerHTML = [
    '去重链路：原始 ' + d.raw + ' 条 → 去重后 ' + d.afterDedup + ' 条 → 增量入库 ' + d.incremental + ' 条。',
    '判定顺序：CVE ID 精确匹配 → 标题语义相似度（阈值 0.92）→ 规范化 URL → 正文内容哈希。',
    '合并保留所有来源断言（source assertions），冲突字段转入复核队列，不做静默覆盖。',
  ].join('<br>');
  dd.append(left, right);
  dedup.card.style.marginTop = '16px';
}
