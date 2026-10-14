import { pageTitle, el, section, fields, table, load, jsonBlock, statusChip, onFail, autoTable } from '../components.js';

export function system(view, { api, signal }) {
  pageTitle(view, '系统运行', '来源状态与同步记录分开；失败不会覆盖上次成功时间。');
  const healthHead = el('h3', '健康状态');
  view.append(healthHead);
  const chips = el('div', undefined, { class: 'status-chips' });
  view.append(chips);
  api.health(signal).then(data => {
    statusChip(chips, '应用', data.application);
    statusChip(chips, '数据库', data.database);
    statusChip(chips, '范围', data.scope);
  }).catch(onFail(() => statusChip(chips, '状态', '读取失败')));
  const sources = section('数据来源与最近同步状态', view);
  load(sources, () => api.sources(signal), data => {
    fields(sources, data, ['total']);
    table(sources, data.items, [
      { label: '来源', key: 'source_key' }, { label: '状态', key: 'status' }, { label: '最近成功', key: 'last_success_at' },
      { label: '错误', key: 'latest_error' }, { label: '记录数', key: 'records' },
      { label: '覆盖范围与完整字段', render: row => { const node = document.createElement('div'); jsonBlock(node, row, '展开来源范围'); return node; } }
    ]);
  }, signal);

  const runs = section('同步记录（SyncRun）', view);
  load(runs, () => api.syncRuns(signal), data => {
    fields(runs, data, ['total']);
    autoTable(runs, data.items, { title: '展开同步记录原始字段' });
  }, signal);
}
