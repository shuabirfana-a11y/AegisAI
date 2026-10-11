const pages = new Set(['dashboard', 'vulnerabilities', 'assets', 'reviews', 'assistant', 'system']);

export function resolveRoute(pathname = '/') {
  if (pathname === '/') return { page: 'dashboard', params: {} };
  const normalized = pathname.replace(/\/$/, '');
  const name = normalized.slice(1);
  if (pages.has(name)) return { page: name, params: {} };
  const detail = /^\/vulnerabilities\/([^/]+)$/.exec(normalized);
  if (detail) {
    try {
      const id = decodeURIComponent(detail[1]);
      if (id && !/[\/\\\x00-\x1f]/.test(id)) return { page: 'vulnerability', params: { id } };
    } catch { /* Invalid URL encoding becomes the not-found page. */ }
  }
  return { page: 'notFound', params: {} };
}

export function attachRouter(render) {
  const navigate = path => { history.pushState(null, '', path); render(resolveRoute(location.pathname)); };
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-route]');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const url = new URL(link.href);
    if (url.origin !== location.origin) return;
    event.preventDefault();
    navigate(url.pathname + url.search);
  });
  window.addEventListener('popstate', () => render(resolveRoute(location.pathname)));
  if (location.pathname === '/') history.replaceState(null, '', '/dashboard');
  render(resolveRoute(location.pathname));
  return navigate;
}
