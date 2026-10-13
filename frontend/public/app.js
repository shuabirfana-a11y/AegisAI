import { createApi } from './modules/services.js';
import { createSession } from './modules/state.js';
import { attachRouter, resolveRoute } from './modules/router.js';
import { el, pageTitle, message } from './modules/components.js';
import { dashboard } from './modules/pages/dashboard.js';
import { vulnerabilities, vulnerability } from './modules/pages/vulnerabilities.js';
import { assets } from './modules/pages/assets.js';
import { reviews } from './modules/pages/reviews.js';
import { assistant } from './modules/pages/assistant.js';
import { system } from './modules/pages/system.js';

const session = createSession();
let localDemoAccess = false;
try {
  const response = await fetch('/client-config', { cache: 'no-store', credentials: 'omit' });
  if (response.ok) localDemoAccess = (await response.json()).localDemoAccess === true;
} catch { /* Manual token entry remains available if config cannot be read. */ }
const api = createApi({ getToken: session.getToken, localDemoAccess });
const pages = { dashboard, vulnerabilities, vulnerability, assets, reviews, assistant, system };
const view = document.querySelector('#view');
let controller;
function render(route) {
  controller?.abort();
  controller = new AbortController();
  view.replaceChildren();
  for (const nav of document.querySelectorAll('nav a')) {
    if (nav.pathname === location.pathname || (route.page === 'vulnerability' && nav.pathname === '/vulnerabilities')) nav.setAttribute('aria-current', 'page');
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
  tokenState.textContent = '本机演示模式已启用';
}
document.querySelector('#access-form').addEventListener('submit', event => {
  event.preventDefault();
  session.setToken(tokenInput.value);
  tokenInput.value = '';
  tokenState.textContent = session.getToken() ? '令牌已设置（仅内存）；刷新页面即清除' : '未设置；刷新页面后需要重新输入';
  render(resolveRoute(location.pathname));
});
document.querySelector('#clear-token').addEventListener('click', () => {
  session.setToken(''); tokenInput.value = '';
  tokenState.textContent = '令牌已清除';
  render(resolveRoute(location.pathname));
});
attachRouter(render);
