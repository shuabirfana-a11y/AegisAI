import { pageTitle, section, fields, load, message, link } from '../components.js';

export function dashboard(view, { api, signal }) {
  pageTitle(view, 'Dashboard', '所有数量来自当前本地 API；空结果和未知状态不会被补成示例数据。');
  const health = section('服务状态', view);
  load(health, () => api.health(signal), data => fields(health, data, ['application', 'database', 'scope']), signal);
  const overview = section('当前访问范围的资产概况', view);
  load(overview, () => api.overview(signal), data => fields(overview, data, Object.keys(data)), signal);
  const vulns = section('漏洞记录', view);
  load(vulns, () => api.vulnerabilities(signal), data => { fields(vulns, data, ['total', 'data_status', 'coverage']); vulns.append(link('查看漏洞', '/vulnerabilities')); }, signal);
  const reviews = section('复核记录', view);
  load(reviews, () => api.reviews(signal), data => { fields(reviews, data, ['total']); reviews.append(link('查看复核', '/reviews')); }, signal);
  message(view, '数据库时间原样展示；来源断言、UNKNOWN、PENDING、CONFLICT 与过期快照均保留。');
}
