import { pageTitle, el, section, fields, table, link, load, metricCard, onFail, message } from '../components.js';

export function assets(view, { api, signal }) {
  pageTitle(view, '资产风险', '从资产与组件出发，查看风险快照与历史变化。');
  view.append(el('h3', '资产概况'));
  const overviewGrid = el('div', undefined, { class: 'metric-grid' });
  view.append(overviewGrid);
  api.overview(signal).then(data => {
    const cards = [
      ['assets', '资产', 'assets', ''],
      ['components', '组件', 'components', ''],
      ['affected', '受影响组件', 'affected_components', 'warn'],
      ['critical', '严重 / 高', 'critical_high', 'danger'],
      ['poc', '已确认 POC', 'confirmed_poc', 'warn'],
      ['kev', 'KEV', 'kev', 'danger'],
      ['patch', '有补丁', 'patch_available', 'ok'],
      ['uncertain', '不确定匹配', 'uncertain_matches', 'review'],
    ];
    for (const [icon, label, key, tone] of cards) metricCard(overviewGrid, { icon, label, value: data[key], tone });
  }).catch(onFail(() => overviewGrid.append(el('div', '概况读取失败', { class: 'metric-empty' }))));

  const inventory = section('资产清单', view);
  load(inventory, () => api.assets(signal), data => {
    fields(inventory, data, ['total']);
    table(inventory, data.items, [
      { label: '名称', render: row => link(row.name, '/assets/' + encodeURIComponent(row.id)) },
      { label: 'ID', key: 'id' },
      { label: '类型', key: 'asset_type' }, { label: '环境', key: 'environment' },
      { label: '暴露面', key: 'exposure' }, { label: '演示资产', key: 'is_demo' }, { label: '更新时间', key: 'updated_at' },
      { label: '', render: row => link('详情 →', '/assets/' + encodeURIComponent(row.id)) }
    ]);
  }, signal);
}
