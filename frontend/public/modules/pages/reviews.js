import { pageTitle, section, fields, table, jsonBlock, message, load } from '../components.js';

export function reviews(view, { api, signal }) {
  pageTitle(view, 'Human Review', '只读复核列表；这里读取现有 /reviews API，该 API 不包含受保护的资产匹配复核。');
  const body = section('复核记录（最多 20 条）', view);
  load(body, () => api.reviews(signal), data => {
    fields(body, data, ['total', 'offset', 'limit']);
    table(body, data.items, [
      { label: '复核 ID', key: 'id' }, { label: '类型', key: 'review_type' }, { label: '状态', key: 'status' },
      { label: '优先级', key: 'priority' }, { label: '修订', key: 'revision' }, { label: '创建时间（原值）', key: 'created_at' },
      { label: '详细字段', render: row => { const holder = document.createElement('div'); jsonBlock(holder, row, '展开复核'); return holder; } }
    ]);
    if (data.items?.some(row => row.details?.conflict || row.status === 'open')) message(body, '待人工复核的记录保持原始状态；此页面不会自动决议。');
  }, signal);
}
