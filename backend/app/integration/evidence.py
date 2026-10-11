"""Coverage checks consume prior verified verdicts, without voting by URL count."""
from app.integration.rules_common import check,finish,assessments,evidence_map,facts,grounded

def check_evidence(c):
    issues=[];v=c.verification;r=c.analysis
    if not v:return (check('evidence','VERIFIED_EVIDENCE_MISSING','Verification evidence not available','REPLAN'),)
    for a in v.claims:
        if a.status=='CONFIRMED' and not grounded(c,a.claim.claim_id):
            issues.append(check('evidence','CONFIRMED_CLAIM_WITHOUT_SUPPORT','Confirmed statement has no eligible original support','REPLAN',refs=(a.claim.claim_id,)))
    refs=evidence_map(c)
    if r:
        for f in facts(c):
            factual=(getattr(f,'provenance',None)=='verified_claim' and getattr(f,'influences_decision',False)) or getattr(f,'action_provenance',None)=='VERIFIED_CLAIM'
            if factual and (not f.claim_ids or not all(grounded(c,id) for id in f.claim_ids)):
                issues.append(check('evidence','UNVERIFIED_DOWNSTREAM_FACT','Decision/action needs confirmed supported claims','REPLAN',refs=(getattr(f,'factor_id',getattr(f,'action_id','fact')),)))
    groups={}
    for e in v.supporting_evidence:
        lineage=e.lineage_key or str(e.observation_id or e.raw_document_id or e.source_id or e.evidence_id)
        groups.setdefault(lineage,set()).add(str(e.raw_document_id))
    if any(len(raw)>1 for raw in groups.values()):issues.append(check('evidence','SHARED_SOURCE_LINEAGE','Reposts share one origin; they are not independent confirmations',warning=True))
    return finish('evidence',issues)
