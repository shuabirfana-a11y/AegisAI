const fields = ['id', 'task_id', 'agent', 'status', 'state', 'at', 'summary', 'result_summary', 'goal', 'task_type', 'dependencies', 'tool_name', 'sequence_no', 'attempt', 'started_at', 'finished_at', 'duration_ms', 'evidence_refs', 'warnings', 'errors', 'retry_count'];
const outputFields = ['status', 'duration_ms', 'evidence_refs', 'warnings', 'errors'];

export function auditSummary(row) {
  const value = Object.fromEntries(fields.filter(key => row[key] !== undefined).map(key => [key, row[key]]));
  if (row.output_summary && typeof row.output_summary === 'object') value.output_summary = Object.fromEntries(outputFields.filter(key => row.output_summary[key] !== undefined).map(key => [key, row.output_summary[key]]));
  return value;
}
