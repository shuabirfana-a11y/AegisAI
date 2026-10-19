"""Read only the selected, validated investigation and its source-bound receipts."""
import json
from pathlib import Path
from datetime import timedelta
from hashlib import sha256
from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import fingerprint
from app.agents.investigation.reader import InvestigationReader
from app.enrichment.contracts import ClaimType
from app.enrichment.evidence import pointer, origin
from app.enrichment.versions import canonical_value
from app.enrichment.acquisition import VENDORS, decode_readme
from urllib.parse import urlsplit
from app.runtime.contracts import TaskPlan
from app.utils.time import utcnow
from app.agents.verification.schemas import (
    VerificationRequest, VerificationClaim, VerificationEvidence, VerificationSourceSnapshot,
)


def authority_weight(level, source_type):
    score={'official':0.95,'authoritative':0.85,'community':0.45,'secondary':0.30}.get(level,0)
    return min(score,0.20) if 'blog' in source_type.casefold() else score


CATALOG_SCOPES={item['source_id']:item['authority_level'] for item in json.loads(
    (Path(__file__).resolve().parents[2]/'resources/sources.json').read_text(encoding='utf-8'))}
PACKAGE_CLAIMS={ClaimType.AFFECTS_PRODUCT,ClaimType.AFFECTS_VERSION,ClaimType.FIXED_VERSION}
STATIC_CLAIMS={ClaimType.POC_EXISTS,ClaimType.POC_ASSOCIATION,ClaimType.PATCH_EXISTS,ClaimType.FIX_COMMIT}
from app.enrichment.source_facts import FACT_TYPES


def scope_supported(scope, claim, *, source_key=None, reference=None):
    if not scope:return False
    text=scope.casefold()
    kind=claim.claim_type
    if source_key in CATALOG_SCOPES:
        if text!=CATALOG_SCOPES[source_key].casefold():return False
        if source_key=='CISA_KEV':
            return kind==ClaimType.KNOWN_EXPLOITED and claim.value.get('known_exploited') is True
        if source_key=='OSV':return kind in PACKAGE_CLAIMS|FACT_TYPES
        # CVE identity alone is not a verdict; CNA-scoped content still needs
        # the original kernel's explicit evidence and independent lineage rules.
        return kind in PACKAGE_CLAIMS|{ClaimType.CVSS_SCORE}
    if source_key in VENDORS:
        repo=VENDORS[source_key]
        if text!=repo.casefold():return False
        address=urlsplit((reference or {}).get('url') or '')
        if (address.scheme!='https' or address.hostname!='api.github.com' or address.username or
            address.password or not address.path.startswith('/repos/'+repo+'/security-advisories/')):return False
        if kind==ClaimType.VENDOR_CONFIRMED:
            return claim.value.get('repository')==repo and claim.scope_key=='vendor:'+repo
        return True  # Exact advisory/Claim association is checked separately.
    if source_key=='GITHUB':
        return text=='public hosting metadata; no exploit authority' and kind in STATIC_CLAIMS
    if source_key=='EPSS':return False  # No probability Claim exists in this protocol.
    return any(token in text for token in ('vulnerability','affected','product','漏洞',
        claim.vulnerability_id.casefold(),str(claim.value.get('package') or '\x00').casefold()))


def _quoted(raw, stored):
    try:
        text=raw.raw_payload.decode('utf-8')
        if stored.locator.get('json_pointer') is not None:
            payload=json.loads(text)
            if getattr(stored,'evidence_type',None)=='repository_readme' and stored.locator['json_pointer']=='/content':
                return stored.excerpt==decode_readme(payload)[:2400]
            fragment=pointer(payload,stored.locator['json_pointer'])
            return stored.excerpt==json.dumps(fragment,ensure_ascii=False)[:2400]
        if stored.locator.get('line') is not None:
            line=int(stored.locator['line'])
            lines=text.splitlines()
            return line>=1 and line<=len(lines) and stored.excerpt in lines[line-1]
        return False
    except (ValueError,KeyError,IndexError,TypeError,UnicodeError):return False


