"""Owner-bound, idempotent analysis inputs using the existing audit table."""
from uuid import UUID,uuid4
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.enrichment.repository import lock
from app.assistant.storage import IdempotencyConflict
from app.agents.contracts import fingerprint
from app.agents.analysis.schemas import AnalysisRequest,AnalysisContext
from app.agents.analysis.snapshot import AnalysisSnapshotReader
from app.utils.time import utcnow

CONTEXT_TYPE='analysis-context-v1'


class AnalysisContextStore:
    def __init__(self,engine):self.engine=engine

    def capture(self,request,*,actor):
        request=AnalysisRequest.model_validate_json(request.model_dump_json())
        if not isinstance(actor,str) or not 1<=len(actor)<=150:raise ValueError('Authenticated actor required')
        request_hash=fingerprint(request.model_dump(mode='json'))
        with transaction(self.engine) as db:
            lock(db,CONTEXT_TYPE+':'+actor+':'+request.request_key)
            existing=db.scalar(select(m.AgentRun).where(m.AgentRun.agent_type==CONTEXT_TYPE,
                m.AgentRun.actor_principal==actor,m.AgentRun.details['analysis_v1']['request_key'].astext==request.request_key))
            if existing:
                saved=self._decode(existing)
                if saved.request_hash!=request_hash:raise IdempotencyConflict('Analysis request key has different content')
                return saved
            now=utcnow()
            inputs=AnalysisSnapshotReader(self.engine).read(request,actor=actor,evaluation_time=now)
            identity={}
            if request.model_assistance:
                from app.llm.config import ModelConfig,ConfigError
                try:
                    config=ModelConfig.from_env()
                    identity={'provider':config.provider,'model':config.model,'endpoint_hash':fingerprint(config.api_base or 'local'),
                              'structured_mode':config.structured_mode,'token_parameter':config.token_parameter}
                except ConfigError:identity={'configuration':'unavailable'}
            context=AnalysisContext(context_id=uuid4(),owner=actor,request=request,request_hash=request_hash,
                input_snapshot_hash=fingerprint(inputs.model_dump(mode='json')),evaluation_time=now,inputs=inputs,model_identity=identity)
            row=m.AgentRun(id=context.context_id,actor_principal=actor,agent_type=CONTEXT_TYPE,
                user_request='Sealed analysis input snapshot; not an executed agent',status='succeeded',
                started_at=now,finished_at=now,duration_ms=0,context={'kind':'input_snapshot'},
                details={'analysis_v1':{'request_key':request.request_key,'context':context.model_dump(mode='json')}},
                result_summary='Input provenance captured; inspect the separate execution run')
            db.add(row);db.flush()
            return context

    def _decode(self,row):
        value=AnalysisContext.model_validate(row.details['analysis_v1']['context'])
        if value.context_id!=row.id or value.owner!=row.actor_principal or value.request_hash!=fingerprint(value.request.model_dump(mode='json')):
            raise ValueError('Analysis context identity invalid')
        if value.input_snapshot_hash!=fingerprint(value.inputs.model_dump(mode='json')):
            raise ValueError('Analysis input snapshot hash invalid')
        return value

    def read(self,context_id,*,actor):
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(str(context_id)),
                m.AgentRun.agent_type==CONTEXT_TYPE,m.AgentRun.actor_principal==actor))
            if row is None:raise LookupError('Analysis context not found')
            return self._decode(row)
