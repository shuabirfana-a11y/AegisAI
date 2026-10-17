/** Phase 12-B 调查 HTTP 客户端（investigations.ts 的浏览器端等价实现）。只做传输，不做业务判定。 */
export class InvestigationApiError extends Error {
  constructor(message, { status = 0, kind = 'network', code = null, requestId = null, retryable = false, retryAfter = null } = {}) {
    super(message);
    this.name = 'InvestigationApiError';
    this.status = status;
    this.kind = kind;
    this.code = code;
    this.requestId = requestId;
    this.retryable = retryable;
    this.retryAfter = retryAfter;
  }
}

export function retryDelayMs(error, minimum = 1000) {
  const seconds = Number.isFinite(error?.retryAfter) && error.retryAfter > 0 ? error.retryAfter : 0;
  return Math.max(seconds * 1000, minimum);
}

function parseRetryAfter(header) {
  if (!header) return null;
  const seconds = Number(header);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

export function createInvestigationClient({ baseUrl = '', getToken = () => '', localDemoAccess = false, fetchImpl = globalThis.fetch } = {}) {
  async function call(path, { method = 'GET', body, headers: extraHeaders, signal } = {}) {
    const headers = { Accept: 'application/json', ...extraHeaders };
    if (!localDemoAccess) {
      const token = getToken();
      if (token) headers.Authorization = 'Bearer ' + token;
    }
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    let response;
    try {
      response = await fetchImpl(baseUrl.replace(/\/$/, '') + '/api/investigations' + path, {
        method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal, credentials: 'omit', cache: 'no-store'
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new InvestigationApiError('无法连接调查 API；请确认后端与本地代理（8769 → 8000）已启动。');
    }
    const retryAfter = parseRetryAfter(response.headers?.get?.('retry-after'));
    let data;
    try { data = await response.json(); }
    catch {
      throw new InvestigationApiError(`调查 API 返回了不可解析的响应（HTTP ${response.status}）。`, { status: response.status, kind: 'invalid_response', retryAfter });
    }
    if (!response.ok) {
      const failure = data && typeof data === 'object' ? data : null;
      throw new InvestigationApiError(failure?.message || `调查 API 请求失败（HTTP ${response.status}）。`, {
        status: response.status, kind: 'http', code: failure?.error_code || null,
        requestId: failure?.request_id || null, retryable: failure?.retryable === true || response.status === 429 || response.status === 503, retryAfter
      });
    }
    return data;
  }
  const idOf = value => encodeURIComponent(String(value));
  const versionQuery = value => value === undefined ? '' : '?version=' + (value === 1 || value === 2 ? value : (() => { throw new InvestigationApiError('非法结果版本。', { kind: 'invalid_request' }); })());
  return {
    isMock: false,
    create(request, idempotencyKey, signal) {
      const question = typeof request?.user_query === 'string' ? request.user_query.trim() : '';
      if (!question || question.length > 2000) throw new InvestigationApiError('问题必须包含 1–2000 个字符。', { status: 422, kind: 'invalid_request' });
      if (!idempotencyKey) throw new InvestigationApiError('缺少幂等键；必须为同一请求提供稳定键。', { status: 422, kind: 'invalid_request' });
      return call('', { method: 'POST', body: { ...request, user_query: question }, headers: { 'Idempotency-Key': idempotencyKey }, signal });
    },
    status: (id, signal) => call('/' + idOf(id) + '/status', { signal }),
    trace: (id, signal, version) => call('/' + idOf(id) + '/trace' + versionQuery(version), { signal }),
    artifacts: (id, signal, version) => call('/' + idOf(id) + '/artifacts' + versionQuery(version), { signal }),
    integration: (id, signal, version) => call('/' + idOf(id) + '/integration' + versionQuery(version), { signal }),
    answer: (id, signal, version) => call('/' + idOf(id) + '/answer' + versionQuery(version), { signal }),
    cancel: (id, signal) => call('/' + idOf(id) + '/cancel', { method: 'POST', body: {}, signal }),
    history(options = {}, signal) {
      const query = new URLSearchParams();
      for (const [key, value] of Object.entries(options)) if (value !== undefined && value !== null) query.set(key, String(value));
      return call('/history?' + query.toString(), { signal });
    }
  };
}
