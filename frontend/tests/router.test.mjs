import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveRoute } from '../public/modules/router.js';

test('all requested page routes resolve and detail identifiers are decoded', () => {
  for (const page of ['dashboard', 'vulnerabilities', 'assets', 'reviews', 'assistant', 'system']) {
    assert.equal(resolveRoute(`/${page}`).page, page);
  }
  assert.deepEqual(resolveRoute('/vulnerabilities/CVE-2025-32434'), { page: 'vulnerability', params: { id: 'CVE-2025-32434' } });
  assert.deepEqual(resolveRoute('/'), { page: 'dashboard', params: {} });
});

test('unknown and malformed paths produce the not-found route without throwing', () => {
  assert.equal(resolveRoute('/anything').page, 'notFound');
  assert.equal(resolveRoute('/vulnerabilities/%zz').page, 'notFound');
  assert.equal(resolveRoute('/vulnerabilities/a/b').page, 'notFound');
});
