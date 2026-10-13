"""Immutable conflict observations derived only from the selected source artifact."""
from typing import Literal
from uuid import UUID,uuid5,NAMESPACE_URL
from pydantic import Field
from app.runtime.contracts import FrozenModel
from app.agents.asset_observations import InvestigationArtifactReference
from app.agents.contracts import fingerprint


class ConflictEvidenceSource(FrozenModel):
    evidence_id:str
    claim_id:str
    source_id:UUID
    raw_document_id:UUID|None
    observation_id:UUID|None
    hash:str|None
    reference_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')


class ConflictEvidenceArtifact(FrozenModel):
    artifact_id:UUID
    type:Literal['CONFLICT_EVIDENCE']='CONFLICT_EVIDENCE'
    schema_version:Literal['conflict-evidence-artifact-v1']='conflict-evidence-artifact-v1'
    source_artifact:InvestigationArtifactReference
    conflict_reason:str=Field(max_length=500)
    conflict_index:int=Field(ge=0)
    conflict_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
    sources:tuple[ConflictEvidenceSource,...]=Field(default=(),max_length=128)
    information_status:Literal['CANDIDATE']='CANDIDATE'
    unresolved_items:tuple[str,...]=()


def conflict_artifacts(artifact,evidence):
    conflicts=artifact.get('conflicts') or []
    if not conflicts:return ()
    parent=InvestigationArtifactReference(run_id=artifact['run_id'],task_id=artifact['task_id'],
        artifact_id=artifact['artifact_id'])
    result=[]
    for index,conflict in enumerate(conflicts[:32]):
        ids={str(value) for key in ('claim_a_id','claim_b_id') if (value:=conflict.get(key))}
        ids.update(str(conflict[key]['id']) for key in ('claim_a','claim_b')
                   if isinstance(conflict.get(key),dict) and conflict[key].get('id'))
        sources=tuple(ConflictEvidenceSource(evidence_id=e.evidence_id,claim_id=e.claim_id,source_id=e.source_id,
            raw_document_id=e.raw_document_id,observation_id=e.observation_id,hash=e.hash,
            reference_sha256=fingerprint(e.reference)) for e in evidence if e.claim_id in ids)
        unresolved=[]
        if not ids or not ids<={s.claim_id for s in sources}:unresolved.append('CONFLICT_SOURCE_EVIDENCE_INCOMPLETE')
        if len(conflicts)>32:unresolved.append('CONFLICT_ARTIFACT_LIMIT: remaining records retained in parent')
        result.append(ConflictEvidenceArtifact(artifact_id=uuid5(NAMESPACE_URL,
            'aegis-conflict:'+fingerprint([parent.model_dump(mode='json'),conflict])),source_artifact=parent,
            conflict_reason=str(conflict.get('conflict_type') or 'SOURCE_CONFLICT')[:500],
            conflict_index=index,conflict_sha256=fingerprint(conflict),sources=sources,unresolved_items=tuple(unresolved)))
    return tuple(result)
