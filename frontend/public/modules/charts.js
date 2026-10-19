/* 原生 SVG 图表库：折线/面积图、柱状图、环形图、迷你火花线、横向条形。
   无外部依赖（CSP: script-src 'self'），全部手工构造 SVG。 */
const NS = 'http://www.w3.org/2000/svg';

function svgEl(tag, attrs = {}, text) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}

const PALETTE = ['#22d3ee', '#818cf8', '#34d399', '#fbbf24', '#fb923c', '#fb4d6d', '#60a5fa', '#e879c9'];
export const SEV_COLOR = { critical: '#fb4d6d', high: '#fb923c', medium: '#facc15', low: '#34d399', info: '#60a5fa', unknown: '#66738c' };

/* ---------- 折线/面积趋势图 ----------
   series: [{ label, color?, points: [{label, value}] }] 多序列；单序列自动加面积渐变 */
export function lineChart(parent, series, { ariaLabel = '趋势图', unit = '', height = 190, area = true } = {}) {
  const W = 640, H = height, L = 40, R = 12, T = 14, B = 26;
  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'line-chart', role: 'img', 'aria-label': ariaLabel });
  const all = series.flatMap(s => s.points.map(p => p.value));
  const max = Math.max(1, ...all) * 1.08;
  const labels = series[0]?.points.map(p => p.label) || [];
  const n = Math.max(1, labels.length - 1);
  const x = i => L + (i / n) * (W - L - R);
  const y = v => T + (1 - v / max) * (H - T - B);

  const defs = svgEl('defs');
  const grad = svgEl('linearGradient', { id: 'chartGradient', x1: '0', y1: '0', x2: '0', y2: '1' });
  grad.append(svgEl('stop', { offset: '0%', 'stop-color': series[0]?.color || '#22d3ee', 'stop-opacity': '0.28' }));
  grad.append(svgEl('stop', { offset: '100%', 'stop-color': series[0]?.color || '#22d3ee', 'stop-opacity': '0' }));
  defs.append(grad);
  svg.append(defs);

  for (let g = 0; g <= 3; g++) {
    const gy = T + (g / 3) * (H - T - B);
    svg.append(svgEl('path', { class: 'chart-grid', d: `M${L} ${gy}H${W - R}` }));
    const lbl = svgEl('text', { x: 4, y: gy + 3, class: 'chart-label' }, String(Math.round(max * (1 - g / 3))));
    svg.append(lbl);
  }
  series.forEach((s, si) => {
    const color = s.color || PALETTE[si % PALETTE.length];
    const pts = s.points.map((p, i) => [x(i), y(p.value)]);
    if (!pts.length) return;
    const d = pts.map((c, i) => (i ? 'L' : 'M') + c[0].toFixed(1) + ' ' + c[1].toFixed(1)).join(' ');
    if (area && si === 0) {
      const areaPath = svgEl('path', { class: 'chart-area', d: d + ` L${x(pts.length - 1).toFixed(1)} ${y(0)} L${x(0).toFixed(1)} ${y(0)} Z` });
      svg.append(areaPath);
    }
    svg.append(svgEl('path', { class: 'chart-line', d, style: `stroke:${color}` }));
    for (let i = 0; i < pts.length; i++) {
      const dot = svgEl('circle', { class: 'chart-dot', cx: pts[i][0].toFixed(1), cy: pts[i][1].toFixed(1), r: '2.6', style: `stroke:${color}` });
      dot.append(svgEl('title', {}, `${s.label ? s.label + ' · ' : ''}${s.points[i].label}：${s.points[i].value}${unit}`));
      svg.append(dot);
    }
  });
  const tickIdx = [...new Set([0, Math.floor(labels.length / 2), labels.length - 1])];
  for (const i of tickIdx) {
    if (!labels[i]) continue;
    svg.append(svgEl('text', {
      x: x(i), y: H - 8, class: 'chart-label',
      'text-anchor': i === 0 ? 'start' : i === labels.length - 1 ? 'end' : 'middle'
    }, labels[i]));
  }
  const wrap = document.createElement('div');
  wrap.className = 'chart-wrap';
  wrap.append(svg);
  parent.append(wrap);
  return wrap;
}

/* ---------- 环形图 ----------
   items: [{ label, value, color?, href? }]；中心显示总数 */
