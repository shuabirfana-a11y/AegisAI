import { pageTitle, el, section, fields, table, link, load, jsonBlock, message } from '../components.js';

export async function review(view, { api, signal }, { id }) {
  pageTitle(view, '复核详情');
  const crumb = el('p', undefined, { class: 'breadcrumb' });
  crumb.append(link('← 返回复核列表', '/reviews'), el('span', ' / ' + id, { class: 'mono' }));
  view.append(crumb);

  const body = section('复核任务', view);
  load(body, () => api.reviewDetail(id, signal), data => {
    document.title = (data.review_type || '复核') + ' · AegisAI';
    body.querySelector('h2').textContent = '复核任务：' + (data.review_type || id);
    fields(body, data, ['id', 'review_type', 'status', 'priority', 'revision', 'created_at', 'updated_at']);
    if (data.status === 'open' || data.details?.conflict) message(body, '存在待人工复核记录', 'conflict');

    /* 关联漏洞入口 */
    const vulnId = data.vulnerability_id || data.claim?.vulnerability_id;
    if (vulnId) {
      const vulnRow = el('p', undefined, { class: 'breadcrumb' });
      vulnRow.append(link('查看关联漏洞 ' + vulnId, '/vulnerabilities/' + encodeURIComponent(vulnId)));
      body.append(vulnRow);
    }

    /* Claim：先展示常见字段，再保留完整原始 JSON */
    if (data.claim) {
      const claimPanel = section('关联 Claim', view);
      fields(claimPanel, data.claim, ['id', 'claim_type', 'predicate', 'verification_status', 'revision', 'scope_key']);
      jsonBlock(claimPanel, data.claim, 'Claim 完整字段');
    }

    /* Evidence 列表 */
    const evidencePanel = section('证据（Evidence）', view);
    if (Array.isArray(data.evidence) && data.evidence.length) {
      table(evidencePanel, data.evidence, [
        { label: 'ID', key: 'id' }, { label: '立场', key: 'stance' }, { label: '来源', key: 'source_key' },
        { label: '摘录', render: row => el('span', String(row.excerpt || '').slice(0, 80), { class: 'mono' }) },
        { label: '获取时间', key: 'retrieved_at' },
        { label: '详情', render: row => { const node = el('div'); jsonBlock(node, row, '展开证据'); return node; } }
      ]);
    } else message(evidencePanel, '暂无证据记录', 'empty');

    /* 审计日志 */
    const auditPanel = section('审计日志', view);
    if (Array.isArray(data.audit) && data.audit.length) {
      table(auditPanel, data.audit, [
        { label: '时间', key: 'created_at' }, { label: '操作者', key: 'actor' },
        { label: '动作', key: 'action' }, { label: '状态', key: 'status' },
        { label: '详情', render: row => { const node = el('div'); jsonBlock(node, row, '展开审计'); return node; } }
      ]);
    } else message(auditPanel, '暂无审计记录', 'empty');

    jsonBlock(view, data, '完整 API 字段');
  }, signal);
}
