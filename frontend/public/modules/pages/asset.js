import { pageTitle, el, section, fields, table, link, load, jsonBlock, message, tabBar, autoTable } from '../components.js';

/* 单个风险快照行的展示（风险页签 + 变化历史共用字段解释） */
const riskColumns = [
  { label: '漏洞', render: row => link(row.canonical_id || row.vulnerability_id, '/vulnerabilities/' + encodeURIComponent(row.canonical_id || row.vulnerability_id)) },
  { label: '组件', key: 'component_name' }, { label: '安装版本', key: 'installed_version' },
  { label: '匹配', key: 'match_status' }, { label: '确认状态', key: 'verification_status' },
  { label: '优先级', key: 'priority' }, { label: '严重度', key: 'severity' },
  { label: '快照过期', key: 'is_stale' }, { label: '评估时间', key: 'evaluated_at' },
  { label: '详情', render: row => { const node = el('div'); jsonBlock(node, row, '展开状态、证据与原因'); return node; } }
];

export async function asset(view, { api, signal }, { id }) {
  pageTitle(view, '资产详情');
  const crumb = el('p', undefined, { class: 'breadcrumb' });
  crumb.append(link('← 返回资产列表', '/assets'), el('span', ' / ' + id, { class: 'mono' }));
  view.append(crumb);

  const detail = section('资产概览', view);
  let assetName = id;
  load(detail, () => api.assetDetail(id, signal), data => {
    assetName = data.name || id;
    document.title = assetName + ' · AegisAI';
    detail.querySelector('h2').textContent = '资产概览：' + assetName;
    fields(detail, data, ['id', 'name', 'asset_type', 'environment', 'exposure', 'description', 'is_demo', 'created_at', 'updated_at']);
    if (Array.isArray(data.components) && data.components.length) {
      const comp = section('组件清单', view);
      table(comp, data.components, [
        { label: '名称', key: 'name' }, { label: '包名', key: 'package_name' }, { label: '生态', key: 'ecosystem' },
        { label: '版本', key: 'version' }, { label: 'PURL', key: 'purl' }, { label: '更新时间', key: 'updated_at' }
      ]);
    }
    jsonBlock(detail, data, '完整 API 字段');
  }, signal);

  /* 页签：风险 / 变化历史 / 库存历史 / 资产复核 */
  const panels = new Map();
  tabBar(view, [['risks', '风险快照'], ['changes', '风险变化'], ['inventory', '库存历史'], ['reviews', '资产复核']], {
    select: tab => { for (const [name, panel] of panels) panel.hidden = name !== tab; }
  });

  const risks = el('section');
  risks.append(el('h2', '资产风险'));
  panels.set('risks', risks);
  load(risks, () => api.risks(id, signal), data => {
    fields(risks, data, ['total']);
    if (data.items?.some(row => row.verification_status === 'CONFLICT' || row.match_status === 'UNCERTAIN')) message(risks, '存在冲突或未确定的版本匹配', 'conflict');
    table(risks, data.items, riskColumns);
  }, signal);
  view.append(risks);

  const changes = el('section');
  changes.append(el('h2', '风险变化历史'));
  panels.set('changes', changes);
  changes.hidden = true;
  load(changes, () => api.riskChanges(id, signal), data => {
    fields(changes, data, ['total']);
    autoTable(changes, data.items);
  }, signal);
  view.append(changes);

  const inventory = el('section');
  inventory.append(el('h2', '库存历史'));
  panels.set('inventory', inventory);
  inventory.hidden = true;
  load(inventory, () => api.inventoryHistory(id, signal), data => {
    fields(inventory, data, ['total']);
    autoTable(inventory, data.items);
  }, signal);
  view.append(inventory);

  const reviewsPanel = el('section');
  reviewsPanel.append(el('h2', '资产专属复核'));
  panels.set('reviews', reviewsPanel);
  reviewsPanel.hidden = true;
  load(reviewsPanel, () => api.assetReviews(id, signal), data => {
    fields(reviewsPanel, data, ['total']);
    table(reviewsPanel, data.items, [
      { label: '复核 ID', render: row => link(row.id, '/reviews/' + encodeURIComponent(row.id)) },
      { label: '状态', key: 'status' }, { label: '优先级', key: 'priority' }, { label: '创建时间', key: 'created_at' },
      { label: '详细字段', render: row => { const node = el('div'); jsonBlock(node, row, '展开复核'); return node; } }
    ]);
  }, signal);
  view.append(reviewsPanel);
}
