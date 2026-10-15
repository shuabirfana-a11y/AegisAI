"""Deterministic admission, never text matching or model permission decisions."""
from uuid import UUID
from app.agents.contracts import fingerprint
from app.integration.contracts import ArtifactRef
from app.orchestration.answer_sources import AnswerSourcesLoader
from app.orchestration.handoff import artifact_ref
from app.investigation_api.multi_asset_repository import snapshot, BatchRepository
from app.orchestration.supplement.contracts import SupplementSpec
from app.db.session import transaction

REPLAN_CODES=frozenset({'OBJECTIVE_NOT_COVERED','REQUIRED_TASK_INCOMPLETE','REQUIRED_DETERMINATION_UNAVAILABLE','UNRESOLVED_ANALYSIS'})
KINDS=frozenset({'AFFECTS_VERSION','FIXED_VERSION','CVSS_SCORE'})

def inventory(engine,context,actor):
    p=context.resolved_scope.planner_input
    if not p.query.asset_id or not p.component_id or not p.component or not p.component.version:
        raise ValueError('NEED_CONTEXT')
    with transaction(engine) as db:
        snap=snapshot(db,p.query.asset_id,actor,selected=p.component_id)
    component=next((c for c in snap.components if c.component_id==p.component_id),None)
    if component is None or component.version!=p.component.version or component.package_name!=p.component.package_name:
        raise ValueError('INVENTORY_CHANGED')
    return snap

def batch_scope(engine,context,actor):
    key=context.original_request.request_key
    if not key.startswith('batch:'):return None
    parts=key.split(':')
    if len(parts)!=4 or parts[2]!='asset':raise ValueError('BATCH_SCOPE_INVALID')
    id=UUID(parts[1]);record=BatchRepository(engine).read(id,actor)
    item=next((i for i in record.response.items if i.child_request_key==key),None)
    if item is None or item.snapshot.asset_id!=context.resolved_scope.planner_input.query.asset_id:
        raise ValueError('BATCH_SCOPE_INVALID')
    if record.response.cancel_requested_at:raise ValueError('CANCELLED')
    return id

def decide(engine,original,actor):
    c=original.context
    if c.owner!=actor:raise PermissionError('OWNER_MISMATCH')
    if not original.answer or original.answer.integration_status!='REPLAN_REQUIRED':return None,'GATE_NOT_REPLAN'
    source,gate,_=AnswerSourcesLoader(engine).load(c,actor=actor)
    if any(ch.blocking in ('HUMAN','FATAL') for ch in gate.checks):return None,'HUMAN_OR_FATAL'
    blocked=[ch for ch in gate.checks if ch.blocking=='REPLAN']
    if not blocked or any(ch.code not in REPLAN_CODES for ch in blocked):return None,'UNSUPPORTED_GAP'
    if not any(ch.code=='OBJECTIVE_NOT_COVERED' and ch.objective=='version_impact' for ch in blocked):
        return None,'NO_VERSION_EVIDENCE_GAP'
    inv,ver=source.investigation,source.verification
    if not inv or not ver or inv.partial_result or ver.partial_result or inv.failed_tools or inv.conflicts or ver.conflicts:
        return None,'INCOMPLETE_OR_CONFLICTING_SOURCE'
    if any(t.error_codes for t in source.tasks):return None,'EXECUTION_ERROR'
    if not source.verification_source or not source.verification_source.version_observations:return None,'NEED_CONTEXT'
    snap=inventory(engine,c,actor);obs=source.verification_source.version_observations[0]
    selected=next(i for i in snap.components if i.component_id==snap.selected_component_id)
    if (obs.version!=selected.version or obs.inventory_revision!=selected.inventory_revision or
        obs.exposure!=snap.exposure or obs.environment!=snap.environment):return None,'INVENTORY_CHANGED'
    gaps=[]
    for assessment in ver.claims:
        claim=assessment.claim
        if assessment.status=='CONFIRMED':continue
        if (assessment.status not in ('PENDING','INSUFFICIENT_EVIDENCE') or claim.origin!='stored' or
                claim.claim_type not in KINDS or claim.evidence_ids):return None,'NO_UNREAD_EVIDENCE_ENTRY'
        try:UUID(claim.claim_id)
        except ValueError:return None,'DERIVED_CLAIM_NOT_QUERYABLE'
        gaps.append(claim.claim_id)
    if not gaps or len(gaps)>3:return None,'GAP_LIMIT_OR_NO_GAP'
    if not any(a.claim.claim_type=='AFFECTS_VERSION' and a.claim.claim_id in gaps for a in ver.claims):
        return None,'NO_IMPACT_CLAIM'
    from sqlalchemy import select
    from app.db import models as m
    with transaction(engine) as db:
        for call in db.scalars(select(m.ToolCallRecord).where(m.ToolCallRecord.agent_run_id==c.investigation_run_id)):
            if call.tool_name=='get_evidence' and str(call.input_summary.get('claim_id')) in gaps:
                return None,'QUERY_ALREADY_ATTEMPTED'
    from app.agents.verification.context_store import VerificationContextStore
    with transaction(engine) as db:
        run=db.get(m.AgentRun,c.verification_run_id)
        vc=VerificationContextStore(engine).read(run.details['runtime_v1']['plan']['route']['verification_v1']['context_id'],actor=actor)
    extras=tuple(ArtifactRef(**r.model_dump(),schema_version='investigation-artifact-v1') for r in vc.request.supporting_artifacts)
    return SupplementSpec(parent_investigation_id=c.logical_investigation_id,parent_integration_id=gate.integration_id,
        parent_gate_hash=gate.input_hash,source_artifact=artifact_ref(inv),supporting_artifacts=extras,
        target=inv.canonical_id,claim_ids=tuple(sorted(gaps)),inventory_hash=snap.inventory_hash,
        gap_hash=fingerprint([gate.integration_id.hex,gate.input_hash,sorted(gaps),snap.inventory_hash]),
        batch_id=batch_scope(engine,c,actor)),'ELIGIBLE_UNREAD_CLAIM_EVIDENCE'
