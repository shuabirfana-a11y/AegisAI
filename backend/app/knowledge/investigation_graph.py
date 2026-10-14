"""Adapt existing immutable Agent/Gate/Answer artifacts, without running Agents."""
from app.orchestration.store import PostgresInvestigationStore
from app.orchestration.reader import InvestigationReader
from app.orchestration.answer_sources import AnswerSourcesLoader
from app.investigation_api.projection import public_copy


def load_linked_investigation(engine,id,actor):
    result=InvestigationReader(PostgresInvestigationStore(engine)).read(id,actor=actor)
    context=result.context
    if not context.integration_result_id:raise LookupError('Investigation has no saved Integration result')
    source,gate,_=AnswerSourcesLoader(engine).load(context,actor=actor)
    investigation=source.investigation
    if investigation is None:raise LookupError('Investigation artifact unavailable')
    answer=result.answer
    references=[{'agent':a.agent_id,'run_id':str(a.run_id),'artifact_id':str(a.artifact_id),'schema_version':a.schema_version}
        for a in (source.investigation,source.verification,source.analysis) if a]
    return public_copy({'vulnerability_id':investigation.vulnerability_id,'canonical_id':investigation.canonical_id,
        'investigation_id':str(id),'agent_references':references,'gate_status':gate.status,'integration_id':str(gate.integration_id),
        'answer_id':str(answer.answer_id) if answer else None,'risk':answer.risk_assessment.model_dump(mode='json') if answer and answer.risk_assessment else None,
        'assets':[x.model_dump(mode='json') for x in answer.affected_assets] if answer else [],
        'inventory_revision':source.analysis.inventory_revision if source.analysis else None,
        'evaluation_time':source.analysis.evaluation_time.isoformat() if source.analysis else None,
        'summary':answer.summary if answer else None,'recommendations':[x.model_dump(mode='json') for x in answer.recommended_actions] if answer else [],
        'evidence_ids':list(dict.fromkeys(e for f in (*source.analysis.risk_factors,*source.analysis.mitigating_factors)
            if f.influences_decision and not f.rejected_reason for e in f.evidence_ids)) if source.analysis else []})
