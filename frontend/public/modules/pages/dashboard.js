import { el, link, badge, pageHead, onFail } from '../components.js';
import { lineChart, donutChart, pipelineFlow, sparkline } from '../charts.js';
import * as mock from '../mock-data.js';

/* 总览驾驶舱：一屏证明系统完整性。
   有后端数据的指标（漏洞总数、来源数、最近情报）以 API 为准；
   后端尚无口径的指标（富化准确率、问答指标、Agent 指标）使用演示数据并在页脚注明。 */

function kpi(parent, { label, value, unit = '', tone = '', delta, spark, sparkColor, href }) {
  const card = href
    ? el('a', undefined, { class: 'kpi-card', href, 'data-route': '' })
    : el('div', undefined, { class: 'kpi-card' });
  if (tone) card.dataset.tone = tone;
  card.append(el('div', label, { class: 'kpi-label' }));
  const val = el('div', undefined, { class: 'kpi-value' });
  val.append(String(value ?? '…'));
  if (unit) val.append(el('small', unit));
  card.append(val);
  if (delta) {
    const d = el('div', undefined, { class: 'kpi-delta' });
    d.innerHTML = delta;
    card.append(d);
  }
  if (spark?.length) {
    const holder = el('div', undefined, { style: 'margin-top:8px;' });
    sparkline(holder, spark, { color: sparkColor || '#22d3ee' });
    card.append(holder);
  }
  parent.append(card);
  return { card, val };
}

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

