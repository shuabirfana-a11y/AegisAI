/** Phase12-B transport client. No UI, stored credentials, models, or business decisions. */
import type {
  InvestigationCreateRequest, InvestigationCreateResult, InvestigationStatusResponse,
  TraceResponse, ArtifactResponse, IntegrationResponse, AnswerResponse, HistoryResponse,
  ApiError, Overall,
  BatchRequest, BatchResponse,
} from './investigation-http.js';

export class InvestigationApiError extends Error {
  constructor(public readonly status: number, public readonly failure: ApiError) {
    super(failure.message);
  }
}

export class InvestigationApiClient {
  constructor(private readonly baseUrl = '', private readonly token: () => string | undefined = () => undefined) {}

  private async call<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set('Accept', 'application/json');
    const token = this.token();
    if (token) headers.set('Authorization', 'Bearer ' + token);
    const response = await fetch(this.baseUrl.replace(/\/$/, '') + '/api/investigations' + path, { ...init, headers });
    const body: unknown = await response.json();
    if (!response.ok) throw new InvestigationApiError(response.status, body as ApiError);
    return body as T;
  }

  create(request: InvestigationCreateRequest, idempotencyKey: string): Promise<InvestigationCreateResult> {
    return this.call('', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey }, body: JSON.stringify(request) });
  }
  status(id: string): Promise<InvestigationStatusResponse> { return this.call('/' + encodeURIComponent(id) + '/status'); }
  trace(id: string, version?: 1 | 2): Promise<TraceResponse> { return this.call('/' + encodeURIComponent(id) + '/trace' + (version === undefined ? '' : '?version=' + version)); }
  artifacts(id: string, version?: 1 | 2): Promise<ArtifactResponse> { return this.call('/' + encodeURIComponent(id) + '/artifacts' + (version === undefined ? '' : '?version=' + version)); }
  integration(id: string, version?: 1 | 2): Promise<IntegrationResponse> { return this.call('/' + encodeURIComponent(id) + '/integration' + (version === undefined ? '' : '?version=' + version)); }
  answer(id: string, version?: 1 | 2): Promise<AnswerResponse> { return this.call('/' + encodeURIComponent(id) + '/answer' + (version === undefined ? '' : '?version=' + version)); }
  createBatch(request: BatchRequest, idempotencyKey: string): Promise<BatchResponse> {
    return this.call('/batches', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey }, body: JSON.stringify(request) });
  }
  batch(id: string): Promise<BatchResponse> { return this.call('/batches/' + encodeURIComponent(id)); }
  batchSummary(id: string): Promise<BatchResponse> { return this.call('/batches/' + encodeURIComponent(id) + '/summary'); }
  cancelBatch(id: string): Promise<BatchResponse> {
    return this.call('/batches/' + encodeURIComponent(id) + '/cancel', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  }
  cancel(id: string): Promise<InvestigationStatusResponse> {
    return this.call('/' + encodeURIComponent(id) + '/cancel', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  }
  history(options: { offset?: number; limit?: number; status?: Overall; sort?: 'created_desc' | 'created_asc' } = {}): Promise<HistoryResponse> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(options)) if (value !== undefined) query.set(key, String(value));
    return this.call('/history?' + query.toString());
  }
}