def _evidence(session, stored, claim, meta, now):
    raw=session.get(m.RawDocument,stored.raw_document_id)
    obs=session.get(m.SourceObservation,stored.observation_id)
    reasons=[]
    integrity='VALID'
    if not raw or not obs:
        integrity='MISSING';reasons.append('MISSING_RAW_PROVENANCE')
    elif (stored.source_id!=raw.source_id or obs.source_id!=stored.source_id or obs.raw_document_id!=raw.id
          or stored.scope_key!=claim.scope_key or str(stored.claim_id)!=claim.claim_id):
        integrity='INVALID';reasons.append('EVIDENCE_SCOPE_OR_SOURCE_MISMATCH')
    elif (sha256(raw.raw_payload).hexdigest()!=raw.content_hash or
          sha256(stored.excerpt.encode('utf-8')).hexdigest()!=stored.excerpt_hash or not _quoted(raw,stored)):
        integrity='INVALID';reasons.append('RAW_OR_EXCERPT_INTEGRITY_FAILED')
    level=meta.get('authority_level')
    level=level if level in ('official','authoritative','secondary','community') else None
    authority_scope=meta.get('authority_scope')
    if not scope_supported(authority_scope,claim,source_key=meta.get('source_key'),reference={'url':stored.source_url}):
        reasons.append('AUTHORITY_SCOPE_NOT_ESTABLISHED');level=None
    if meta.get('claim_revision') is not None and meta['claim_revision']!=claim.claim_revision:
        reasons.append('CLAIM_REVISION_MISMATCH');integrity='INVALID'
    if meta.get('source_id') and str(stored.source_id)!=str(meta['source_id']):
        reasons.append('RECEIPT_SOURCE_MISMATCH');integrity='INVALID'
    latest=None
    if obs:
        latest=session.scalar(select(m.SourceObservation.id).where(m.SourceObservation.source_id==obs.source_id,
            m.SourceObservation.external_id==obs.external_id,m.SourceObservation.parse_status=='parsed',
            m.SourceObservation.created_at<=now).order_by(m.SourceObservation.retrieved_at.desc(),
                m.SourceObservation.created_at.desc(),m.SourceObservation.id.desc()).limit(1))
    current=bool(obs and obs.parse_status=='parsed' and latest==obs.id and meta.get('is_current') is True)
    if not current:reasons.append('HISTORICAL_OR_UNRESOLVED_OBSERVATION')
    if stored.retrieved_at<now-timedelta(days=30):reasons.append('STALE_EVIDENCE')
    if stored.retrieved_at>now+timedelta(minutes=5):reasons.append('FUTURE_RETRIEVAL')
    if stored.published_at and (stored.published_at>now+timedelta(minutes=5) or
                               stored.published_at>stored.retrieved_at+timedelta(minutes=5)):
        reasons.append('INCONSISTENT_SOURCE_TIME')
    direct=bool(stored.details.get('explicit') and integrity=='VALID')
    source_type=stored.evidence_type
    details=dict(stored.details)
    # Reserved derived metadata is always rebuilt from this raw witness.
    details.pop('normalized_version_scope',None)
    if integrity=='VALID' and claim.claim_type in ('AFFECTS_VERSION','FIXED_VERSION'):
        from app.enrichment.version_scope import stored_scope
        version_scope=stored_scope(session,stored,claim.claim_type)
        if version_scope:details['normalized_version_scope']=version_scope.model_dump(mode='json')
    return VerificationEvidence(evidence_id=str(stored.id),claim_id=claim.claim_id,
        source_id=stored.source_id,source_key=meta.get('source_key') or 'unknown',source_type=source_type,
        source_name=stored.publisher[:300],source_time=stored.published_at or stored.retrieved_at,
        content=stored.excerpt,reference={'url':stored.source_url,'locator':stored.locator},
        hash=raw.content_hash if raw else None,excerpt_hash=stored.excerpt_hash,
        authority_score=authority_weight(level,source_type),directness_score=1.0 if direct else 0.25,
        authority_level=level,authority_scope=authority_scope,lineage_key=origin(obs) if obs else None,
        observation_id=stored.observation_id,raw_document_id=stored.raw_document_id,
        published_at=stored.published_at,retrieved_at=stored.retrieved_at,observed_value=stored.observed_value or {},
        scope_key=stored.scope_key,vulnerability_id=claim.vulnerability_id,stance=stored.stance,
        directness='direct' if direct else 'mention',evidence_type=stored.evidence_type,is_current=current,
        integrity_status=integrity,exclusion_reasons=tuple(reasons),details=details)


