"""Owner-bound, once-only evaluation snapshots using the existing AgentRun table."""
from uuid import UUID,uuid4
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.enrichment.repository import lock
from app.assistant.storage import IdempotencyConflict
from app.agents.contracts import fingerprint
from app.agents.verification.schemas import VerificationRequest,VerificationContext
from app.agents.verification.snapshot import InvestigationSnapshotReader
from app.utils.time import utcnow

CONTEXT_TYPE='verification-context-v1'


class VerificationContextStore:
    def __init__(self,engine):self.engine=engine

    def capture(self,request,*,actor):
        request=VerificationRequest.model_validate_json(request.model_dump_json())
        if not isinstance(actor,str) or not 1<=len(actor)<=150:raise ValueError('Authenticated actor required')
        request_hash=fingerprint(request.model_dump(mode='json'))
        with transaction(self.engine) as db:
            lock(db,CONTEXT_TYPE+':'+actor+':'+request.request_key)
            existing=db.scalar(select(m.AgentRun).where(m.AgentRun.agent_type==CONTEXT_TYPE,
                m.AgentRun.actor_principal==actor,m.AgentRun.details['verification_v1']['request_key'].astext==request.request_key))
            if existing:
                saved=self._decode(existing)
                if saved.request_hash!=request_hash:raise IdempotencyConflict('Verification request key has different content')
                return saved
            now=utcnow()
            snapshot=InvestigationSnapshotReader(self.engine).read(request,actor=actor,evaluation_time=now)
            identity={}
            if request.model_assistance:
                from app.llm.config import ModelConfig,ConfigError
                try:
                    settings=ModelConfig.from_env()
                    identity={'provider':settings.provider,'model':settings.model,
                              'endpoint_hash':fingerprint(settings.api_base or 'local'),
                              'structured_mode':settings.structured_mode,'token_parameter':settings.token_parameter}
                except ConfigError:identity={'configuration':'unavailable'}
            context=VerificationContext(context_id=uuid4(),owner=actor,request=request,request_hash=request_hash,
                source_snapshot_hash=fingerprint(snapshot.model_dump(mode='json')),evaluation_time=now,
                snapshot=snapshot,model_identity=identity)
            row=m.AgentRun(id=context.context_id,actor_principal=actor,agent_type=CONTEXT_TYPE,
                user_request='Sealed verification input snapshot; not an executed agent',status='succeeded',
                started_at=now,finished_at=now,duration_ms=0,context={'kind':'input_snapshot'},
                details={'verification_v1':{'request_key':request.request_key,'context':context.model_dump(mode='json')}},
                result_summary='Input provenance captured; inspect the separate execution run')
            db.add(row);db.flush()
            return context

    def _decode(self,row):
        value=VerificationContext.model_validate(row.details['verification_v1']['context'])
        if value.context_id!=row.id or value.owner!=row.actor_principal or value.request_hash!=fingerprint(value.request.model_dump(mode='json')):
            raise ValueError('Verification context identity invalid')
        if value.source_snapshot_hash!=fingerprint(value.snapshot.model_dump(mode='json')):
            raise ValueError('Verification source snapshot hash invalid')
        return value

    def read(self,context_id,*,actor):
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(str(context_id)),
                m.AgentRun.agent_type==CONTEXT_TYPE,m.AgentRun.actor_principal==actor))
            if row is None:raise LookupError('Verification context not found')
            return self._decode(row)
