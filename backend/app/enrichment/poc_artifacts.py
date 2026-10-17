"""Project existing candidates, Evidence and Verification. No network or verdict writes."""
import hashlib
import json
from datetime import timedelta
from sqlalchemy import select
from pydantic import TypeAdapter, ValidationError
from app.db import models as m
from app.enrichment.contracts import API_VERIFY
from app.enrichment.evidence import current_evidence, pointer
from app.enrichment.acquisition import decode_readme
from app.enrichment.versions import canonical_value
from app.enrichment.queries import target_id
from app.monitoring.views import has_verified_exploit
from app.assets.remediation import trusted_claim
from app.utils.time import utcnow
from app.enrichment.poc_schemas import POCArtifact, POCEvidence, POCPage, POCVerification, PublicReference

URL=TypeAdapter(PublicReference)


def intact_evidence(session, evidence, claim):
    raw=session.get(m.RawDocument,evidence.raw_document_id)
    obs=session.get(m.SourceObservation,evidence.observation_id)
    if (raw is None or obs is None or raw.source_id!=evidence.source_id
        or obs.source_id!=evidence.source_id or obs.raw_document_id!=raw.id
        or evidence.source_url!=raw.source_url
        or evidence.scope_key!=claim.scope_key
        or hashlib.sha256(raw.raw_payload).hexdigest()!=raw.content_hash
        or hashlib.sha256(evidence.excerpt.encode()).hexdigest()!=evidence.excerpt_hash):
        return False
    try:
        locator=evidence.locator;text=raw.raw_payload.decode('utf-8')
        if not isinstance(locator,dict):return False
        if 'json_pointer' in locator:
            payload=json.loads(text)
            if not isinstance(locator['json_pointer'],str):return False
            if evidence.evidence_type=='repository_readme' and not isinstance(payload,dict):return False
            excerpt=decode_readme(payload) if evidence.evidence_type=='repository_readme' and locator['json_pointer']=='/content' else json.dumps(pointer(payload,locator['json_pointer']),ensure_ascii=False)
        elif 'text_span' in locator:
            start,end=locator['text_span']
            if not isinstance(start,int) or not isinstance(end,int) or not 0<=start<end<=len(text):return False
            excerpt=text[start:end]
        elif 'line' in locator:
            line=locator['line']
            if not isinstance(line,int) or not 1<=line<=len(text.splitlines()):return False
            return evidence.excerpt in text.splitlines()[line-1]
        else:return False
        return evidence.excerpt==excerpt[:2400]
    except (ValueError,KeyError,IndexError,TypeError,UnicodeError,AttributeError):
        return False


def qualifying_exploit_evidence(evidence,claim,*,current,now):
    return (current and isinstance(evidence.details,dict) and evidence.details.get('validated_exploit') is True
        and evidence.stance=='support' and now-timedelta(days=30)<=evidence.retrieved_at<=now+timedelta(minutes=5)
        and (evidence.published_at is None or evidence.published_at<=min(now,evidence.retrieved_at)+timedelta(minutes=5))
        and canonical_value(claim.claim_type,evidence.observed_value or {})==canonical_value(claim.claim_type,claim.value_json))


