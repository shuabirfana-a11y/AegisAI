"""Fixed READ_ONLY adapters. Only runtime audit outputs are written by the caller."""
from app.agents.contracts import fingerprint
from app.agents.verification.context_store import VerificationContextStore
from app.agents.verification.roles import TOOLS
from app.agents.verification.rules import evaluate_snapshot
from app.agents.verification.schemas import VerificationAssessment
from app.runtime.contracts import json_bytes


def execute_verification(session,name,arguments,actor):
    context=VerificationContextStore(session.bind).read(arguments['context_id'],actor=actor)
    if TOOLS[context.request.task_type]!=name or tuple(arguments.get('claim_ids',()))!=context.request.claim_ids:
        raise ValueError('Tool does not match the sealed verification request')
    assessment=evaluate_snapshot(context)
    if context.request.model_assistance:
        from app.llm.gateway import ModelGateway
        from app.llm.config import ModelConfig,ConfigError
        from app.agents.verification.assistance import assist_claims
        warnings=list(assessment.warnings)
        try:
            config=ModelConfig.from_env()
            identity={'provider':config.provider,'model':config.model,'endpoint_hash':fingerprint(config.api_base or 'local'),
                      'structured_mode':config.structured_mode,'token_parameter':config.token_parameter}
            if identity!=context.model_identity:raise ConfigError('Sealed model identity changed')
            config=ModelConfig.model_validate({**config.model_dump(), 'api_base':config.api_base,'api_key':config.api_key,
                'timeout_seconds':min(config.timeout_seconds,5.0),'max_output_tokens':512})
            gateway=ModelGateway(config)
            try:assisted=assist_claims(context,gateway=gateway,remaining_seconds=5.0)
            finally:gateway.close()
            assessment=VerificationAssessment.model_validate({**assessment.model_dump(),
                'model_calls':assisted.model_calls,'model_hints':tuple(h.model_dump(mode='json') for h in assisted.hints),
                'warnings':tuple(warnings)+assisted.warnings})
        except (ConfigError,ValueError):
            assessment=assessment.model_copy(update={'warnings':tuple(warnings)+('MODEL_ASSIST_FAILED: model configuration unavailable or changed',)})
    refs=[]
    for evidence in (*assessment.supporting_evidence,*assessment.conflicting_evidence):
        value={'evidence_id':evidence.evidence_id,'claim_id':evidence.claim_id,'source_id':str(evidence.source_id) if evidence.source_id else None,
            'raw_document_id':str(evidence.raw_document_id) if evidence.raw_document_id else None,
            'observation_id':str(evidence.observation_id) if evidence.observation_id else None,
            'url':evidence.reference.get('url'),'locator':evidence.reference.get('locator'),
            'authority_level':evidence.authority_level,'authority_scope':evidence.authority_scope,
            'retrieved_at':evidence.retrieved_at.isoformat() if evidence.retrieved_at else None,
            'lineage_key':evidence.lineage_key,'verified':False,'content_trust_level':'UNTRUSTED_EXTERNAL_CONTENT'}
        if value not in refs:refs.append(value)
    data={'context_id':str(context.context_id),'source_run_id':str(context.snapshot.source_run_id),
        'source_artifact_id':str(context.snapshot.source_artifact_id),'source_snapshot_hash':context.source_snapshot_hash,
        'evaluation_time':context.evaluation_time.isoformat(),'assessment':assessment.model_dump(mode='json')}
    try:
        # Leave space for original Artifact identity, duplicated evidence and canonical refs.
        json_bytes({'data':data,'evidence_refs':refs},380*1024)
    except ValueError:
        assessment=VerificationAssessment(verification_status='CONFLICT' if assessment.verification_status=='CONFLICT' else 'INSUFFICIENT_EVIDENCE',
            confidence=0,partial_result=True,model_calls=assessment.model_calls,
            warnings=('VERIFICATION_OUTPUT_LIMIT: complete source data retained in sealed context',),
            unresolved_items=('Read owner-bound context '+str(context.context_id)+' for unabridged input; output could not fit Runtime budget',))
        data['assessment']=assessment.model_dump(mode='json');refs=[]
        data['claims_checked']=[c.claim_id for c in context.snapshot.claims if not context.request.claim_ids or c.claim_id in context.request.claim_ids]
    # Do not redecorate these refs from live Source state in the legacy adapter.
    return {'status':'partial' if assessment.partial_result else 'success','data':data,
            'evidence_refs':refs,'warnings':list(assessment.warnings)}


def evaluate_evidence_snapshot(session,arguments,actor):
    return execute_verification(session,'evaluate_evidence_snapshot',arguments,actor)


def validate_claim_snapshot(session,arguments,actor):
    return execute_verification(session,'validate_claim_snapshot',arguments,actor)


def compare_claim_snapshot(session,arguments,actor):
    return execute_verification(session,'compare_claim_snapshot',arguments,actor)
