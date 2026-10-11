"""Deterministic global verdict; no tools, model, domain recalculation or writes."""
from app.integration.contracts import IntegrationContext,IntegrationResult,GateCheck
from app.integration.registry import registered_checks
from app.integration.rules_common import decision,check
from app.integration.objective import coverage
from app.integration.redaction import public_reference,public_lineage

def assemble(c,checks):
    warning=tuple(dict.fromkeys(ch.code for ch in checks if ch.outcome=='WARNING'))
    blockers=tuple(dict.fromkeys(ch.code for ch in checks if ch.blocking!='NONE'))
    status=decision([ch.blocking for ch in checks],bool(warning))
    refs=tuple(ref for ref,art in ((c.request.investigation,c.investigation),(c.request.verification,c.verification),(c.request.analysis,c.analysis)) if ref and art)
    evidence=[]
    if c.verification:
        seen=set()
        for e in (*c.verification.supporting_evidence,*c.verification.conflicting_evidence):
            if e.evidence_id in seen:continue
            seen.add(e.evidence_id)
            evidence.append({'evidence_id':e.evidence_id,'claim_id':e.claim_id,'hash':e.hash,'reference':public_reference(e.reference),
                'lineage_key':public_lineage(e.lineage_key),'verification_artifact_id':str(c.verification.artifact_id)})
    return IntegrationResult(integration_id=c.integration_id,logical_investigation_id=c.logical_investigation_id,trace_id=c.integration_id,
        run_id=c.request.run_id or (c.investigation.run_id if c.investigation else None),source_run_ids=c.source_run_ids,status=status,
        objective_coverage=coverage(c),task_completion_summary=c.tasks,checks=tuple(checks),
        passed_checks=tuple(ch.code for ch in checks if ch.outcome=='PASS'),failed_checks=tuple(ch.code for ch in checks if ch.outcome in ('BLOCKED','ERROR')),
        blocking_issues=blockers,warnings=warning,unresolved_items=tuple(dict.fromkeys((*blockers,*warning))),
        artifact_references=refs,evidence_references=tuple(evidence),
        replan_reasons=tuple(dict.fromkeys(ch.code for ch in checks if ch.blocking=='REPLAN')),
        human_review_reasons=tuple(dict.fromkeys(ch.code for ch in checks if ch.blocking=='HUMAN')),
        final_result_references=refs if status in ('PASS','PASS_WITH_WARNINGS') else (),
        partial_result_references=refs if status not in ('PASS','PASS_WITH_WARNINGS') else (),
        input_hash=c.input_hash,objective_hash=c.objective_hash,policy_version=c.policy_version,created_at=c.evaluation_time,evaluation_time=c.evaluation_time)

class IntegrationGateEvaluator:
    def evaluate(self,context):
        try:
            # Inspect Python Any values before JSON serializers can turn NaN/Inf
            # into null; then deeply revalidate all nested protocol instances.
            IntegrationContext.model_validate(context.model_dump(mode='python'))
            c=IntegrationContext.model_validate_json(context.model_dump_json())
        except (ValueError,TypeError):
            # Preserve identity from the internal container, without reading its
            # corrupted business fields to compute any final security result.
            c=context.model_copy(update={'investigation':None,'verification':None,'analysis':None,'verification_source':None,'asset_snapshot':None,'objective':None})
            checks=[check('integrity','RESULT_CONTRACT_INCONSISTENT','Malformed internal context/artifact','FATAL')]
            checks.extend(GateCheck(gate=name,code='UNUSABLE_INPUT',outcome='NOT_APPLICABLE',message='Critical input invalid') for name,_ in registered_checks() if name!='integrity')
            return assemble(c,checks)
        checks=list(c.capture_checks)
        for name,rule in registered_checks():
            checks.extend(rule(c))
        return assemble(c,checks)
