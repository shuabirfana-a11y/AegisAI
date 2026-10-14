export function text(value) {
  if (value === undefined || value === null || value === '') return '未提供 / UNKNOWN';
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

export function el(tag, value, attributes = {}) {
  const node = document.createElement(tag);
  if (value !== undefined) node.textContent = text(value);
  for (const [name, attribute] of Object.entries(attributes)) node.setAttribute(name, attribute);
  return node;
}

export function link(label, href) {
  const node = el('a', label, { href });
  node.dataset.route = '';
  return node;
}

export function section(title, parent) {
  const node = el('section');
  node.append(el('h2', title));
  parent.append(node);
  return node;
}

export function message(parent, value, kind = 'status') {
  const node = el('p', value, { class: 'message', role: kind === 'error' ? 'alert' : 'status', 'data-state': kind });
  parent.append(node);
  return node;
}

export function showError(parent, error) {
  if (error.name === 'AbortError') return;
  message(parent, (error.kind === 'conflict' ? 'Conflict / 冲突：' : 'Error / ') + error.message + (error.status ? ` (HTTP ${error.status})` : ''), 'error');
}

export function jsonBlock(parent, value, title = '原始 API 字段') {
  const details = el('details');
  details.append(el('summary', title), el('pre', JSON.stringify(value, null, 2)));
  parent.append(details);
}

export function fields(parent, data, keys) {
  const list = el('dl');
  for (const key of keys) list.append(el('dt', key), el('dd', data?.[key]));
  parent.append(list);
}

export function table(parent, rows, columns) {
  if (!Array.isArray(rows) || !rows.length) { message(parent, '暂无记录', 'empty'); return; }
  const wrapper = el('div', undefined, { class: 'table-container' });
  const tableNode = el('table');
  const head = el('tr');
  for (const column of columns) head.append(el('th', column.label, { scope: 'col' }));
  const thead = el('thead'); thead.append(head); tableNode.append(thead);
  const body = el('tbody');
  for (const row of rows) {
    const tr = el('tr');
    for (const column of columns) {
      const td = el('td');
      const value = column.render ? column.render(row) : row[column.key];
      if (value instanceof Node) td.append(value); else td.textContent = text(value);
      tr.append(td);
    }
    body.append(tr);
  }
  tableNode.append(body); wrapper.append(tableNode); parent.append(wrapper);
}

export async function load(parent, fetchData, render, signal) {
  const pending = message(parent, '读取中…', 'loading');
  try {
    const data = await fetchData();
    if (signal?.aborted) return;
    pending.remove();
    render(data);
  } catch (error) {
    pending.remove();
    if (!signal?.aborted) showError(parent, error);
  }
}

export function pageTitle(parent, title, description) {
  const node = el('h2', title, { class: 'page-title' });
  parent.append(node);
  if (description) parent.append(el('p', description));
  return node;
}

/* ---------- 数字卡 / 状态标签（仪表盘、资产概况等共用） ---------- */
const svgIcon = body => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
export const METRIC_ICONS = {
  assets: svgIcon('<rect width="20" height="8" x="2" y="2" rx="2"/><rect width="20" height="8" x="2" y="14" rx="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/>'),
  components: svgIcon('<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>'),
  affected: svgIcon('<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>'),
  critical: svgIcon('<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>'),
  poc: svgIcon('<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>'),
  kev: svgIcon('<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'),
  patch: svgIcon('<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'),
  uncertain: svgIcon('<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>'),
  vulns: svgIcon('<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1 1 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'),
  reviews: svgIcon('<rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>'),
  search: svgIcon('<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>'),
};

export function metricCard(parent, { icon, label, value, tone, note, href }) {
  const card = href ? el('a', undefined, { class: 'metric-card metric-link', href }) : el('div', undefined, { class: 'metric-card' });
  if (href) card.dataset.route = '';
  if (tone) card.dataset.tone = tone;
  const head = el('div', undefined, { class: 'metric-head' });
  const ic = document.createElement('span');
  ic.className = 'metric-ic';
  ic.innerHTML = METRIC_ICONS[icon] || '';
  head.append(ic, el('span', label));
  const val = el('div', undefined, { class: 'metric-value' });
  val.textContent = value === undefined ? '…' : text(value);
  if (note) card.append(el('span', note, { class: 'metric-note' }));
  card.append(head, val);
  parent.append(card);
  return { card, val };
}

export function statusChip(parent, label, value) {
  const chip = el('span', undefined, { class: 'status-chip' });
  chip.dataset.state = String(value);
  chip.append(el('span', label), el('b', String(value)));
  parent.append(chip);
  return chip;
}

/* ---------- 徽标 / 严重度 ---------- */
const TONES = { danger: 'danger', warn: 'warn', ok: 'ok', review: 'review', info: 'info', neutral: 'neutral' };
export function badge(parent, value, tone = 'neutral') {
  const node = el('span', value, { class: 'badge' });
  node.dataset.tone = TONES[tone] || 'neutral';
  parent.append(node);
  return node;
}
const SEVERITY_TONE = { critical: 'danger', high: 'danger', medium: 'warn', low: 'ok', info: 'neutral', unknown: 'neutral' };
export function severityBadge(parent, severity) {
  return badge(parent, String(severity ?? 'UNKNOWN'), SEVERITY_TONE[String(severity).toLowerCase()] || 'neutral');
}

/* ---------- 页头（标题 + 操作区） ---------- */
export function pageHead(parent, title, description, actions) {
  const head = el('div', undefined, { class: 'page-head' });
  const textCol = el('div', undefined, { class: 'page-head-text' });
  textCol.append(el('h2', title, { class: 'page-title' }));
  if (description) textCol.append(el('p', description, { class: 'page-sub' }));
  head.append(textCol);
  if (actions && actions.childNodes.length) head.append(actions);
  parent.append(head);
  return head;
}

/* ---------- 原生 SVG 折线图（无依赖；数据为空时调用方显示空态） ---------- */
export function svgLineChart(parent, points, { ariaLabel = '趋势图', valueUnit = '' } = {}) {
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.setAttribute('class', 'line-chart');
  svg.setAttribute('viewBox', '0 0 320 130');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', ariaLabel);
  const W = 292, H = 94, L = 26, T = 8;
  const max = Math.max(1, ...points.map(p => p.value));
  const step = points.length > 1 ? W / (points.length - 1) : 0;
  const scaleY = v => T + H - (v / max) * H;
  const grid = document.createElementNS(svgNS, 'path');
  grid.setAttribute('class', 'chart-grid');
  grid.setAttribute('d', `M${L} ${T}H${L + W}M${L} ${T + H / 2}H${L + W}M${L} ${T + H}H${L + W}`);
  svg.append(grid);
  for (const [frac, text] of [[0, String(max)], [.5, String(Math.round(max / 2))], [1, '0']]) {
    const label = document.createElementNS(svgNS, 'text');
    label.setAttribute('x', '2');
    label.setAttribute('y', String(T + H - frac * H + 3));
    label.setAttribute('class', 'chart-label');
    label.textContent = text;
    svg.append(label);
  }
  const coords = points.map((p, i) => ({ x: L + i * step, y: scaleY(p.value), p }));
  if (coords.length) {
    const line = document.createElementNS(svgNS, 'path');
    line.setAttribute('class', 'chart-line');
    line.setAttribute('d', coords.map((c, i) => (i ? 'L' : 'M') + c.x.toFixed(1) + ' ' + c.y.toFixed(1)).join(' '));
    svg.append(line);
    for (const c of coords) {
      const dot = document.createElementNS(svgNS, 'circle');
      dot.setAttribute('class', 'chart-dot');
      dot.setAttribute('cx', c.x.toFixed(1));
      dot.setAttribute('cy', c.y.toFixed(1));
      dot.setAttribute('r', '3');
      const title = document.createElementNS(svgNS, 'title');
      title.textContent = `${c.p.label}：${c.p.value}${valueUnit}`;
      dot.append(title);
      svg.append(dot);
    }
  }
  for (const i of [0, Math.floor((points.length - 1) / 2), points.length - 1]) {
    if (!points[i]) continue;
    const label = document.createElementNS(svgNS, 'text');
    label.setAttribute('x', String(L + i * step));
    label.setAttribute('y', '122');
    label.setAttribute('class', 'chart-label');
    label.setAttribute('text-anchor', i === 0 ? 'start' : i === points.length - 1 ? 'end' : 'middle');
    label.textContent = points[i].label;
    svg.append(label);
  }
  const wrap = el('div', undefined, { class: 'chart-wrap' });
  wrap.append(svg);
  parent.append(wrap);
  return wrap;
}

/* ---------- 分页 ---------- */
export function pager(parent, { offset = 0, limit = 20, total = 0, onPage }) {
  if (total <= limit) return null;
  const bar = el('div', undefined, { class: 'pager' });
  const from = total ? offset + 1 : 0;
  const to = Math.min(offset + limit, total);
  bar.append(el('span', `${from}–${to} / ${total}`, { class: 'pager-info' }));
  const group = el('div', undefined, { class: 'pager-btns' });
  const prev = el('button', '上一页', { type: 'button' });
  prev.disabled = offset <= 0;
  prev.addEventListener('click', () => onPage(Math.max(0, offset - limit)));
  const next = el('button', '下一页', { type: 'button' });
  next.disabled = to >= total;
  next.addEventListener('click', () => onPage(offset + limit));
  group.append(prev, next);
  bar.append(group);
  parent.append(bar);
  return bar;
}

/* ---------- 页签 ---------- */
export function tabBar(parent, tabs, { select, initial = 0 }) {
  const bar = el('div', undefined, { class: 'tab-bar', role: 'tablist' });
  const buttons = [];
  tabs.forEach(([id, label], index) => {
    const button = el('button', label, { type: 'button', role: 'tab' });
    button.setAttribute('aria-selected', String(index === initial));
    button.dataset.tone = index === initial ? 'active' : '';
    button.addEventListener('click', () => {
      buttons.forEach(b => { b.setAttribute('aria-selected', 'false'); b.dataset.tone = ''; });
      button.setAttribute('aria-selected', 'true');
      button.dataset.tone = 'active';
      select(id);
    });
    buttons.push(button);
    bar.append(button);
  });
  parent.append(bar);
  return bar;
}

/* ---------- 防御式表格：结构未知的记录取前 8 个键做列，对象值序列化展示 ---------- */
export function autoTable(parent, rows, { title = '展开完整原始字段' } = {}) {
  if (!Array.isArray(rows) || !rows.length) { message(parent, '暂无记录', 'empty'); return; }
  const keys = [...new Set(rows.flatMap(row => Object.keys(row ?? {})))].filter(key => !['metadata'].includes(key)).slice(0, 8);
  table(parent, rows, keys.map(key => ({ label: key, render: row => {
    const value = row?.[key];
    if (value === null || value === undefined) return '—';
    if (typeof value === 'object') return JSON.stringify(value).slice(0, 120);
    return String(value);
  } })));
  jsonBlock(parent, rows, title);
}

/* 页面卸载(signal abort)之外的读取失败才回调 */
export const onFail = fn => err => { if (err?.name !== 'AbortError') fn(err); };
