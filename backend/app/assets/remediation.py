from sqlalchemy import select
from app.db import models as m
from app.enrichment.evidence import current_evidence
from app.utils.time import utcnow
from datetime import timedelta
from uuid import UUID
from app.enrichment.evidence import evidence_fingerprint
from app.enrichment.versions import canonical_value

def trusted_claim(session,c,*,now=None):
    if c.verification_status!='confirmed' or not c.adopted or c.details.get('superseded'):return False
    evidence=[e for e in current_evidence(session,c) if e['is_current']];now=now or utcnow()
    if any(e['stance']=='contradict' for e in evidence):return False
    if session.scalar(select(m.ConflictRecord.id).where(m.ConflictRecord.status=='open',(m.ConflictRecord.claim_a_id==c.id)|(m.ConflictRecord.claim_b_id==c.id)).limit(1)):return False
    support=[e for e in evidence if e['stance']=='support' and now-timedelta(days=30)<=e['retrieved_at']<=now+timedelta(minutes=5) and canonical_value(c.claim_type,e['value'] or {})==canonical_value(c.claim_type,c.value_json)]
    if not support:return False
    result=session.scalar(select(m.VerificationResult).where(m.VerificationResult.claim_id==c.id,m.VerificationResult.claim_revision==c.revision).limit(1))
    if result is None:return False
    if result is not None:
        if result.status!='confirmed':return False
        known_ids={UUID(x) for x in result.details.get('observed_evidence_ids',[])}
        known_ids.update(session.scalars(select(m.VerificationEvidence.evidence_id).where(m.VerificationEvidence.verification_result_id==result.id)))
        if known_ids:
            known={evidence_fingerprint(e) for e in session.scalars(select(m.Evidence).where(m.Evidence.id.in_(known_ids)))}
            if any(e['fingerprint'] not in known for e in evidence):return False
        elif result.verified_by_type=='human':return False
    return True

def evidence_ids(session,c):return [e['id'] for e in current_evidence(session,c) if e['is_current'] and e['stance']=='support']

def get_remediation(session,vulnerability_id,package_id):
    pkg=session.get(m.PackageIdentifier,package_id);claims=list(session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==vulnerability_id)))
    if pkg is None or session.get(m.Vulnerability,vulnerability_id) is None:raise LookupError('Vulnerability or package not found')
    fixed=[];patches=[];guidance=[];related=[]
    for c in claims:
        if not trusted_claim(session,c):continue
        if c.claim_type=='FIXED_VERSION' and c.package_identifier_id==pkg.id and c.value_json.get('version'):
            fixed.append({'version':c.value_json['version'],'claim_id':str(c.id),'claim_revision':c.revision,'evidence_ids':evidence_ids(session,c),'scope_key':c.scope_key})
        if c.claim_type in ('PATCH_EXISTS','FIX_COMMIT') and c.patch_candidate_id:
            p=session.get(m.PatchCandidate,c.patch_candidate_id)
            if p.product_id==pkg.product_id and p.status=='confirmed':
                item={'patch_id':str(p.id),'url':p.url,'type':p.patch_type,'claim_id':str(c.id),'evidence_ids':evidence_ids(session,c),'branch':p.branch,'applicability':'UNKNOWN'}
                applies=p.details.get('package_identifier_id')==str(pkg.id) and not p.branch and not p.details.get('branch')
                if applies:patches.append({**item,'applicability':'PACKAGE_CONFIRMED'})
                else:related.append(item)
        if c.claim_type=='VENDOR_CONFIRMED':
            scoped=c.package_identifier_id==pkg.id or c.value_json.get('ecosystem')==pkg.ecosystem and c.value_json.get('package')==pkg.package_name
            if scoped:guidance.append({'claim_id':str(c.id),'evidence_ids':evidence_ids(session,c),'reason':'Official advisory is available for this package; inspect exact branch scope'})
    statuses=[]
    if fixed:statuses.append('FIXED_VERSION_AVAILABLE')
    if patches:statuses.append('PATCH_AVAILABLE')
    if guidance:statuses.append('VENDOR_GUIDANCE_AVAILABLE')
    jobs=list(session.scalars(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==vulnerability_id,m.EnrichmentJob.enrichment_type.in_(['patch','vendor'])).order_by(m.EnrichmentJob.created_at.desc())))
    latest={}
    for j in jobs:latest.setdefault(j.enrichment_type,j)
    if not statuses:
        statuses=['NO_PUBLIC_FIX_FOUND'] if latest.get('patch') and latest['patch'].status=='no_result' else ['UNKNOWN']
    return {'statuses':statuses,'fixed_versions':fixed,'patches':patches,'related_patches':related,'vendor_guidance':guidance,
        'recommended_action':'Consider upgrade to a confirmed fixed release for this package/branch; validate compatibility' if fixed else 'Inspect the cited patch/vendor guidance' if patches or guidance else 'No confirmed remediation evidence available',
        'search_scope':[{'kind':j.enrichment_type,'status':j.status,'checked_at':j.finished_at.isoformat() if j.finished_at else None} for j in latest.values()],
        'absence_is_not_no_patch':True}
