import { createApi } from './modules/services.js';
import { createSession } from './modules/state.js';
import { attachRouter, resolveRoute } from './modules/router.js';
import { el, pageTitle, message } from './modules/components.js';
import { dashboard } from './modules/pages/dashboard.js';
import { intel } from './modules/pages/intel.js';
import { vulnerabilities, vulnerability } from './modules/pages/vulnerabilities.js';
import { assets } from './modules/pages/assets.js';
import { asset } from './modules/pages/asset.js';
import { reviews } from './modules/pages/reviews.js';
import { review } from './modules/pages/review.js';
import { assistant } from './modules/pages/assistant.js';
import { agents } from './modules/pages/agents.js';
import { knowledge } from './modules/pages/knowledge.js';
import { system } from './modules/pages/system.js';

const session = createSession();
let localDemoAccess = false;
try {
  const response = await fetch('/client-config', { cache: 'no-store', credentials: 'omit' });
  if (response.ok) localDemoAccess = (await response.json()).localDemoAccess === true;
} catch { /* Manual token entry remains available if config cannot be read. */ }
const api = createApi({ getToken: session.getToken, localDemoAccess });
const pages = { dashboard, intel, vulnerabilities, vulnerability, assets, asset, reviews, review, assistant, agents, knowledge, system };
const view = document.querySelector('#view');
let controller;
function render(route) {
  controller?.abort();
  controller = new AbortController();
  view.replaceChildren();
  for (const nav of document.querySelectorAll('nav a')) {
    const active = nav.pathname === location.pathname
      || (route.page === 'vulnerability' && nav.pathname === '/vulnerabilities')
      || (route.page === 'asset' && nav.pathname === '/assets')
      || (route.page === 'review' && nav.pathname === '/reviews');
    if (active) nav.setAttribute('aria-current', 'page');
    else nav.removeAttribute('aria-current');
  }
  const page = pages[route.page];
  if (page) page(view, { api, session, signal: controller.signal, localDemoAccess }, route.params);
  else { pageTitle(view, '页面不存在'); message(view, '请使用上方导航进入支持的页面。', 'error'); }
}

const tokenInput = document.querySelector('#access-token');
const tokenState = document.querySelector('#access-state');
if (localDemoAccess) {
  document.querySelector('#access-form').hidden = true;
  tokenState.className = 'demo-chip';
  tokenState.title = '本机演示模式：无需令牌，数据来自本地 API';
  tokenState.textContent = '演示模式';
}
document.querySelector('#access-form').addEventListener('submit', event => {
  event.preventDefault();
  session.setToken(tokenInput.value);
  tokenInput.value = '';
  tokenState.className = '';
  tokenState.textContent = session.getToken() ? '令牌已设置' : '未设置';
  render(resolveRoute(location.pathname));
});
document.querySelector('#clear-token').addEventListener('click', () => {
  session.setToken(''); tokenInput.value = '';
  tokenState.className = '';
  tokenState.textContent = '令牌已清除';
  render(resolveRoute(location.pathname));
});
const navigate = attachRouter(render);

/* ---------- 顶栏实时时钟 ---------- */
const clockEl = document.querySelector('#header-clock');
if (clockEl) {
  const tick = () => {
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    clockEl.textContent = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  };
  tick();
  setInterval(tick, 1000);
}

/* ---------- Ctrl+K 全局搜索（漏洞 / 资产 / 页面导航） ---------- */
const searchButton = document.querySelector('#global-search');
let searchOpen = false;
let searchController;
function closeSearch() {
  searchOpen = false;
  document.querySelector('#search-modal')?.remove();
  searchController?.abort();
}
function searchResult(label, sub, href) {
  const row = el('button', undefined, { type: 'button', class: 'search-result' });
  row.append(el('span', label, { class: 'search-result-label' }));
  if (sub) row.append(el('span', sub, { class: 'search-result-sub' }));
  row.addEventListener('click', () => { closeSearch(); navigate(href); });
  return row;
}
async function runSearch(term, results) {
  searchController?.abort();
  searchController = new AbortController();
  const signal = searchController.signal;
  const query = term.trim();
  if (!query) {
    results.append(el('div', '输入 CVE 编号、资产名称或页面名称', { class: 'search-hint' }));
    return;
  }
  const loading = el('div', '搜索中…', { class: 'search-hint' });
  results.append(loading);
  const lower = query.toLowerCase();
  try {
    const [vulns, assetsData] = await Promise.allSettled([
      api.vulnerabilitiesPage(signal, { limit: 10, query }),
      api.assets(signal)
    ]);
    if (signal.aborted) return;
    loading.remove();
    if (vulns.status === 'fulfilled' && vulns.value.items?.length) {
      results.append(el('div', '漏洞', { class: 'search-group' }));
      for (const row of vulns.value.items) results.append(searchResult(row.canonical_id || row.id, row.title || '', '/vulnerabilities/' + encodeURIComponent(row.canonical_id || row.id)));
    }
    if (assetsData.status === 'fulfilled') {
      const hits = (assetsData.value.items || []).filter(row => String(row.name || '').toLowerCase().includes(lower)).slice(0, 5);
      if (hits.length) {
        results.append(el('div', '资产', { class: 'search-group' }));
        for (const row of hits) results.append(searchResult(row.name, row.id, '/assets/' + encodeURIComponent(row.id)));
      }
    }
    const pageMatches = [['总览驾驶舱', '/dashboard'], ['情报监测中心', '/intel'], ['漏洞情报', '/vulnerabilities'], ['AI 安全问答', '/assistant'], ['Agent 编排中心', '/agents'], ['知识底座', '/knowledge'], ['资产', '/assets'], ['复核', '/reviews'], ['系统运维', '/system']]
      .filter(([name]) => name.toLowerCase().includes(lower));
    if (pageMatches.length) {
      results.append(el('div', '页面', { class: 'search-group' }));
      for (const [name, href] of pageMatches) results.append(searchResult(name, '', href));
    }
    if (!results.querySelector('.search-result')) results.append(el('div', '没有匹配结果（漏洞搜索仅匹配 CVE 编号）', { class: 'search-hint' }));
  } catch {
    if (!signal.aborted) { loading.textContent = '搜索请求失败'; }
  }
}
function openSearch() {
  if (searchOpen) return;
  searchOpen = true;
  const backdrop = el('div', undefined, { class: 'search-backdrop', id: 'search-modal' });
  const modal = el('div', undefined, { class: 'search-modal', role: 'dialog', 'aria-modal': 'true', 'aria-label': '全局搜索' });
  const input = el('input', undefined, { type: 'search', placeholder: '搜索 CVE、产品或资产', autocomplete: 'off', 'aria-label': '全局搜索' });
  const results = el('div', undefined, { class: 'search-results' });
  const foot = el('div', 'Enter 打开首条 · Esc 关闭', { class: 'search-foot' });
  modal.append(input, results, foot);
  backdrop.append(modal);
  backdrop.addEventListener('click', event => { if (event.target === backdrop) closeSearch(); });
  document.body.append(backdrop);
  input.focus();
  let debounce;
  input.addEventListener('input', () => {
    clearTimeout(debounce);
    results.replaceChildren();
    debounce = setTimeout(() => runSearch(input.value, results), 250);
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); results.querySelector('.search-result')?.click(); }
  });
  runSearch('', results);
}
searchButton.addEventListener('click', openSearch);
window.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); openSearch(); }
  else if (event.key === 'Escape' && searchOpen) { event.preventDefault(); closeSearch(); }
});
