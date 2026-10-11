import { pageTitle, section, fields, table, load, jsonBlock } from '../components.js';

export function system(view, { api, signal }) {
  pageTitle(view, '系统', 'Backend: 127.0.0.1:8000 · Frontend: 127.0.0.1:8769 · 原型端口 8768 保留。');
  const health = section('健康状态', view);
  load(health, () => api.health(signal), data => fields(health, data, Object.keys(data)), signal);
  const sources = section('数据来源与最近同步状态', view);
  load(sources, () => api.sources(signal), data => {
    fields(sources, data, ['total', 'status_semantics']);
    table(sources, data.items, [
      { label: '来源', key: 'source_key' }, { label: '状态', key: 'status' }, { label: '最近成功（原值）', key: 'last_success_at' },
      { label: '错误', key: 'latest_error' }, { label: '记录数', key: 'records' },
      { label: '覆盖范围与完整字段', render: row => { const node = document.createElement('div'); jsonBlock(node, row, '展开来源范围'); return node; } }
    ]);
  }, signal);
}
