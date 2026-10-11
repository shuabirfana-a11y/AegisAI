import test from 'node:test';
import assert from 'node:assert/strict';
import { auditSummary } from '../public/modules/audit.js';

test('backend tool attempts and output status are visible while hidden reasoning is excluded', () => {
  const row = auditSummary({ tool_name: 'semantic_search', status: 'succeeded', sequence_no: 2, attempt: 1,
    chain_of_thought: 'hidden', output_summary: { status: 'success', warnings: ['source assertion'], evidence_refs: [{ raw_document_id: 'real-doc' }], data: { chain_of_thought: 'hidden nested content' } } });
  assert.equal(row.sequence_no, 2);
  assert.equal(row.attempt, 1);
  assert.equal(row.output_summary.status, 'success');
  assert.deepEqual(row.output_summary.evidence_refs, [{ raw_document_id: 'real-doc' }]);
  assert.equal('chain_of_thought' in row, false);
  assert.equal('data' in row.output_summary, false);
});

test('real trace event state and timestamp remain auditable', () => {
  assert.deepEqual(auditSummary({ task_id: 'root', state: 'started', at: '2026-10-06T14:00:00Z', chain_of_thought: 'hidden' }), { task_id: 'root', state: 'started', at: '2026-10-06T14:00:00Z' });
});
