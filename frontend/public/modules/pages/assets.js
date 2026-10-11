import { pageTitle, el, section, fields, table, link, load, jsonBlock, message } from '../components.js';

export function assets(view, { api, signal }) {
  pageTitle(view, '资产', '资产属于后端已配置的访问主体。演示资产会保留 is_demo 标记。');
  const overview = section('资产概况', view);
  load(overview, () => api.overview(signal), data => fields(overview, data, Object.keys(data)), signal);
  const inventory = section('资产清单（最多 20 条）', view);
  const risks = section('选中资产的风险（最多 20 条）', view);
  message(risks, '选择一个资产读取已保存的风险快照。', 'empty');
  let generation = 0;
  function showRisks(assetId, name) {
    const current = ++generation;
    risks.replaceChildren(el('h2', '资产风险：' + name));
    load(risks, () => api.risks(assetId, signal), data => {
      if (current !== generation) return;
      fields(risks, data, ['total', 'offset', 'limit', 'coverage']);
      if (data.items?.some(row => row.verification_status === 'CONFLICT' || row.match_status === 'UNCERTAIN')) message(risks, 'Conflict / 存在冲突或未确定的版本匹配；请查看证据与 match_explanation。', 'conflict');
      table(risks, data.items, [
        { label: '漏洞', render: row => link(row.canonical_id || row.vulnerability_id, '/vulnerabilities/' + encodeURIComponent(row.canonical_id || row.vulnerability_id)) },
        { label: '组件', key: 'component_name' }, { label: '安装版本', key: 'installed_version' },
        { label: '匹配', key: 'match_status' }, { label: '确认状态', key: 'verification_status' },
        { label: '优先级', key: 'priority' }, { label: '快照过期', key: 'is_stale' }, { label: '评估时间（原值）', key: 'evaluated_at' },
        { label: 'POC / KEV / 修复 / Evidence', render: row => {
          const node = el('div');
          jsonBlock(node, { poc: row.poc, kev: row.kev, remediation: row.remediation, evidence_refs: row.evidence_refs, match_explanation: row.match_explanation, why_now: row.why_now }, '展开状态、证据与原因');
          return node;
        } }
      ]);
    }, signal);
  }
  load(inventory, () => api.assets(signal), data => {
    fields(inventory, data, ['total', 'offset', 'limit']);
    table(inventory, data.items, [
      { label: '名称', key: 'name' }, { label: '类型', key: 'asset_type' }, { label: '环境', key: 'environment' },
      { label: '暴露面', key: 'exposure' }, { label: '演示资产', key: 'is_demo' }, { label: '更新时间（原值）', key: 'updated_at' },
      { label: '风险', render: row => {
        const button = el('button', '读取风险', { type: 'button' });
        button.addEventListener('click', () => showRisks(row.id, row.name)); return button;
      } }
    ]);
    const selected = new URLSearchParams(location.search).get('asset');
    if (selected) {
      const row = data.items?.find(item => item.id === selected);
      showRisks(selected, row?.name || selected);
    }
  }, signal);
}