def poc_artifact(session,poc):
    now=utcnow()
    source=session.get(m.Source,poc.source_id)
    if source is None:raise ValueError('POC_SOURCE_MISSING')
    origin=session.get(m.SourceObservation,poc.observation_id)
    raw=session.get(m.RawDocument,origin.raw_document_id) if origin else None
    if origin is None or origin.source_id!=poc.source_id or raw is None or raw.source_id!=poc.source_id:
        raise ValueError('POC_SOURCE_OBSERVATION_MISMATCH')
    if not isinstance(poc.details,dict):raise ValueError('POC_METADATA_INVALID')
    URL.validate_python(poc.url)
    claims=list(session.scalars(select(m.Claim).where(m.Claim.poc_candidate_id==poc.id,
        m.Claim.vulnerability_id==poc.vulnerability_id,m.Claim.asset_component_id.is_(None))))
    evidence=[];verifications=[];excluded=0;proof_links={}
    for claim in claims:
        if not isinstance(claim.details,dict):raise ValueError('POC_CLAIM_METADATA_INVALID')
        stored=list(session.scalars(select(m.Evidence).where(m.Evidence.claim_id==claim.id).order_by(m.Evidence.id)))
        if any(not isinstance(e.details,dict) for e in stored):raise ValueError('POC_EVIDENCE_METADATA_INVALID')
        current={x['id']:x['is_current'] for x in current_evidence(session,claim)}
        valid={}
        for e in stored:
            if not intact_evidence(session,e,claim):excluded+=1;continue
            ev_source=session.get(m.Source,e.source_id)
            if ev_source is None:continue
            try:
                item=POCEvidence(id=e.id,claim_id=claim.id,source=ev_source.source_key,reference=e.source_url,
                    content=e.excerpt,raw_document_id=e.raw_document_id,observation_id=e.observation_id,
                    hash=session.get(m.RawDocument,e.raw_document_id).content_hash,retrieved_time=e.retrieved_at,
                    is_current=current[str(e.id)],stance=e.stance,
                    supports_exploit_validation=qualifying_exploit_evidence(e,claim,current=current[str(e.id)],now=now))
            except ValidationError:excluded+=1;continue
            evidence.append(item);valid[e.id]=e
        for v in session.scalars(select(m.VerificationResult).where(m.VerificationResult.claim_id==claim.id).order_by(m.VerificationResult.claim_revision)):
            links=tuple(session.scalars(select(m.VerificationEvidence.evidence_id)
                .where(m.VerificationEvidence.verification_result_id==v.id,m.VerificationEvidence.claim_id==claim.id)))
            ids=tuple(x for x in links if x in valid)
            qualifying={x for x in ids if qualifying_exploit_evidence(valid[x],claim,current=current[str(x)],now=now)
                and valid[x].retrieved_at<=v.verified_at+timedelta(minutes=5)}
            # Only actual linked, intact and current validation Evidence can establish usability.
            exploit=(trusted_claim(session,claim) and v.status=='confirmed' and v.verified_by_type=='human' and v.claim_revision==claim.revision
                and poc.first_seen_at<=v.verified_at<=now+timedelta(minutes=5)
                and bool(qualifying))
            proof_links[v.id]=qualifying if exploit else set()
            verifications.append(POCVerification(id=v.id,claim_id=claim.id,claim_type=claim.claim_type,
                status=API_VERIFY[v.status],current_revision=v.claim_revision==claim.revision,
                verified_time=v.verified_at,method=v.verification_method,verified_by_type=v.verified_by_type,
                evidence_ref=ids,exploit_validation=exploit))
    if not evidence:raise ValueError('POC_EVIDENCE_MISSING_OR_INVALID')
    # Bound transport history without throwing away an otherwise valid candidate.
    proof_ids={eid for ids in proof_links.values() for eid in ids}
    evidence.sort(key=lambda e:(e.id in proof_ids,e.is_current,e.retrieved_time,str(e.id)),reverse=True)
    omitted_evidence=max(0,len(evidence)-128);evidence=evidence[:128]
    selected={e.id for e in evidence}
    verifications=[v.model_copy(update={'evidence_ref':tuple(eid for eid in v.evidence_ref if eid in selected),
        'exploit_validation':v.exploit_validation and bool(proof_links[v.id]&selected)}) for v in verifications]
    verifications.sort(key=lambda v:(v.exploit_validation,v.current_revision,v.verified_time,str(v.id)),reverse=True)
    omitted_verification=max(0,len(verifications)-128);verifications=verifications[:128]
    verified=has_verified_exploit(session,poc) and any(v.exploit_validation for v in verifications)
    details=poc.details or {}
    return POCArtifact(id=poc.id,vulnerability_id=poc.vulnerability_id,source=source.source_key,reference=poc.url,
        title=(poc.repository or details.get('title') or poc.candidate_type)[:300],
        description=details.get('description'),language=details.get('language'),
        status='VERIFIED_EXPLOIT' if verified else 'POC_CANDIDATE',created_time=poc.first_seen_at,
        verified_time=max(v.verified_time for v in verifications if v.exploit_validation) if verified else None,
        evidence_ref=tuple(e.id for e in evidence),evidence=tuple(evidence),verification=tuple(verifications),
        association_status=poc.status,usability_status=poc.usability_status,
        omitted_evidence_count=omitted_evidence,omitted_verification_count=omitted_verification,
        excluded_evidence_count=excluded)


def poc_page(session,identifier,*,offset=0,limit=20,job_status=None):
    target=target_id(session,identifier)
    if target is None:raise LookupError('Vulnerability not found')
    vuln=session.get(m.Vulnerability,target)
    records=list(session.scalars(select(m.PocCandidate).where(m.PocCandidate.vulnerability_id==target,
        m.PocCandidate.status!='rejected').order_by(m.PocCandidate.first_seen_at.desc(),m.PocCandidate.id)))
    items=[];warnings=[]
    for row in records:
        try:items.append(poc_artifact(session,row))
        except (ValueError,TypeError,KeyError,AttributeError):
            warnings.append('POC_RECORD_OMITTED: '+str(row.id)+'; invalid or missing public provenance.')
    job=session.scalar(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==target,
        m.EnrichmentJob.enrichment_type=='poc').order_by(m.EnrichmentJob.created_at.desc(),m.EnrichmentJob.id.desc()).limit(1))
    job_status=job_status if job_status is not None else job.status if job else None
    search='NOT_RUN' if job_status is None else 'FAILED' if job_status=='failed' else 'PARTIAL' if job_status in ('partial','running','queued') else 'COMPLETED'
    if search!='COMPLETED':warnings.append('POC_SEARCH_'+search+': discovery does not establish global absence.')
    status='VERIFIED_EXPLOIT' if any(x.status=='VERIFIED_EXPLOIT' for x in items) else 'POC_CANDIDATE' if items else 'NO_EVIDENCE'
    return POCPage(vulnerability_id=target,canonical_id=vuln.canonical_id,status=status,search_status=search,
        items=tuple(items[offset:offset+limit]),total=len(items),stored_count=len(records),omitted_count=len(records)-len(items),
        offset=offset,limit=limit,as_of=utcnow(),warnings=tuple(warnings))
