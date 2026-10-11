"""Read the exact historical Gate revision, never refresh or recalculate sources."""
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.integration.store import decode,TYPE
from app.orchestration.handoff import artifact_ref


class AnswerSourcesLoader:
    def __init__(self,engine):self.engine=engine

    def load(self,context,*,actor):
        if context.owner!=actor or context.integration_result_id is None:raise LookupError('Answer source not available')
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==context.integration_result_id,
                m.AgentRun.actor_principal==actor,m.AgentRun.agent_type==TYPE))
            if row is None:raise LookupError('Answer source not available')
            source,gate,trace=decode(row,actor)
        expected={ref.schema_version:ref for ref in context.artifact_references}
        actual={ref.schema_version:ref for ref in (source.request.investigation,source.request.verification,source.request.analysis) if ref}
        if (actual!=expected or source.request.run_id!=context.investigation_run_id or
            source.request.planner_run_id!=context.planner_run_id or source.request.request_key!=context.stage_keys['integration'] or
            source.request.objective_profile!=context.resolved_scope.objective_profile or
            source.request.objective_source!=context.resolved_scope.objective_source or
            gate.logical_investigation_id!=context.gate_logical_investigation_id or
            gate.input_hash!=context.gate_input_hash or gate.objective_hash!=context.objective_hash):
            raise ValueError('ANSWER_GATE_BINDING_INVALID')
        if source.objective and source.objective!=context.resolved_scope.objective:
            raise ValueError('ANSWER_OBJECTIVE_BINDING_INVALID')
        for art,id in ((source.investigation,context.investigation_run_id),(source.verification,context.verification_run_id),(source.analysis,context.analysis_run_id)):
            if art and (art.run_id!=id or artifact_ref(art)!=expected.get(art.schema_version)):
                raise ValueError('ANSWER_ARTIFACT_BINDING_INVALID')
        return source,gate,trace