export function donutChart(parent, items, { ariaLabel = '分布图', size = 190, centerLabel = '总计', onSelect } = {}) {
  const total = items.reduce((s, it) => s + it.value, 0) || 1;
  const R = 62, C = 2 * Math.PI * R, cx = size / 2, cy = size / 2;
  const svg = svgEl('svg', { viewBox: `0 0 ${size} ${size}`, width: size, height: size, role: 'img', 'aria-label': ariaLabel });
  svg.append(svgEl('circle', { cx, cy, r: R, fill: 'none', stroke: 'rgba(148,163,184,.12)', 'stroke-width': 17 }));
  let acc = 0;
  items.forEach((it, i) => {
    if (!it.value) return;
    const frac = it.value / total;
    const seg = svgEl('circle', {
      cx, cy, r: R, fill: 'none',
      stroke: it.color || PALETTE[i % PALETTE.length],
      'stroke-width': 17,
      'stroke-dasharray': `${(frac * C).toFixed(2)} ${C.toFixed(2)}`,
      'stroke-dashoffset': String((-acc * C).toFixed(2)),
      transform: `rotate(-90 ${cx} ${cy})`
    });
    seg.append(svgEl('title', {}, `${it.label}：${it.value}（${(frac * 100).toFixed(1)}%）`));
    svg.append(seg);
    acc += frac;
  });
  const sum = items.reduce((s, it) => s + it.value, 0);
  svg.append(svgEl('text', { x: cx, y: cy + 2, 'text-anchor': 'middle', class: 'donut-center-num' }, String(sum)));
  svg.append(svgEl('text', { x: cx, y: cy + 20, 'text-anchor': 'middle', class: 'donut-center-label' }, centerLabel));

  const legend = document.createElement('div');
  legend.className = 'donut-legend';
  items.forEach((it, i) => {
    const row = document.createElement(onSelect || it.href ? 'button' : 'div');
    row.className = 'lg-item';
    if (row.tagName === 'BUTTON') row.type = 'button';
    const dot = document.createElement('span');
    dot.className = 'lg-dot';
    dot.style.background = it.color || PALETTE[i % PALETTE.length];
    const name = document.createElement('span');
    name.textContent = it.label;
    const val = document.createElement('span');
    val.className = 'lg-val';
    val.textContent = String(it.value);
    row.append(dot, name, val);
    if (onSelect) row.addEventListener('click', () => onSelect(it));
    else if (it.href) row.addEventListener('click', () => { location.href = it.href; });
    legend.append(row);
  });
  const wrap = document.createElement('div');
  wrap.className = 'donut-wrap';
  wrap.append(svg, legend);
  parent.append(wrap);
  return wrap;
}

/* ---------- 横向条形图 ----------
   items: [{ label, value, color?, hint? }] */
export function barList(parent, items, { unit = '' } = {}) {
  const max = Math.max(1, ...items.map(i => i.value));
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;flex-direction:column;gap:9px;';
  for (const it of items) {
    const row = document.createElement('div');
    row.style.cssText = 'display:grid;grid-template-columns:130px 1fr 52px;gap:10px;align-items:center;font-size:12px;';
    const label = document.createElement('span');
    label.textContent = it.label;
    label.style.cssText = 'color:var(--secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
    if (it.hint) label.title = it.hint;
    const track = document.createElement('div');
    track.style.cssText = 'height:8px;border-radius:4px;background:rgba(148,163,184,.12);overflow:hidden;';
    const bar = document.createElement('i');
    bar.style.cssText = `display:block;height:100%;width:${(it.value / max * 100).toFixed(1)}%;border-radius:4px;background:${it.color || 'linear-gradient(90deg,#0e7490,#22d3ee)'};transition:width .5s ease;`;
    track.append(bar);
    const val = document.createElement('span');
    val.textContent = it.value + unit;
    val.style.cssText = 'font-family:var(--mono);text-align:right;color:var(--text);font-weight:600;';
    row.append(label, track, val);
    wrap.append(row);
  }
  parent.append(wrap);
  return wrap;
}

/* ---------- 迷你火花线（KPI 卡内） ---------- */
export function sparkline(parent, values, { color = '#22d3ee', width = 120, height = 34 } = {}) {
  const max = Math.max(1, ...values), min = Math.min(0, ...values);
  const n = Math.max(1, values.length - 1);
  const pts = values.map((v, i) => [(i / n) * width, height - 4 - ((v - min) / (max - min || 1)) * (height - 8)]);
  const svg = svgEl('svg', { viewBox: `0 0 ${width} ${height}`, width, height, 'aria-hidden': 'true' });
  const d = pts.map((c, i) => (i ? 'L' : 'M') + c[0].toFixed(1) + ' ' + c[1].toFixed(1)).join(' ');
  svg.append(svgEl('path', { d: d + ` L${width} ${height} L0 ${height} Z`, fill: color, opacity: '0.14', stroke: 'none' }));
  svg.append(svgEl('path', { d, fill: 'none', stroke: color, 'stroke-width': '1.8', 'stroke-linecap': 'round' }));
  parent.append(svg);
  return svg;
}

/* ---------- 自动化流水线（横向节点流） ----------
   nodes: [{ name, state: 'ok'|'running'|'error'|'idle', meta: [..] }] */
