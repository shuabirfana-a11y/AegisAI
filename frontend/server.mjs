import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const publicRoot = fileURLToPath(new URL('./public/', import.meta.url));
const mimeTypes = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.ico': 'image/x-icon' };
const safeHeaders = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'Cache-Control': 'no-store',
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
};

function json(response, status, detail) {
  response.writeHead(status, { ...safeHeaders, 'Content-Type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify({ detail }));
}

// Only the test harness changes this port. The application entry point fixes it to 8000.
export function createFrontendServer({ backendPort = 8000, localDemoToken = '' } = {}) {
  return http.createServer(async (request, response) => {
    const host = request.headers.host || '';
    if (!/^(127\.0\.0\.1|localhost):[0-9]+$/.test(host)) return json(response, 403, 'Use the local frontend address.');
    if (!request.url?.startsWith('/') || request.url.startsWith('//') || /[\\\r\n]/.test(request.url)) return json(response, 400, 'Invalid local request path.');
    let url;
    try { url = new URL(request.url, 'http://' + host); } catch { return json(response, 400, 'Invalid request URL.'); }
    if (url.pathname === '/client-config') {
      if (request.method !== 'GET') return json(response, 405, 'Method not supported.');
      response.writeHead(200, { ...safeHeaders, 'Content-Type': 'application/json; charset=utf-8' });
      response.end(JSON.stringify({ localDemoAccess: Boolean(localDemoToken) }));
      return;
    }
    const investigationRoute = url.pathname === '/api/investigations' || url.pathname.startsWith('/api/investigations/');
    const api = url.pathname === '/health' || url.pathname.startsWith('/api/v1/') || investigationRoute;
    if (api) {
      if (!['GET', 'HEAD', 'POST'].includes(request.method)) return json(response, 405, 'Method not supported by the skeleton.');
      if (request.method === 'POST') {
        const investigationWrite = url.pathname === '/api/investigations' ||
          /^\/api\/investigations\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/cancel$/i.test(url.pathname);
        if (url.pathname !== '/api/v1/assistant/query' && !investigationWrite) return json(response, 405, 'Only Assistant queries and investigation creation/cancellation are supported.');
        if (request.headers.origin !== 'http://' + host) return json(response, 403, 'Assistant queries require the same frontend origin.');
        if (!/^application\/json(?:\s*;|$)/i.test(request.headers['content-type'] || '')) return json(response, 415, 'Assistant queries require application/json.');
      }
      const headers = { Accept: 'application/json' };
      if (request.headers.authorization) headers.Authorization = request.headers.authorization;
      if (investigationRoute && request.headers['idempotency-key']) headers['Idempotency-Key'] = request.headers['idempotency-key'];
      const protectedDemoRoute = url.pathname === '/api/v1/assets' || url.pathname.startsWith('/api/v1/assets/') ||
        url.pathname === '/api/v1/assistant' || url.pathname.startsWith('/api/v1/assistant/') || investigationRoute;
      if (localDemoToken && protectedDemoRoute) headers.Authorization = 'Bearer ' + localDemoToken;
      if (request.method === 'POST') headers['Content-Type'] = 'application/json';
      let settled = false;
      const upstream = http.request({ hostname: '127.0.0.1', port: backendPort, path: url.pathname + url.search, method: request.method, headers, timeout: 30000 }, incoming => {
        settled = true;
        const acknowledgement = {};
        if (investigationRoute) for (const name of ['location', 'retry-after', 'x-request-id', 'www-authenticate']) {
          if (incoming.headers[name]) acknowledgement[name] = incoming.headers[name];
        }
        response.writeHead(incoming.statusCode || 502, { ...safeHeaders, ...acknowledgement, 'Content-Type': incoming.headers['content-type'] || 'application/json; charset=utf-8' });
        incoming.pipe(response);
      });
      upstream.on('timeout', () => upstream.destroy(new Error('Backend timeout')));
      upstream.on('error', () => { if (!settled && !response.headersSent) json(response, 502, 'Backend unavailable or timed out on 127.0.0.1:8000.'); else response.destroy(); });
      let bytes = 0;
      request.on('data', chunk => {
        if (settled) return;
        bytes += chunk.length;
        if (bytes > 2 * 1024 * 1024) {
          settled = true;
          json(response, 413, 'Request body exceeds 2 MiB.');
          upstream.destroy();
        } else if (!settled) upstream.write(chunk);
      });
      request.on('end', () => { if (!settled) upstream.end(); });
      request.on('aborted', () => upstream.destroy());
      return;
    }
    if (!['GET', 'HEAD'].includes(request.method)) return json(response, 405, 'Static pages are read-only.');
    if (url.pathname === '/favicon.ico') { response.writeHead(204, safeHeaders); response.end(); return; }
    let decoded;
    try { decoded = decodeURIComponent(url.pathname); } catch { return json(response, 400, 'Invalid path encoding.'); }
    if (/[\\\x00]/.test(decoded) || decoded.split('/').some(segment => segment === '..')) return json(response, 400, 'Invalid static path.');
    const isRoute = decoded === '/' || /^\/(dashboard|vulnerabilities|assets|reviews|assistant|system)\/?$/.test(decoded) || /^\/(vulnerabilities|assets|reviews)\/[^/]+\/?$/.test(decoded);
    const target = path.resolve(publicRoot, '.' + (isRoute ? '/index.html' : decoded));
    if (!target.startsWith(path.resolve(publicRoot) + path.sep)) return json(response, 403, 'Invalid static path.');
    try {
      const data = await readFile(target);
      response.writeHead(200, { ...safeHeaders, 'Content-Type': mimeTypes[path.extname(target)] || 'application/octet-stream' });
      response.end(request.method === 'HEAD' ? undefined : data);
    } catch { json(response, 404, 'File not found.'); }
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const localDemoToken = process.env.AEGIS_LOCAL_DEMO === '1' ? process.env.AEGIS_ASSET_TOKEN || '' : '';
  if (process.env.AEGIS_LOCAL_DEMO === '1' && !localDemoToken) {
    process.stderr.write('Local demo requires AEGIS_ASSET_TOKEN.\n');
    process.exit(1);
  }
  const server = createFrontendServer({ localDemoToken });
  server.listen(8769, '127.0.0.1', () => process.stdout.write('AegisAI frontend: http://127.0.0.1:8769/dashboard\nBackend: http://127.0.0.1:8000\n'));
  server.on('error', error => { process.stderr.write(`Frontend startup failed: ${error.code || 'unknown error'}\n`); process.exitCode = 1; });
}
