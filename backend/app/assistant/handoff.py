from app.assistant.contracts import TaskArtifact
from app.tooling.attestation import claim_key,evidence_key

def validate_handoff(task,value,trace_id,accepted,*,evidence_attested=None,claims_attested=frozenset()):
    value=TaskArtifact.model_validate(value)
    if value.task_id!=task.task_id or value.trace_id!=trace_id or value.agent!=task.task_type:raise ValueError('Handoff identity mismatch')
    if value.status not in ('success','partial'):raise ValueError('Terminal failure cannot satisfy a dependency')
    if any(dep not in accepted or accepted[dep].status not in ('success','partial') for dep in task.dependencies):raise ValueError('Dependency not accepted')
    if task.evidence_required and not value.evidence_refs:raise ValueError('Evidence required')
    for ref in value.evidence_refs:
        if not ref.get('raw_document_id') or not ref.get('url') or not isinstance(ref.get('locator'),dict):raise ValueError('Evidence provenance incomplete')
        from uuid import UUID
        UUID(ref['raw_document_id'])
        if evidence_attested is not None and evidence_key(ref) not in evidence_attested:raise ValueError('Evidence not in gateway receipts')
    if any(c.get('verification_status')=='CONFIRMED' and claim_key(c) not in claims_attested for c in value.claims):raise ValueError('Claim not in gateway receipts')
    return value
