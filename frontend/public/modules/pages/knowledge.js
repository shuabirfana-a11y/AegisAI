import { el, link, badge, pageHead, message } from '../components.js';
import * as mock from '../mock-data.js';

/* 知识底座：AI 安全学术论文、技术标准与政策法规。
   检索接口就绪前使用演示数据。 */

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

export function knowledge(view) {
  pageHead(view, '知识底座', '同步采集的 AI 安全学术论文、技术标准与政策法规，支撑富化与问答的语义底座。');

  /* 知识库统计 */
  const kpis = el('div', undefined, { class: 'kpi-grid' });
  view.append(kpis);
  const s = mock.KB_STATS;
  for (const [label, value, unit, note] of [
    ['知识库文档', s.docs.toLocaleString(), '篇', '论文 + 公告 + 标准 + 博客'],
    ['向量片段', s.chunks.toLocaleString(), '段', 'BM25 + 向量双索引'],
    ['学术论文', s.papers, '篇', 'arXiv / USENIX / NDSS 等'],
    ['标准政策', s.standards, '份', 'TC260 / NIST / ISO / OWASP'],
    ['更新频率', s.updateFreq, '', '定时增量同步'],
  ]) {
    const c = el('div', undefined, { class: 'kpi-card' });
    c.append(el('div', label, { class: 'kpi-label' }));
    const v = el('div', undefined, { class: 'kpi-value' });
    v.append(String(value), el('small', ' ' + unit));
    c.append(v, el('div', note, { class: 'kpi-delta' }));
    kpis.append(c);
  }

  /* 检索栏 */
  const bar = el('div', undefined, { class: 'filter-bar' });
  const kw = el('input', undefined, { type: 'search', placeholder: '关键词检索（标题 / 摘要 / 机构）', 'aria-label': '知识检索', style: 'min-width:240px;' });
  const cat = el('select', undefined, { 'aria-label': '分类筛选' });
  for (const t of ['全部分类', '推理框架', '提示词注入', '供应链', '智能体', '对齐安全', '治理框架', '合规要求']) cat.append(el('option', t, { value: t }));
  bar.append(el('span', '检索', { class: 'fb-label' }), kw, cat);
  view.append(bar);

  /* 论文 + 标准政策双栏 */
  const two = el('div', undefined, { class: 'grid grid-2' });
  view.append(two);

  const paperCard = card(two, '学术论文', '标题 · 作者 · 摘要 · 关联漏洞');
  const paperBody = el('div');
  paperCard.body.append(paperBody);

  const stdCard = card(two, '标准与政策法规', '名称 · 发布机构 · 适用范围');
  const stdBody = el('div');
  stdCard.body.append(stdBody);

  function render() {
    const k = kw.value.trim().toLowerCase();
    const c = cat.value;
    paperBody.replaceChildren();
    const papers = mock.MOCK_PAPERS.filter(p =>
      (!k || (p.title + p.abs + p.authors + p.org).toLowerCase().includes(k)) &&
      (c === '全部分类' || p.tags.includes(c)));
    if (!papers.length) message(paperBody, '没有匹配的论文', 'empty');
    for (const p of papers) {
      const item = el('div', undefined, { class: 'feed-item', style: 'flex-direction:column;align-items:stretch;' });
      const titleRow = el('div', undefined, { style: 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;' });
      titleRow.append(el('b', p.title, { style: 'font-size:13.5px;' }));
      for (const t of p.tags) titleRow.append(el('span', t, { class: 'tag accent' }));
      item.append(titleRow);
      item.append(el('div', `${p.authors} · ${p.org} · ${p.date} · ${p.id}`, { class: 'feed-meta' }));
      item.append(el('p', p.abs, { class: 'hint', style: 'margin:6px 0 0;' }));
      if (p.linked.length) {
        const linkRow = el('div', undefined, { class: 'feed-meta', style: 'margin-top:6px;' });
        linkRow.append(el('span', '关联漏洞：'));
        for (const cve of p.linked) linkRow.append(link(cve, '/vulnerabilities/' + encodeURIComponent(cve)));
        item.append(linkRow);
      }
      paperBody.append(item);
    }

    stdBody.replaceChildren();
    const stds = mock.MOCK_STANDARDS.filter(x =>
      (!k || (x.name + x.org + x.scope).toLowerCase().includes(k)) &&
      (c === '全部分类' || x.linked === c));
    if (!stds.length) message(stdBody, '没有匹配的标准政策', 'empty');
    for (const x of stds) {
      const item = el('div', undefined, { class: 'feed-item', style: 'flex-direction:column;align-items:stretch;' });
      const titleRow = el('div', undefined, { style: 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;' });
      titleRow.append(el('b', x.name, { style: 'font-size:13.5px;' }), el('span', x.linked, { class: 'tag ok' }));
      item.append(titleRow);
      item.append(el('div', `${x.org} · ${x.date} · ${x.id}`, { class: 'feed-meta' }));
      item.append(el('p', '适用范围：' + x.scope, { class: 'hint', style: 'margin:6px 0 0;' }));
      stdBody.append(item);
    }
  }
  kw.addEventListener('input', render);
  cat.addEventListener('change', render);
  render();

  view.append(el('p', '演示口径：论文与标准条目为模拟数据；知识检索接口就绪后接入真实向量检索结果。', { class: 'chart-note', style: 'margin-top:14px;' }));
}
