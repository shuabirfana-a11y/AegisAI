"""Read-only sealed-context analysis. Only the existing Runtime writes its audit."""
from app.agents.contracts import fingerprint
from app.agents.analysis.context_store import AnalysisContextStore
from app.agents.analysis.roles import TOOLS
from app.agents.analysis.rules import assess_risk
from app.agents.analysis.recommendations import build_actions
from app.agents.analysis.schemas import RiskAssessment
from app.runtime.contracts import json_bytes


def base_assessment(context):
    result=assess_risk(context)
    actions=build_actions(context,asset_match=result.asset_match_result,version_match=result.version_match_result,
        risk_level=result.risk_level,priority=result.priority)
    # Preserve the reference closure, including actions and inspectable conflicts.
    ids={e for a in actions for e in a.evidence_ids}
    ids.update(e for r in context.inputs.verification.claims for e in (*r.supporting_evidence_ids,*r.conflicting_evidence_ids))
    refs={ref['evidence_id']:ref for ref in result.evidence_refs}
    for e in (*context.inputs.verification.supporting_evidence,*context.inputs.verification.conflicting_evidence):
        if e.evidence_id in ids and e.evidence_id not in refs:
            refs[e.evidence_id]={'evidence_id':e.evidence_id,'claim_id':e.claim_id,'reference':e.reference,
                'raw_document_id':str(e.raw_document_id) if e.raw_document_id else None,'hash':e.hash,
                'source_key':e.source_key,'source_time':e.source_time.isoformat() if e.source_time else None,
                'verification_source_artifact_id':str(context.inputs.verification.artifact_id)}
    return RiskAssessment.model_validate({**result.model_dump(),'recommended_actions':actions,'evidence_refs':tuple(refs.values())})


def protected_decision(result):
    value=result.model_dump(mode='json')
    for key in ('reasoning_summary','warnings','model_assist_used','model_assist_status','model_calls'):
        value.pop(key)
    value['recommended_actions']=sorted(value['recommended_actions'],key=lambda a:a['action_id'])
    return fingerprint(value)


def execute_analysis(session,name,arguments,actor):
    context=AnalysisContextStore(session.bind).read(arguments['context_id'],actor=actor)
    if TOOLS[context.request.task_type]!=name:raise ValueError('Tool does not match sealed analysis request')
    assessment=base_assessment(context)
    immutable=protected_decision(assessment)
    if context.request.model_assistance:
        from app.llm.gateway import ModelGateway
        from app.llm.config import ModelConfig,ConfigError
        from app.agents.analysis.assistance import organize_explanation
        warnings=assessment.warnings
        try:
            config=ModelConfig.from_env()
            identity={'provider':config.provider,'model':config.model,'endpoint_hash':fingerprint(config.api_base or 'local'),
                'structured_mode':config.structured_mode,'token_parameter':config.token_parameter}
            if identity!=context.model_identity:raise ConfigError('Sealed model identity changed')
            config=ModelConfig.model_validate({**config.model_dump(),'api_base':config.api_base,'api_key':config.api_key,
                'timeout_seconds':min(config.timeout_seconds,5.0),'max_output_tokens':512})
            gateway=ModelGateway(config)
            try:organized=organize_explanation(context,assessment,gateway=gateway,remaining_seconds=5.0)
            finally:gateway.close()
            actions={a.action_id:a for a in assessment.recommended_actions}
            assessment=RiskAssessment.model_validate({**assessment.model_dump(),
                'recommended_actions':tuple(actions[key] for key in organized.action_ids),
                'reasoning_summary':organized.reasoning_summary,'model_assist_used':organized.used,
                'model_assist_status':organized.status,'model_calls':organized.model_calls,
                'warnings':warnings+organized.warnings})
        except (ConfigError,ValueError):
            assessment=RiskAssessment.model_validate({**assessment.model_dump(),'model_assist_status':'FAILED',
                'warnings':warnings+('MODEL_ASSIST_FAILED: model configuration unavailable or changed',)})
    if protected_decision(assessment)!=immutable:raise ValueError('Model changed protected analysis fields')
    return bounded_payload(context,assessment)


def bounded_payload(context,assessment):
    data={'context_id':str(context.context_id),'input_snapshot_hash':context.input_snapshot_hash,
        'evaluation_time':context.evaluation_time.isoformat(),
        'input_artifact_ids':[str(context.inputs.investigation.artifact_id),str(context.inputs.verification.artifact_id)],
        'assessment':assessment.model_dump(mode='json')}
    refs=list(assessment.evidence_refs)
    try:json_bytes({'data':data,'evidence_refs':refs},380*1024)
    except ValueError:
        assessment=RiskAssessment(verification_status=context.inputs.verification.verification_status,
            asset_id=context.inputs.asset.asset_id,component=context.inputs.asset.component,
            version=context.inputs.asset.deployed_version,partial_result=True,coverage_complete=False,
            warnings=('ANALYSIS_OUTPUT_LIMIT: unabridged input retained in sealed context',),
            unresolved_items=('Inspect owned context '+str(context.context_id)+' for complete inputs',))
        data['assessment']=assessment.model_dump(mode='json');refs=[]
    return {'status':'partial' if assessment.partial_result else 'success','data':data,
        'evidence_refs':refs,'warnings':list(assessment.warnings)}
