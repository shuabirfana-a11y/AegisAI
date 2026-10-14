export class ApiError extends Error {
  constructor(message, { status = 0, kind = 'network' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.kind = kind;
  }
}

export function createApi({ getToken = () => '', fetchImpl = globalThis.fetch, localDemoAccess = false } = {}) {
  async function request(path, { method = 'GET', body, protected: needsToken = false, signal } = {}) {
    if (!(path === '/health' || /^\/api\/v1\//.test(path)) || /[\\\r\n]/.test(path)) {
      throw new ApiError('Only local API paths are allowed.', { kind: 'invalid_request' });
    }
    const headers = { Accept: 'application/json' };
    if (needsToken && !localDemoAccess) {
      const token = getToken();
      if (!token) throw new ApiError('Enter the local asset access token above to load this page.', { status: 401, kind: 'auth' });
      headers.Authorization = 'Bearer ' + token;
    }
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    let response;
    try {
      response = await fetchImpl(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal, credentials: 'omit', cache: 'no-store' });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new ApiError('The API could not be reached. Check that the backend is running on port 8000.');
    }
    let data;
    try { data = await response.json(); }
    catch { throw new ApiError(`The API returned an unreadable response (HTTP ${response.status}).`, { status: response.status, kind: 'invalid_response' }); }
    if (!response.ok) {
      const detail = data?.detail;
      const message = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : `API request failed (HTTP ${response.status}).`;
      const kind = response.status === 409 ? 'conflict' : [401, 403].includes(response.status) ? 'auth' : response.status === 404 ? 'not_found' : response.status === 422 ? 'validation' : 'server';
      throw new ApiError(message, { status: response.status, kind });
    }
    return data;
  }
  const id = value => encodeURIComponent(String(value));
  const read = (path, signal, needsToken = false) => request(path, { signal, protected: needsToken });
  const readPage = async (path, signal, needsToken = false) => {
    const data = await read(path, signal, needsToken);
    if (!Array.isArray(data?.items)) throw new ApiError('The list API response is missing its items array.', { kind: 'invalid_response' });
    return data;
  };
  return {
    request,
    vulnerabilities: (signal, query = '') => readPage('/api/v1/vulnerabilities?limit=20' + (query ? '&q=' + id(query) : ''), signal),
    vulnerabilitiesPage: (signal, { offset = 0, limit = 20, sort = 'modified_desc', query = '' } = {}) => readPage('/api/v1/vulnerabilities?offset=' + offset + '&limit=' + limit + '&sort=' + id(sort) + (query ? '&q=' + id(query) : ''), signal),
    vulnerability: (value, signal) => read('/api/v1/vulnerabilities/' + id(value), signal),
    assets: signal => readPage('/api/v1/assets?limit=100', signal, true),
    overview: signal => read('/api/v1/assets/overview', signal, true),
    assetDetail: (value, signal) => read('/api/v1/assets/' + id(value), signal, true),
    risks: (value, signal) => readPage('/api/v1/assets/' + id(value) + '/risks?limit=100', signal, true),
    riskChanges: (value, signal) => readPage('/api/v1/assets/' + id(value) + '/risk-changes?limit=20', signal, true),
    inventoryHistory: (value, signal) => readPage('/api/v1/assets/' + id(value) + '/inventory-history?limit=20', signal, true),
    assetReviews: (value, signal) => readPage('/api/v1/assets/' + id(value) + '/reviews?limit=20', signal, true),
    sources: signal => readPage('/api/v1/sources', signal),
    syncRuns: signal => readPage('/api/v1/sync-runs?limit=20', signal),
    reviews: signal => readPage('/api/v1/reviews?limit=100', signal),
    reviewDetail: (value, signal) => read('/api/v1/reviews/' + id(value), signal),
    health: signal => read('/health', signal),
    evidence: (value, signal) => read('/api/v1/evidence/' + id(value), signal),
    startRun: async (body, signal) => {
      if (typeof body?.question !== 'string' || !body.question.trim() || body.question.length > 2000) throw new ApiError('Question must contain 1–2000 characters.', { status: 422, kind: 'validation' });
      return request('/api/v1/assistant/query', { method: 'POST', body, signal, protected: true });
    },
    run: (value, signal) => read('/api/v1/assistant/runs/' + id(value), signal, true),
    tasks: (value, signal) => read('/api/v1/assistant/runs/' + id(value) + '/tasks', signal, true),
    trace: (value, signal) => read('/api/v1/assistant/runs/' + id(value) + '/trace', signal, true)
  };
}

const activeStates = new Set(['PLANNING', 'RUNNING', 'WAITING_TOOL', 'VERIFYING', 'REPLANNING']);
export function normalizeRun(data) {
  const status = typeof data?.status === 'string' ? data.status : 'UNKNOWN';
  return { ...data, status, shouldPoll: activeStates.has(status), warnings: Array.isArray(data?.warnings) ? data.warnings : [] };
}