export function pipelineFlow(parent, nodes) {
  const wrap = document.createElement('div');
  wrap.className = 'pipeline';
  const STATE_LABEL = { ok: '正常', running: '运行中', error: '异常', idle: '待机' };
  const STATE_DOT = { ok: 'on', running: 'on', error: 'off', idle: 'idle' };
  nodes.forEach((node, i) => {
    if (i) {
      const arrow = document.createElement('span');
      arrow.className = 'pipe-arrow';
      arrow.setAttribute('aria-hidden', 'true');
      arrow.textContent = '→';
      wrap.append(arrow);
    }
    const card = document.createElement('div');
    card.className = 'pipe-node';
    card.dataset.state = node.state;
    const name = document.createElement('div');
    name.className = 'pn-name';
    const dot = document.createElement('i');
    dot.className = 'pulse-dot ' + (STATE_DOT[node.state] || 'idle');
    name.append(dot, document.createTextNode(node.name));
    const stateTag = document.createElement('span');
    stateTag.className = 'tag' + (node.state === 'ok' ? ' ok' : node.state === 'error' ? ' danger' : node.state === 'running' ? '' : ' warn');
    stateTag.textContent = STATE_LABEL[node.state] || node.state;
    name.append(stateTag);
    card.append(name);
    if (node.meta?.length) {
      const meta = document.createElement('div');
      meta.className = 'pn-meta';
      meta.innerHTML = node.meta.map(l => String(l).replace(/[<&]/g, c => ({ '<': '&lt;', '&': '&amp;' }[c]))).join('<br>');
      card.append(meta);
    }
    wrap.append(card);
  });
  parent.append(wrap);
  return wrap;
}

/* ---------- 知识图谱（力导向静态布局简版：径向布局） ----------
   center: { label, sub }, nodes: [{ label, sub, color?, href?, ring? }] */
export function knowledgeGraph(parent, center, nodes, { width = 720, height = 380 } = {}) {
  const svg = svgEl('svg', { viewBox: `0 0 ${width} ${height}`, class: 'kg-svg', role: 'img', 'aria-label': '知识图谱关系图' });
  const cx = width / 2, cy = height / 2;
  const rings = new Map();
  for (const n of nodes) {
    const ring = n.ring ?? 1;
    if (!rings.has(ring)) rings.set(ring, []);
    rings.get(ring).push(n);
  }
  const placed = [];
  for (const [ring, group] of [...rings.entries()].sort()) {
    const radius = ring === 0 ? 0 : 90 + ring * 62;
    group.forEach((n, i) => {
      const angle = (i / group.length) * Math.PI * 2 - Math.PI / 2 + (ring * 0.5);
      placed.push({ ...n, x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) });
    });
  }
  for (const n of placed) {
    svg.append(svgEl('line', { x1: cx, y1: cy, x2: n.x, y2: n.y, class: 'kg-edge' }));
    const mx = (cx + n.x) / 2, my = (cy + n.y) / 2;
    if (n.relation) svg.append(svgEl('text', { x: mx, y: my - 3, 'text-anchor': 'middle', class: 'kg-edge-label' }, n.relation));
  }
  for (const n of placed) {
    const g = svgEl('g', { class: 'kg-node' });
    const c = svgEl('circle', { cx: n.x, cy: n.y, r: n.r || 15, fill: n.color || '#16213a', stroke: n.stroke || 'rgba(34,211,238,.55)', 'stroke-width': '1.5' });
    g.append(c);
    g.append(svgEl('text', { x: n.x, y: n.y + (n.r || 15) + 13, 'text-anchor': 'middle' }, n.label));
    if (n.sub) g.append(svgEl('text', { x: n.x, y: n.y + (n.r || 15) + 25, 'text-anchor': 'middle', class: 'kg-edge-label' }, n.sub));
    if (n.href) {
      g.style.cursor = 'pointer';
      g.addEventListener('click', () => { location.href = n.href; });
    }
    const title = svgEl('title', {}, n.label + (n.sub ? ' · ' + n.sub : ''));
    g.append(title);
    svg.append(g);
  }
  const g0 = svgEl('g', { class: 'kg-node' });
  g0.append(svgEl('circle', { cx, cy, r: 30, fill: 'rgba(34,211,238,.16)', stroke: '#22d3ee', 'stroke-width': '2' }));
  g0.append(svgEl('text', { x: cx, y: cy - 1, 'text-anchor': 'middle', style: 'font-weight:700;font-size:9.5px;' }, center.label));
  if (center.sub) g0.append(svgEl('text', { x: cx, y: cy + 11, 'text-anchor': 'middle', class: 'kg-edge-label' }, center.sub));
  svg.append(g0);
  const wrap = document.createElement('div');
  wrap.className = 'kg-wrap';
  wrap.append(svg);
  parent.append(wrap);
  return wrap;
}
