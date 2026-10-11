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
  if (!Array.isArray(rows) || !rows.length) { message(parent, 'Empty / 当前请求没有记录。', 'empty'); return; }
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
  const pending = message(parent, 'Loading / 正在读取 API…', 'loading');
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
  parent.append(el('h2', title));
  if (description) parent.append(el('p', description));
}
