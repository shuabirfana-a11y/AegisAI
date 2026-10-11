"""Explicit acceptance audit; this is not an executed fourth professional Agent."""
from app.integration.contracts import IntegrationTrace
def build_integration_trace(context,result,elapsed_ms):
    return IntegrationTrace(integration_id=result.integration_id,logical_investigation_id=result.logical_investigation_id,
        source_run_ids=result.source_run_ids,artifact_references=result.artifact_references,rule_version=result.policy_version,
        checks=result.checks,evidence_references=result.evidence_references,status=result.status,
        blocking_issues=result.blocking_issues,execution_time_ms=elapsed_ms,
        error_codes=tuple(c.code for c in result.checks if c.blocking=='FATAL'))
