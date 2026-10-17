"""Pure deterministic projection. No tool, model, SQL or security verdict changes."""
import re
from uuid import uuid5,NAMESPACE_URL
from uuid import UUID
from urllib.parse import urlsplit
from app.integration.contracts import IntegrationContext,IntegrationResult
from app.integration.rules_common import grounded,evidence_map
from app.integration.redaction import public_reference
from app.orchestration.answer_contracts import (AnswerEnvelope,VerifiedFact,Citation,RiskView,ActionView,AssetView,
    DisputedClaim,EvidenceObservation)
from app.orchestration.handoff import artifact_ref

STATE={'PASS':('COMPLETE','调查结果已通过全局验收，结论及证据如下。'),
       'PASS_WITH_WARNINGS':('COMPLETE_WITH_WARNINGS','调查结果已通过验收，请同时查看非阻塞警告。'),
       'REPLAN_REQUIRED':('INCOMPLETE','调查尚不完整；以下仅为已核验事实及风险观察，需要补充调查。'),
       'HUMAN_REVIEW_REQUIRED':('REVIEW_REQUIRED','证据存在冲突，需要人工复核；系统保留冲突，不裁决争议事实。'),
       'FAILED':('FAILED','调查验收失败，未交付安全结论；请依据审计原因检查后重新提交新请求。')}
VALUE_KEYS=frozenset({'ecosystem','package','product','version','fixed','introduced','last_affected','raw_expression',
    'ranges','events','type','score','severity','url','commit','commit_url','patch_url','repository','condition',
    'known_exploited','cve','canonical_id','purl','operator','value'})


def safe_text(value):
    value=str(value)
    value=re.sub(r'https?://[^\s<>\"\']+',lambda m:str(public_reference(m.group(0))),value,flags=re.I)
    return re.sub(r'(?i)\b(api[_-]?key|access[_-]?token|token|password|secret|credential)\s*[:=]\s*[^\s,;]+',r'\1=[REDACTED]',value)


def safe_value(value):
    if isinstance(value,dict):return {k:safe_value(v) for k,v in value.items() if k in VALUE_KEYS}
    if isinstance(value,(list,tuple)):return [safe_value(v) for v in value]
    return safe_text(value) if isinstance(value,str) else value


def safe_impact_value(value):
    """Public range fields are data; credentials remain outside the allowlist."""
    result=safe_value(value)
    if not isinstance(value,dict):return result
    # Only validated source fact shapes; arbitrary input keys remain filtered.
    from app.enrichment.source_facts import fact_value
    kind='CWE' if 'cwe' in value else 'SOURCE_FACT' if value.get('field')=='summary' else None
    if kind:
        try:result.update({k:safe_text(v) for k,v in fact_value(kind,value).items()})
        except (ValueError,TypeError):pass
    for key in ('range','range_type','parse_status'):
        item=value.get(key)
        if isinstance(item,str) and len(item)<=2400:result[key]=safe_text(item)
    if isinstance(value.get('explicit_versions'),(list,tuple)):
        result['explicit_versions']=[safe_text(x) for x in value['explicit_versions'] if isinstance(x,str)]
    if isinstance(value.get('impact_scope'),dict):
        from app.enrichment.impact_scope import ImpactScope
        try:result['impact_scope']=ImpactScope.model_validate(value['impact_scope']).model_dump(mode='json',exclude_none=True)
        except (ValueError,TypeError):pass
    return result


def project_fact_value(claim,*,verification_state,confidence):
    # Existing immutable answers must retain their old deterministic projection.
    if claim.impact_scope is None:
        result=safe_impact_value(claim.value) if claim.claim_type in ('CWE','SOURCE_FACT') else safe_value(claim.value)
        # A CVSS vector is part of this typed metric, not a generic JSON field.
        # Preserve only its supplied scalar; never fetch or calculate one here.
        if claim.claim_type=='CVSS_SCORE' and 'vector' in claim.value:
            vector=claim.value['vector']
            if vector is None:result['vector']=None
            elif isinstance(vector,str) and len(vector)<=2400:result['vector']=safe_text(vector)
        return result
    result=safe_impact_value(claim.value)
    result['impact_scope']=claim.impact_scope.model_copy(update={'verification_state':getattr(verification_state,'value',verification_state),
        'confidence':confidence}).model_dump(mode='json',exclude_none=True)
    for ref in result['impact_scope']['evidence_refs']:ref['reference']=safe_reference(ref['reference'])
    for key in ('affected_product','affected_component','condition','platform','architecture','branch'):
        if isinstance(result['impact_scope'].get(key),str):result['impact_scope'][key]=safe_text(result['impact_scope'][key])
    return result


