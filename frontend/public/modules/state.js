export function createSession() {
  let token = '';
  let runId = null;
  return {
    getToken: () => token,
    setToken(value) { token = String(value ?? '').trim(); runId = null; },
    getRunId: () => runId,
    setRunId(value) { runId = value || null; }
  };
}