def _claim(value, source_task_id, vulnerability_id):
    kind=value.get('claim_type')
    if kind not in set(ClaimType) or str(value.get('vulnerability_id'))!=vulnerability_id:return None
    return VerificationClaim(claim_id=str(value['id']),statement=kind+' '+json.dumps(value['value_json'],ensure_ascii=False)[:2100],
        claim_type=kind,source_task_id=source_task_id,related_entities={'vulnerability_id':vulnerability_id,
            'package_identifier_id':value.get('package_identifier_id'),'cvss_version':value.get('cvss_version'),
            'assessment_kind':value.get('assessment_kind'),
            'superseded':(value.get('metadata') or value.get('details') or {}).get('superseded') is True},
        value=value['value_json'],
        scope_key=value['scope_key'],vulnerability_id=vulnerability_id,
        package_identifier_id=str(value['package_identifier_id']) if value.get('package_identifier_id') else None,
        branch=value.get('branch'),claim_revision=value.get('revision'),origin='stored',source_field='intelligence.claims')


class InvestigationSnapshotReader:
    def __init__(self,engine):self.engine=engine

    def read(self,request,*,actor,evaluation_time=None):
        request=VerificationRequest.model_validate_json(request.model_dump_json())
        now=evaluation_time or utcnow()
        found=InvestigationReader(self.engine).read(request.source_run_id,actor)
        artifact=next((a for a in found.artifacts if a.task_id==request.source_task_id
                       and a.artifact_id==request.source_artifact_id),None)
        if artifact is None:raise LookupError('Source artifact not available')
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==request.source_run_id,
                m.AgentRun.actor_principal==actor,m.AgentRun.agent_type=='runtime-v1'))
            ns=row.details['runtime_v1'];plan=TaskPlan.model_validate(ns['plan'])
            selected=set()
            def include(task_id):
                if task_id in selected:return
                selected.add(task_id)
                for parent in next(t for t in plan.tasks if t.task_id==task_id).dependencies:include(parent)
            include(request.source_task_id)
            artifacts={a.task_id:a for a in found.artifacts}
            for ref in request.supporting_artifacts:
                extra=artifacts.get(ref.task_id)
                if (extra is None or extra.artifact_id!=ref.artifact_id or extra.run_id!=ref.run_id or
                    extra.runtime_status!='SUCCESS' or extra.partial_result or extra.canonical_id not in (None,artifact.canonical_id)):
                    raise ValueError('SUPPORTING_ARTIFACT_INVALID')
                include(ref.task_id)
            refs=[];metadata={};claims={};candidate_rows=[];records=[]
            root=str(artifact.vulnerability_id) if artifact.vulnerability_id else ''
            source_tasks=[(task,ns,row.id,False) for task in plan.tasks if task.task_id in selected]
            extra_ids=()
            if request.supplement_id:
                from app.orchestration.supplement.runtime import read_extra_sources
                extra_id,extra_plan,extra_ns=read_extra_sources(self.engine,request,actor)
                extra_ids=(extra_id,)
                source_tasks.extend((task,extra_ns,extra_id,True) for task in extra_plan.tasks)
            for task,source_ns,source_id,supplementary in source_tasks:
                for call in source_ns['artifacts'].get(task.task_id,{}).get('tool_calls',[]):
                    record=db.get(m.ToolCallRecord,UUID(call['record_id']))
                    if record is None or record.agent_run_id!=source_id:raise ValueError('Invalid source receipt')
                    envelope=record.output_summary
                    if not supplementary:records.append((record,task.task_id))
                    refs.append({**call,'input_hash':fingerprint(record.input_summary),
                                 'output_hash':fingerprint(envelope),**({'source_run_id':str(source_id)} if supplementary else {})})
                    for item in envelope.get('evidence_refs',[]):
                        if item.get('evidence_id'):
                            key=str(item['evidence_id']);previous=metadata.get(key,{})
                            metadata[key]={**previous,**item} if previous.get('source_id')==item.get('source_id') else dict(item)
                    data=envelope.get('data') or {}
                    if not isinstance(data,dict):continue
                    # The original size fallback retains identity only in formal receipts.
                    if not root and record.tool_name in ('get_vulnerability','relation_query') and data.get('canonical_id') and data.get('id'):
                        root=str(data['id'])
                    intel=data.get('intelligence') or {}
                    # Old reference decorators do not include source_key. The original
                    # receipt's serialized Evidence rows do; never fill it from live Source.
                    evidence_rows=intel.get('evidence',[]) + (data.get('items',[]) if record.tool_name=='get_evidence' else [])
                    for item in evidence_rows:
                        saved_meta=metadata.get(str(item.get('id')))
                        if saved_meta and str(item.get('source_id'))==str(saved_meta.get('source_id')) and item.get('source_key'):
                            saved_meta.setdefault('source_key',item['source_key'])
                    rows=intel.get('claims',[]) + (data.get('items',[]) if record.tool_name=='get_claims' else [])
                    for item in rows:
                        got=_claim(item,task.task_id,root)
                        # Auxiliary source facts are an explicit factual query scope,
                        # not new required decisions for existing asset tasks.
                        if got and got.claim_type in FACT_TYPES and not request.include_source_facts:continue
                        if got:claims[got.claim_id]=got
                    if isinstance(data.get('affected_versions'),list):candidate_rows+=data['affected_versions']
            # Parsed source ranges become candidates when no equivalent stored claim exists.
            for item in candidate_rows:
                package=str(item.get('package_identifier_id') or '')
                match=next((c for c in claims.values() if c.package_identifier_id==package),None)
                value={'raw_expression':item.get('raw_expression'),
                       'ecosystem':match.value.get('ecosystem') if match else None,
                       'package':match.value.get('package') if match else None}
                from app.agents.verification.asset_snapshot import candidate_version_value
                value=candidate_version_value(item,match)
                if not root or not value['raw_expression'] or any(c.claim_type==ClaimType.AFFECTS_VERSION and
                    c.package_identifier_id==package and canonical_value('AFFECTS_VERSION',c.value)==canonical_value('AFFECTS_VERSION',value)
                    for c in claims.values()):continue
                identifier='derived:'+fingerprint([str(artifact.artifact_id),'affected_versions',item])
                claims[identifier]=VerificationClaim(claim_id=identifier,statement='Affected range '+value['raw_expression'],
                    claim_type='AFFECTS_VERSION',source_task_id=request.source_task_id,related_entities={'package_identifier_id':package},
                    value=value,scope_key=match.scope_key if match else 'unresolved:'+package,vulnerability_id=root,
                    package_identifier_id=package or None,source_field='affected_versions',origin='derived')
            all_ids=sorted(claims);kept=all_ids[:32];evidence=[];omitted=0
            for identifier in kept:
                claim=claims[identifier];bound=[]
                for eid,meta in sorted(metadata.items()):
                    if str(meta.get('claim_id'))!=identifier:continue
                    stored=db.get(m.Evidence,UUID(eid))
                    if stored is None:continue
                    if len(bound)>=16 or len(evidence)>=128:omitted+=1;continue
                    evidence.append(_evidence(db,stored,claim,meta,now));bound.append(eid)
                claims[identifier]=claim.model_copy(update={'evidence_ids':tuple(bound)})
            from app.agents.verification.impact_normalization import normalize_bundle
            normalized,bound_evidence=normalize_bundle(tuple(claims[i] for i in kept),tuple(evidence),
                source_artifact_id=artifact.artifact_id,asset_id=request.asset_id,
                coalesce=not request.claim_ids and request.task_type=='evidence_verification')
            claims={c.claim_id:c for c in normalized};kept=list(claims);evidence=list(bound_evidence)
            unresolved=list(artifact.uncertainties)
            if any(c.origin=='derived' and not c.evidence_ids for c in (claims[i] for i in kept)):
                unresolved.append('Derived ranges without immutable claim-bound evidence remain candidates')
            if len(all_ids)>32 or omitted:unresolved.append('VERIFICATION_INPUT_LIMIT: unprocessed claims/evidence retained as counts')
            from app.agents.verification.conflict_evidence import conflict_artifacts
            extension={'conflict_evidence_artifacts':conflict_artifacts(artifact.model_dump(mode='json'),evidence)}
            if request.asset_id:
                from app.agents.verification.asset_snapshot import capture_version_observation,impact_references
                extension['version_observations']=capture_version_observation(request,records,artifacts,tuple(claims[i] for i in kept),actor)
                extension['impact_version_evidence']=impact_references(tuple(claims[i] for i in kept),evidence)
                if not extension['version_observations']:unresolved.append('ASSET_VERSION_OBSERVATION_MISSING_OR_AMBIGUOUS')
            return VerificationSourceSnapshot(source_run_id=row.id,source_task_id=artifact.task_id,
                supplementary_run_ids=extra_ids,
                source_artifact_id=artifact.artifact_id,source_snapshot_as_of=now,artifact=artifact.model_dump(mode='json'),
                receipt_references=tuple(refs),claims=tuple(claims[i] for i in kept),evidence=tuple(evidence),
                omitted_claim_ids=tuple(all_ids[32:288]),omitted_claim_count=max(0,len(all_ids)-32),
                omitted_evidence_count=omitted,unresolved_items=tuple(unresolved),
                warnings=('TIME_CHAIN_PARTIAL: release/fix dates are only checked when supplied',),
                parent_planner_run_id=plan.route.get('planner_run_id'),**extension)
