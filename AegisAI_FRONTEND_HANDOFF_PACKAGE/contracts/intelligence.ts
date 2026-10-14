/** Read-only monitoring transport. Credentials supplied at runtime, never stored. */
import type { SecurityIntelligenceObject, IntelligencePage, SourceStatusPage, AssetRiskPage, POCPage, RecordPage, PipelineRunPage } from '../api/reference/intelligence-http.js';

export class IntelligenceApiError extends Error {
  constructor(public readonly status: number, public readonly detail: unknown) {
    super('Intelligence API request failed: ' + status);
  }
}

export class IntelligenceApiClient {
  constructor(private readonly baseUrl = '', private readonly token: () => string | undefined = () => undefined) {}
  private async call<T>(path: string): Promise<T> {
    const headers = new Headers({ Accept: 'application/json' });
    const token = this.token();
    if (token) headers.set('Authorization', 'Bearer ' + token);
    const response = await fetch(this.baseUrl.replace(/\/$/, '') + '/api/v1/intelligence' + path, { headers });
    const body: unknown = await response.json();
    if (!response.ok) throw new IntelligenceApiError(response.status, body);
    return body as T;
  }
  list(options: { type?: SecurityIntelligenceObject['type']; q?: string; offset?: number; limit?: number } = {}): Promise<IntelligencePage> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(options)) if (value !== undefined) query.set(key, String(value));
    return this.call('?' + query.toString());
  }
  sources(): Promise<SourceStatusPage> { return this.call('/sources'); }
  records(options: { type?: string; q?: string; offset?: number; limit?: number } = {}): Promise<RecordPage> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(options)) if (value !== undefined) query.set(key, String(value));
    return this.call('/records?' + query.toString());
  }
  monitoringRuns(options: { source?: string; offset?: number; limit?: number } = {}): Promise<PipelineRunPage> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(options)) if (value !== undefined) query.set(key, String(value));
    return this.call('/monitoring/runs?' + query.toString());
  }
  vulnerability(id: string): Promise<SecurityIntelligenceObject> { return this.call('/vulnerabilities/' + encodeURIComponent(id)); }
  poc(id: string, offset = 0, limit = 20): Promise<POCPage> {
    return this.call('/vulnerabilities/' + encodeURIComponent(id) + '/poc?' + new URLSearchParams({ offset: String(offset), limit: String(limit) }).toString());
  }
  document(id: string): Promise<SecurityIntelligenceObject> { return this.call('/documents/' + encodeURIComponent(id)); }
  assets(id: string, offset = 0, limit = 20): Promise<AssetRiskPage> {
    return this.call('/vulnerabilities/' + encodeURIComponent(id) + '/assets?' + new URLSearchParams({ offset: String(offset), limit: String(limit) }).toString());
  }
}