def public_locator(value):
    """Only bounded position selectors are exportable; no arbitrary excerpts."""
    if not isinstance(value,dict):return {}
    result={}
    for key,item in value.items():
        if key in ('line','line_start','line_end','column','column_start','column_end','page','index'):
            if type(item) is int and 0<=item<=10_000_000:result[key]=item
        elif key in ('json_pointer','json_path','field'):
            patterns={'json_pointer':r'(?:/[A-Za-z0-9_.~\-]+)*',
                'json_path':r'\$(?:\.[A-Za-z_][A-Za-z0-9_\-]*|\[(?:[0-9]+|\*)\])*',
                'field':r'[A-Za-z_][A-Za-z0-9_\-]*(?:\.[A-Za-z_][A-Za-z0-9_\-]*)*'}
            if isinstance(item,str) and len(item)<=500 and re.fullmatch(patterns[key],item):
                result[key]=safe_text(item)
    return result


def safe_reference(value):
    result={}
    for key,item in value.items():
        if key in ('url','source_url') and isinstance(item,str):
            try:
                parsed=urlsplit(item)
                if parsed.scheme.casefold() in ('http','https') and parsed.hostname and len(item)<=2000:
                    result[key]=safe_text(str(public_reference(item)))
            except ValueError:pass
        elif key=='locator':result[key]=public_locator(item)
        elif key in ('source_id','raw_document_id','observation_id'):
            try:result[key]=str(UUID(str(item)))
            except (ValueError,TypeError,AttributeError):pass
    return result


def eligible(e,claim):
    return (e.claim_id==claim.claim_id and e.scope_key==claim.scope_key and e.integrity_status=='VALID' and
        e.is_current and e.hash and e.raw_document_id and e.observation_id and e.source_id and
        e.authority_level in ('official','authoritative') and e.directness=='direct' and e.stance=='support' and not e.exclusion_reasons)


