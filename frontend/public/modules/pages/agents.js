import { el, badge, pageHead } from '../components.js';
import * as mock from '../mock-data.js';

/* Agent 运行与编排中心：把「Agent 在干什么」可视化。
   后端编排接口就绪前使用演示数据（页面底部标注口径）。 */

const NS = 'http://www.w3.org/2000/svg';
function svgEl(tag, attrs = {}, text) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}

const AGENT_ICONS = {
  radar: '<path d="M12 20h.01"/><path d="M2 8.82a15 15 0 0 1 20 0"/><path d="M5 12.86a10 10 0 0 1 14 0"/><path d="M8.5 16.43a5 5 0 0 1 7 0"/>',
  tag: '<path d="M12 2H2v10l9.3 9.3a1 1 0 0 0 1.4 0l8.6-8.6a1 1 0 0 0 0-1.4Z"/><circle cx="7.5" cy="7.5" r="1"/>',
  spark: '<path d="M12 3v3m0 12v3M5.6 5.6l2.2 2.2m8.4 8.4 2.2 2.2M3 12h3m12 0h3M5.6 18.4l2.2-2.2m8.4-8.4 2.2-2.2"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  check: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
};

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

/* 编排流程图 */
function orchFlow(parent, nodes, edges) {
  const W = 900, H = 230, NW = 150, NH = 56;
  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'orch-svg', role: 'img', 'aria-label': 'Agent 任务编排流程图' });
  const defs = svgEl('defs');
  const marker = svgEl('marker', { id: 'orchArrow', viewBox: '0 0 10 10', refX: '9', refY: '5', markerWidth: '7', markerHeight: '7', orient: 'auto-start-reverse' });
  marker.append(svgEl('path', { d: 'M0 0L10 5L0 10z', fill: 'rgba(148,163,184,.6)' }));
  defs.append(marker);
  svg.append(defs);
  const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
  for (const [from, to] of edges) {
    const a = byId[from], b = byId[to];
    if (!a || !b) continue;
    const x1 = a.x + NW, y1 = a.y + NH / 2, x2 = b.x, y2 = b.y + NH / 2;
    const midX = (x1 + x2) / 2;
    const d = y1 === y2 ? `M${x1} ${y1}H${x2}` : `M${x1} ${y1} C${midX} ${y1} ${midX} ${y2} ${x2} ${y2}`;
    const edge = svgEl('path', { d, class: 'orch-edge' + (a.state === 'running' || b.state === 'running' ? ' flow' : '') });
    svg.append(edge);
  }
  for (const n of nodes) {
    const g = svgEl('g', { class: 'orch-node ' + (n.state || 'idle') });
    g.append(svgEl('rect', { x: n.x, y: n.y, width: NW, height: NH }));
    g.append(svgEl('text', { x: n.x + NW / 2, y: n.y + 24, 'text-anchor': 'middle', style: 'font-weight:600;' }, n.name));
    g.append(svgEl('text', { x: n.x + NW / 2, y: n.y + 41, 'text-anchor': 'middle', class: 'on-sub' }, n.sub));
    const title = svgEl('title', {}, `${n.name} · ${n.sub} · ${({ done: '已完成', running: '运行中', error: '异常', idle: '等待' })[n.state] || '等待'}`);
    g.append(title);
    svg.append(g);
  }
  parent.append(svg);
}

