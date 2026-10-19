import { el, badge, pageHead, statusChip, table, load, jsonBlock, onFail, tabBar } from '../components.js';
import { lineChart, barList } from '../charts.js';
import * as mock from '../mock-data.js';

/* 系统运维与性能监控：服务健康、延迟趋势、质量指标、告警、容器、部署、日志。
   /health、/api/v1/sources、/api/v1/sync-runs 为真实接口，其余为演示口径。 */

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

export function system(view, { api, signal }) {
  const head = pageHead(view, '系统运维与性能监控', '服务健康、采集/富化/问答质量指标、异常告警、容器与部署记录。');
  const actions = el('div', undefined, { class: 'page-actions' });
  const chips = el('div', undefined, { class: 'status-chips', style: 'margin:0;' });
  actions.append(chips);
  head.append(actions);
  api.health(signal).then(data => {
    statusChip(chips, '应用', data.application);
    statusChip(chips, '数据库', data.database);
    statusChip(chips, '范围', data.scope);
  }).catch(onFail(() => statusChip(chips, '状态', '读取失败')));

  /* 1. 服务健康状态 */
  const svcCard = card(view, '服务健康状态', '采集 / 富化 / 问答 / 向量库 / 数据库 / LLM 网关');
  const svcGrid = el('div', undefined, { class: 'svc-grid' });
  for (const s of mock.MOCK_SERVICES) {
    const item = el('div', undefined, { class: 'svc-item' });
    item.append(el('i', undefined, { class: 'pulse-dot ' + s.state }));
    const col = el('div');
    col.append(el('div', s.name, { class: 'svc-name' }), el('div', s.sub, { class: 'svc-sub' }), el('div', s.note, { class: 'hint' }));
    item.append(col);
    svcGrid.append(item);
  }
  svcCard.body.append(svcGrid);

  /* 2. 质量指标 KPI */
  const m = mock.OPS_METRICS;
  const kpis = el('div', undefined, { class: 'kpi-grid', style: 'margin-top:16px;' });
  view.append(kpis);
  for (const [label, value, note] of [
    ['采集延迟 P50 / P95', m.collectLatencyP50 + ' / ' + m.collectLatencyP95, '发布时间 → 入库'],
    ['富化准确率 / 召回率', m.enrichPrecision + ' / ' + m.enrichRecall, '人工复核抽样'],
    ['问答准确率', m.qaAccuracy, '120 题评测集'],
    ['问答响应 P95', m.qaP95, '端到端'],
    ['Agent 任务成功率', m.agentSuccess, '近 24h'],
    ['平台可用性', m.uptime, '近 30 天'],
  ]) {
    const c = el('div', undefined, { class: 'kpi-card' });
    c.append(el('div', label, { class: 'kpi-label' }));
    c.append(el('div', value, { class: 'kpi-value', style: 'font-size:19px;' }), el('div', note, { class: 'kpi-delta' }));
    kpis.append(c);
  }

  /* 3. 趋势 + 告警 双栏 */
  const two = el('div', undefined, { class: 'grid grid-2', style: 'margin-top:16px;' });
  view.append(two);
  const trend = card(two, '采集延迟趋势', '近 7 天平均延迟（小时）');
  lineChart(trend.body, [{ label: '平均延迟', color: '#fbbf24', points: mock.LATENCY_TREND }], { ariaLabel: '近7天平均采集延迟趋势', unit: 'h', height: 180 });
  const alerts = card(two, '异常告警', '自动处理记录见 Agent 编排中心');
  const alertList = el('div', undefined, { class: 'alert-list' });
  for (const a of mock.MOCK_ALERTS) {
    const item = el('div', undefined, { class: 'alert-item ' + a.level });
    item.append(el('span', a.time, { class: 'alert-time' }), el('span', a.text));
    alertList.append(item);
  }
  alerts.body.append(alertList);

  /* 4. 容器 / 部署 / 真实来源 三栏 */
  const three = el('div', undefined, { class: 'grid grid-3', style: 'margin-top:16px;' });
  view.append(three);

  const dockerCard = card(three, '容器运行状态', 'docker-compose 编排');
  const dk = el('div', undefined, { class: 'tool-log' });
  for (const s of mock.MOCK_SERVICES) {
    const row = el('div', undefined, { class: 'tool-row', style: 'grid-template-columns:1fr auto auto;' });
    row.append(el('span', s.name, { class: 'tool-name' }), el('span', s.sub.split('·')[1] || 'container', { class: 'tool-dur' }));
    badge(row, s.state === 'on' ? 'Up' : 'Degraded', s.state === 'on' ? 'ok' : 'warn');
    dk.append(row);
  }
  dockerCard.body.append(dk);

  const deployCard = card(three, '部署记录', '最近版本发布');
  for (const d of mock.MOCK_DEPLOYS) {
    const item = el('div', undefined, { class: 'feed-item' });
    const main = el('div', undefined, { class: 'feed-main' });
    main.append(el('span', d.ver, { class: 'tag' }), el('span', ' ' + d.note, { style: 'font-size:12.5px;' }));
    main.append(el('div', d.time + ' · by ' + d.by, { class: 'feed-meta' }));
    item.append(main);
    deployCard.body.append(item);
  }

  const srcCard = card(three, '来源同步状态', '真实接口数据');
  load(srcCard.body, () => api.sources(signal), data => {
    table(srcCard.body, (data.items || []).slice(0, 8), [
      { label: '来源', key: 'source_key' },
      { label: '状态', render: row => badge(el('span'), String(row.status ?? '—'), String(row.status).toLowerCase() === 'ok' ? 'ok' : 'warn') },
      { label: '最近成功', render: row => el('span', String(row.last_success_at || '—').replace('T', ' ').slice(0, 16), { class: 'mono', style: 'font-size:11px;' }) },
    ]);
  }, signal);

  /* 5. 日志检索 */
  const logCard = card(view, '运行日志', '关键字过滤 · 级别着色');
  logCard.card.style.marginTop = '16px';
  const logBar = el('div', undefined, { class: 'wb-inline', style: 'margin-bottom:10px;' });
  const logKw = el('input', undefined, { type: 'search', placeholder: '检索日志关键字…', 'aria-label': '日志检索', style: 'min-width:220px;' });
  logBar.append(logKw);
  logCard.body.append(logBar);
  const logView = el('div', undefined, { class: 'log-view', role: 'log', 'aria-label': '系统运行日志' });
  logCard.body.append(logView);
  const LV_CLS = { err: 'lv-err', warn: 'lv-warn', info: 'lv-info', ok: 'lv-ok' };
  function renderLogs() {
    logView.replaceChildren();
    const k = logKw.value.trim().toLowerCase();
    const rows = mock.MOCK_LOGS.filter(l => !k || l.msg.toLowerCase().includes(k));
    if (!rows.length) { logView.append(el('span', '没有匹配的日志行', { class: 'hint' })); return; }
    for (const l of rows) {
      const line = el('div');
      line.append(el('span', l.t + ' ', { class: 'lv-time' }), el('span', l.msg, { class: LV_CLS[l.lv] || '' }));
      logView.append(line);
    }
  }
  logKw.addEventListener('input', renderLogs);
  renderLogs();

  /* 6. 真实同步记录（折叠审计） */
  const runs = card(view, '同步记录（真实接口）', 'SyncRun 原始字段审计');
  runs.card.style.marginTop = '16px';
  load(runs.body, () => api.syncRuns(signal), data => {
    if (!data.items?.length) { runs.body.append(el('p', '暂无同步记录', { class: 'message', 'data-state': 'empty' })); return; }
    table(runs.body, data.items.slice(0, 10), [
      { label: '来源', render: r => r.source_key || r.source || '—' },
      { label: '状态', key: 'status' },
      { label: '开始时间', render: r => el('span', String(r.started_at || r.created_at || '—').replace('T', ' ').slice(0, 19), { class: 'mono', style: 'font-size:11px;' }) },
    ]);
    jsonBlock(runs.body, data.items.slice(0, 3), '展开原始字段');
  }, signal);

  view.append(el('p', '说明：服务健康、趋势、告警、容器、部署与日志为演示口径；来源状态与同步记录来自真实后端接口。', { class: 'chart-note', style: 'margin-top:14px;' }));
}