class AnswerComposer:
    def compose(self,context,source,gate,*,answer_id=None):
        source=IntegrationContext.model_validate_json(source.model_dump_json())
        gate=IntegrationResult.model_validate_json(gate.model_dump_json())
        facts=[];citations=[];disputed=[];observations=[];actions=[];assets=[];risk=None;warn=list(gate.warnings)
        accepted=gate.status in ('PASS','PASS_WITH_WARNINGS');scope='ACCEPTED' if accepted else 'OBSERVATION'
        if gate.status!='FAILED' and source.verification:
            refs=evidence_map(source);vref=artifact_ref(source.verification)
            statuses={a.claim.claim_id:a.status for a in source.verification.claims}
            for e in refs.values():
                observations.append(EvidenceObservation(evidence_id=e.evidence_id,claim_id=e.claim_id,
                    verification_status=statuses.get(e.claim_id,'PENDING'),scope_key=safe_text(e.scope_key),hash=e.hash,
                    source_id=e.source_id,raw_document_id=e.raw_document_id,observation_id=e.observation_id,
                    reference=safe_reference(e.reference),stance=e.stance,directness=e.directness,
                    integrity_status=e.integrity_status,is_current=e.is_current,verification_artifact=vref))
            for assessment in source.verification.claims:
                claim=assessment.claim
                if assessment.status!='CONFIRMED':
                    disputed.append(DisputedClaim(claim_id=claim.claim_id,claim_type=claim.claim_type,
                        verification_status=assessment.status,value=project_fact_value(claim,verification_state=assessment.status,
                            confidence=assessment.confidence),scope_key=safe_text(claim.scope_key),
                        supporting_evidence_ids=assessment.supporting_evidence_ids,conflicting_evidence_ids=assessment.conflicting_evidence_ids,
                        verification_artifact=vref))
                if not grounded(source,claim.claim_id):continue
                evidence=[refs[id] for id in assessment.supporting_evidence_ids if id in refs and eligible(refs[id],claim)]
                if not evidence:continue
                facts.append(VerifiedFact(claim_id=claim.claim_id,claim_type=claim.claim_type,
                    value=project_fact_value(claim,verification_state=assessment.status,confidence=assessment.confidence),
                    evidence_ids=tuple(e.evidence_id for e in evidence),source_artifact=vref))
                for e in evidence:
                    reference=safe_reference(e.reference)
                    citations.append(Citation(evidence_id=e.evidence_id,claim_id=claim.claim_id,hash=e.hash,
                        source_id=e.source_id,raw_document_id=e.raw_document_id,observation_id=e.observation_id,
                        reference=reference,verification_artifact=vref))
        if gate.status!='FAILED' and source.analysis:
            r=source.analysis;rref=artifact_ref(r)
            risk=RiskView(risk_level=r.risk_level,priority=r.priority,affected=r.affected,verification_status=r.verification_status,
                source_artifact=rref,asset_match_status=r.asset_match_status,version_match_status=r.version_match_status,
                exploitation_status=r.exploitation_signal.status,usability=r.exploitation_signal.usability,
                patch_status=r.patch_availability.status,patch_applied=r.patch_availability.applied,conclusion_scope=scope)
            if r.risk_level=='UNKNOWN':warn.append('UNKNOWN_IS_NOT_SAFE')
            if r.exploitation_signal.status in ('POC_CANDIDATE','VERIFIED_POC_ASSOCIATION'):warn.append('POC_USABILITY_NOT_EVALUATED')
            if r.patch_availability.status!='CONFIRMED_PRESENT':warn.append('PATCH_CANDIDATE_NOT_A_FIX')
            if source.asset_snapshot:
                a=source.asset_snapshot
                assets.append(AssetView(asset_id=a.asset_id,component_id=a.component_id,deployed_version=a.deployed_version,
                    source_artifact=rref,claim_ids=r.version_match_result.claim_ids))
            fact_ids={f.claim_id for f in facts};evidence_ids={c.evidence_id for c in citations}
            for a in r.recommended_actions:
                precise=bool(a.fixed_version or a.patch_reference)
                if precise and (a.action_provenance!='VERIFIED_CLAIM' or not a.claim_ids or not a.evidence_ids or
                    not set(a.claim_ids)<=fact_ids or not set(a.evidence_ids)<=evidence_ids):
                    warn.append('PRECISE_ACTION_NOT_DELIVERED');continue
                actions.append(ActionView(action_id=a.action_id,action_type=a.action_type,category=a.category,
                    summary='依据核验来源核对修复方案及适用条件。' if precise else '建议补充调查或采用通用防护措施；不表示已确认修复。',
                    fixed_version=safe_text(a.fixed_version) if a.fixed_version else None,
                    patch_reference=safe_text(a.patch_reference) if a.patch_reference else None,
                    claim_ids=a.claim_ids,evidence_ids=a.evidence_ids,action_provenance=a.action_provenance,
                    applicability=a.applicability,source_artifact=rref,conclusion_scope=scope))
        if source.investigation and source.investigation.poc_candidates:warn.append('POC_CANDIDATES_NOT_VERIFIED')
        status,summary=STATE[gate.status]
        return AnswerEnvelope(answer_id=answer_id or uuid5(NAMESPACE_URL,str(context.logical_investigation_id)+':answer-v1'),
            logical_investigation_id=context.logical_investigation_id,original_question=context.original_request.user_query,
            answer_status=status,integration_status=gate.status,summary=summary,key_findings=tuple(f.claim_id for f in facts),
            affected_assets=tuple(assets),risk_assessment=risk,recommended_actions=tuple(actions),verified_claims=tuple(facts),
            citations=tuple({c.evidence_id:c for c in citations}.values()),disputed_claims=tuple(disputed),
            evidence_observations=tuple(observations),evidence_references=tuple(e.evidence_id for e in observations),
            warnings=tuple(dict.fromkeys(warn)),unresolved_items=gate.unresolved_items,integration_result_id=gate.integration_id,
            agent_run_references=tuple(id for id in (context.investigation_run_id,context.verification_run_id,context.analysis_run_id) if id),
            accepted_source_run_references=gate.source_run_ids,trace_reference=context.logical_investigation_id,generated_at=gate.evaluation_time)

    def failure(self,context,*,code,cancelled=False):
        return AnswerEnvelope(answer_id=uuid5(NAMESPACE_URL,str(context.logical_investigation_id)+':answer-v1'),
            logical_investigation_id=context.logical_investigation_id,original_question=context.original_request.user_query,
            answer_status='CANCELLED' if cancelled else 'FAILED',summary='调查已取消。' if cancelled else '调查未完成，请查看审计状态。',
            warnings=(code,),unresolved_items=(code,),integration_result_id=context.integration_result_id,
            agent_run_references=tuple(id for id in (context.investigation_run_id,context.verification_run_id,context.analysis_run_id) if id),
            trace_reference=context.logical_investigation_id,generated_at=context.finished_at or context.updated_at)