const SEV_LABEL = { critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息', unknown: '未知' };

function feedItem(f) {
  const item = el('div', undefined, { class: 'feed-item' });
  item.append(el('i', undefined, { class: 'feed-sev ' + (f.severity || 'unknown') }));
  const main = el('div', undefined, { class: 'feed-main' });
  const title = link(`${f.cve} · ${f.title}`, '/vulnerabilities/' + encodeURIComponent(f.cve));
  title.classList.add('feed-title');
  main.append(title);
  const meta = el('div', undefined, { class: 'feed-meta' });
  meta.append(
    el('span', '来源 ' + f.source),
    el('span', '发布 ' + f.published),
    el('span', '采集 ' + f.collected),
  );
  const cls = el('span', f.cls, { class: 'tag' });
  meta.append(cls);
  main.append(meta);
  const right = el('div', undefined, { class: 'feed-right' });
  right.append(el('span', f.cvss?.toFixed ? f.cvss.toFixed(1) : '—', { class: 'cvss-num ' + (f.severity || 'unknown') }));
  badge(right, f.enrich, f.enrich === '已富化' ? 'ok' : f.enrich === '富化中' ? 'info' : 'neutral');
  item.append(main, right);
  return item;
}

export async function dashboard(view, { api, signal }) {
  const head = pageHead(view, '总览驾驶舱', 'AI 安全情报全流程一屏总览：采集 → 清洗去重 → 分类 → 富化 → 入库 → 索引 → 问答。');
  const actions = el('div', undefined, { class: 'page-actions' });
  const live = el('span', undefined, { class: 'tag ok' });
  live.append(el('i', undefined, { class: 'pulse-dot on' }), ' 实时监测中');
  const refresh = el('button', '刷新', { type: 'button' });
  refresh.addEventListener('click', () => window.dispatchEvent(new PopStateEvent('popstate')));
  actions.append(live, refresh);
  head.append(actions);

  /* 1. 核心指标卡 */
  const kpis = el('div', undefined, { class: 'kpi-grid' });
  view.append(kpis);
  const kSource = kpi(kpis, { label: '接入数据源', value: '9', unit: '个', delta: 'CVE/NVD · 社区 · 厂商 · 博客 · 论文 · 标准', href: '/intel' });
  const kNew = kpi(kpis, { label: '今日新增漏洞', value: '141', unit: '条', tone: '', delta: '<span class="up">▲ 12.8%</span> 较昨日', spark: mock.KPI_SPARKS.vulns, href: '/intel' });
  const kAi = kpi(kpis, { label: 'AI 相关漏洞', value: '38', unit: '条', tone: 'warn', delta: '<span class="up">▲ 5</span> 较昨日', spark: mock.KPI_SPARKS.ai, sparkColor: '#fb923c', href: '/vulnerabilities' });
  const kLatency = kpi(kpis, { label: '平均采集延迟', value: '3.2', unit: '小时', tone: 'ok', delta: '<span class="down">▼ 0.3h</span> 近 24h', spark: mock.KPI_SPARKS.latency, sparkColor: '#34d399' });
  kpi(kpis, { label: '富化覆盖率', value: '93.1', unit: '%', delta: '8 维度富化口径', spark: mock.KPI_SPARKS.enrich, sparkColor: '#818cf8' });
  kpi(kpis, { label: '富化准确率', value: '91.7', unit: '%', tone: 'accent', delta: '人工复核抽样口径', href: '/vulnerabilities' });
  kpi(kpis, { label: '知识库文档', value: '2,847', unit: '篇', delta: '向量片段 46,213', href: '/knowledge' });
  kpi(kpis, { label: 'Agent 成功率', value: '96.8', unit: '%', tone: 'ok', delta: '异常自愈 7 次 · 今日', href: '/agents' });

  /* 真实漏洞总数覆盖演示值 */
  api.vulnerabilitiesPage(signal, { limit: 1 }).then(data => {
    if (signal.aborted || data.total == null) return;
    kNew.val.textContent = String(data.total);
    kNew.val.append(el('small', ' 条（库内总量）'));
  }).catch(onFail(() => {}));

  /* 2. 自动化流水线状态 */
  const pipe = card(view, '系统自动化流水线', '采集 → 问答全链路节点状态');
  pipelineFlow(pipe.body, mock.PIPELINE_NODES);

  /* 3. 中部：趋势 + 风险分类 + 高危情报流 */
  const mid = el('div', undefined, { class: 'grid', style: 'grid-template-columns: 1.35fr 1fr; margin-top:16px;' });
  view.append(mid);

  const trend = card(mid, '采集时效趋势', '近 7 天 · 平均延迟 vs 采集量');
  lineChart(trend.body, [
    { label: '采集量', color: '#22d3ee', points: mock.COLLECT_TREND },
    { label: '平均延迟(×40h)', color: '#fbbf24', points: mock.LATENCY_TREND.map(p => ({ label: p.label, value: p.value * 40 })) },
  ], { ariaLabel: '近7天采集量与平均采集延迟趋势', height: 210 });
  trend.body.append(el('p', '黄线为平均延迟（按 ×40 缩放以便同屏对比）；延迟口径：漏洞发布时间 → 系统入库时间。', { class: 'chart-note' }));

  const donut = card(mid, 'AI 安全风险分类分布', '点击分类跳转漏洞列表');
  donutChart(donut.body, mock.AI_RISK_CLASSES.map(c => ({ ...c })), {
    centerLabel: 'AI 风险',
    onSelect: item => { location.href = '/vulnerabilities?cls=' + encodeURIComponent(item.label); },
  });

  /* 4. 数据源覆盖矩阵 + 高危情报流 */
  const low = el('div', undefined, { class: 'grid', style: 'grid-template-columns: 1.35fr 1fr; margin-top:16px;' });
  view.append(low);

  const matrix = card(low, '数据源覆盖矩阵', '按类型筛选 · 含增量/全量与最近采集');
  const filterRow = el('div', undefined, { style: 'display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;' });
  matrix.body.append(filterRow);
  const matrixGrid = el('div', undefined, { class: 'src-grid' });
  matrix.body.append(matrixGrid);

  function renderSources(items) {
    matrixGrid.replaceChildren();
    for (const s of items) {
      const c = el('div', undefined, { class: 'src-card' });
      const headRow = el('div', undefined, { class: 'src-head' });
      const name = el('div', undefined, { class: 'src-name' });
      name.append(el('i', undefined, { class: 'pulse-dot ' + (s.enabled ? 'on' : 'idle') }), s.name);
      headRow.append(name, el('span', s.type, { class: 'src-type' }));
      const meta = el('div', undefined, { class: 'src-meta' });
      meta.append(
        el('span', '频率 '), el('b', s.freq),
        el('span', '模式 '), el('b', s.incr ? '增量' : '全量'),
        el('span', '最近采集 '), el('b', String(s.last).slice(5, 16)),
        el('span', '状态 '), el('b', s.mode),
      );
      c.append(headRow, meta);
      matrixGrid.append(c);
    }
    if (!items.length) matrixGrid.append(el('p', '该类型暂无数据源', { class: 'message', 'data-state': 'empty' }));
  }
  let sourceItems = mock.MOCK_SOURCES;
  const types = ['全部', ...new Set(mock.MOCK_SOURCES.map(s => s.type))];
  types.forEach((t, i) => {
    const chip = el('button', t, { type: 'button', class: 'filter-chip', 'aria-pressed': String(i === 0) });
    chip.addEventListener('click', () => {
      filterRow.querySelectorAll('.filter-chip').forEach(c => c.setAttribute('aria-pressed', 'false'));
      chip.setAttribute('aria-pressed', 'true');
      renderSources(t === '全部' ? sourceItems : sourceItems.filter(s => s.type === t));
    });
    filterRow.append(chip);
  });
  renderSources(sourceItems);
  /* 有真实来源接口时叠加真实计数 */
  api.sources(signal).then(data => {
    if (signal.aborted || !Array.isArray(data.items) || !data.items.length) return;
    kSource.val.textContent = String(data.items.length);
    kSource.val.append(el('small', ' 个'));
  }).catch(onFail(() => {}));

  const feed = card(low, '最新高危情报流', '点击进入漏洞详情与富化证据链');
  const feedBox = el('div', undefined, { class: 'feed-scroll' });
  for (const f of mock.MOCK_FEED) feedBox.append(feedItem(f));
  feed.body.append(feedBox);
  const foot = el('div', undefined, { class: 'card-foot' });
  foot.append(link('查看全部情报 →', '/intel'));
  feed.card.append(foot);
  /* 真实漏洞流覆盖演示流 */
  api.vulnerabilitiesPage(signal, { limit: 8, sort: 'published_desc' }).then(data => {
    if (signal.aborted || !Array.isArray(data.items) || !data.items.length) return;
    feedBox.replaceChildren();
    for (const row of data.items) {
      feedBox.append(feedItem({
        cve: row.canonical_id || row.id, title: row.title || '（无标题）',
        severity: String(row.primary_severity || 'unknown').toLowerCase(),
        cvss: row.cvss_score ?? row.cvss, source: '平台库',
        published: String(row.published_at || '—').slice(0, 16),
        collected: String(row.modified_at || '—').slice(0, 16),
        enrich: row.status || '已入库', cls: '',
      }));
    }
  }).catch(onFail(() => {}));

  view.append(el('p', '标注说明：漏洞列表与来源状态来自后端 API；采集延迟、富化/问答/Agent 指标在后端接口就绪前展示演示口径（模拟数据）。', { class: 'chart-note', style: 'margin-top:14px;' }));
}