export function agents(view, { signal }) {
  pageHead(view, 'Agent 运行与编排中心', '自主决策、任务编排、工具调用全链路可视化 —— 「Agent 在干什么」一目了然。');

  /* 顶部 KPI */
  const kpis = el('div', undefined, { class: 'kpi-grid' });
  view.append(kpis);
  for (const [label, value, unit, note] of [
    ['在线 Agent', 7, '个', '6 运行中 · 1 待机'],
    ['今日任务执行', 640, '次', '跨 6 类 Agent'],
    ['任务成功率', 96.8, '%', '近 24h'],
    ['异常自愈', 7, '次', '自动重试 / 降级 / 回退'],
    ['工具调用', '3,214', '次', '11 种工具'],
  ]) {
    const c = el('div', undefined, { class: 'kpi-card' });
    c.append(el('div', label, { class: 'kpi-label' }));
    const v = el('div', undefined, { class: 'kpi-value' });
    v.append(String(value), el('small', ' ' + unit));
    c.append(v, el('div', note, { class: 'kpi-delta' }));
    kpis.append(c);
  }

  /* 2. 任务编排图 */
  const orch = card(view, '任务编排实况', '一次新 CVE 情报处理任务 · 节点显示耗时与状态');
  const orchBox = el('div', undefined, { class: 'orch-flow' });
  orchFlow(orchBox, mock.MOCK_ORCH, mock.MOCK_ORCH_EDGES);
  orch.body.append(orchBox);

  /* 1. Agent 角色列表 */
  const listCard = card(view, 'Agent 角色', '职责 · 工具列表 · 运行状态 · 成功率');
  listCard.card.style.marginTop = '16px';
  const grid = el('div', undefined, { class: 'agent-grid' });
  for (const a of mock.MOCK_AGENTS) {
    const c = el('div', undefined, { class: 'agent-card' });
    const headRow = el('div', undefined, { class: 'agent-head' });
    const avatar = el('span', undefined, { class: 'agent-avatar' });
    avatar.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${AGENT_ICONS[a.icon] || AGENT_ICONS.spark}</svg>`;
    const nameCol = el('div');
    nameCol.append(el('div', a.name, { class: 'agent-name' }), el('div', a.role, { class: 'agent-role' }));
    headRow.append(avatar, nameCol);
    const state = el('span', a.state, { class: 'tag ' + (a.state === '运行中' ? 'ok' : 'warn'), style: 'margin-left:auto;' });
    headRow.append(state);
    const stats = el('div', undefined, { class: 'agent-stats' });
    for (const [num, lab] of [[a.success + '%', '成功率'], [String(a.runs), '运行次数'], [a.avgDur, '平均耗时']]) {
      const s = el('div', undefined, { class: 'agent-stat' });
      s.append(el('b', num), el('span', lab));
      stats.append(s);
    }
    const tools = el('div', undefined, { class: 'agent-tools' });
    for (const t of a.tools) tools.append(el('span', t, { class: 'tag' }));
    c.append(headRow, stats, tools);
    grid.append(c);
  }
  listCard.body.append(grid);

  /* 3 + 4 双栏：工具调用日志 / 自主决策轨迹 */
  const two = el('div', undefined, { class: 'grid', style: 'grid-template-columns: 1.25fr 1fr; margin-top:16px;' });
  view.append(two);

  const toolCard = card(two, '工具调用日志', '工具调用能力的直接证据');
  const logBox = el('div', undefined, { class: 'tool-log' });
  for (const t of mock.MOCK_TOOL_LOGS) {
    const row = el('div', undefined, { class: 'tool-row' });
    row.append(
      el('span', t.tool, { class: 'tool-name' }),
      el('span', t.io, { class: 'tool-io', title: t.io }),
      el('span', t.dur, { class: 'tool-dur' }),
      el('span', t.time, { class: 'tool-dur hide-sm' }),
    );
    badge(row, t.ok ? '成功' : '失败', t.ok ? 'ok' : 'danger');
    logBox.append(row);
  }
  toolCard.body.append(logBox);

  const decCard = card(two, '自主决策轨迹', 'Agent 的决策理由可审计');
  for (const d of mock.MOCK_DECISIONS) {
    const item = el('div', undefined, { class: 'decision-item' });
    const ic = el('span', undefined, { class: 'd-icon' });
    ic.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a7 7 0 0 1 7 7c0 2.4-1.2 4.5-3 5.7V17a1 1 0 0 1-1 1h-6a1 1 0 0 1-1-1v-2.3c-1.8-1.3-3-3.4-3-5.7a7 7 0 0 1 7-7z"/><path d="M9 22h6"/></svg>`;
    const main = el('div');
    main.append(el('div', d.text, { class: 'd-text' }), el('div', d.agent + ' · ' + d.time, { class: 'd-meta' }));
    item.append(ic, main);
    decCard.body.append(item);
  }

  /* 5. 异常处理与自愈 */
  const healCard = card(view, '异常处理与自愈', '异常事件 → 处理动作 → 恢复状态');
  healCard.card.style.marginTop = '16px';
  for (const h of mock.MOCK_HEALING) {
    const row = el('div', undefined, { class: 'heal-flow', style: 'margin-bottom:10px;' });
    row.append(
      el('span', h.err, { class: 'heal-step err' }),
      el('span', '→', { class: 'heal-arrow' }),
      el('span', h.act, { class: 'heal-step act' }),
      el('span', '→', { class: 'heal-arrow' }),
      el('span', h.ok, { class: 'heal-step ok' }),
      el('span', h.time, { class: 'hint mono' }),
    );
    healCard.body.append(row);
  }
  view.append(el('p', '演示口径：本页指标与轨迹为模拟数据；编排接口就绪后切换为真实任务流。', { class: 'chart-note', style: 'margin-top:14px;' }));
}
