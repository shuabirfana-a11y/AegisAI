import { pageTitle, section, table, jsonBlock, message, load, link } from '../components.js';

export function reviews(view, { api, signal }) {
  pageTitle(view, '待复核', '对具体 Claim 作有依据的判断；保留原值、原文与每次人工决定。');
  const body = section('复核记录', view);
  load(body, () => api.reviews(signal), data => {
    table(body, data.items, [
      { label: '复核 ID', render: row => link(row.id, '/reviews/' + encodeURIComponent(row.id)) },
      { label: '类型', key: 'review_type' }, { label: '状态', key: 'status' },
      { label: '优先级', key: 'priority' }, { label: '修订', key: 'revision' }, { label: '创建时间', key: 'created_at' },
      { label: '', render: row => link('详情 →', '/reviews/' + encodeURIComponent(row.id)) }
    ]);
    if (data.items?.some(row => row.details?.conflict || row.status === 'open')) message(body, '存在待人工复核记录', 'conflict');
  }, signal);
}
