"""Reference and verdict utilities, not a replacement verification/risk engine."""
from app.integration.contracts import GateCheck

def check(gate,code,message,blocking='NONE',*,warning=False,refs=(),objective=None):
    return GateCheck(gate=gate,code=code,message=message,blocking=blocking,
        outcome='ERROR' if blocking=='FATAL' else 'BLOCKED' if blocking!='NONE' else 'WARNING' if warning else 'PASS',
        refs=tuple(str(r) for r in refs),objective=objective)

def finish(gate,issues):
    return tuple(issues) or (check(gate,gate.upper()+'_OK','All applicable constraints satisfied'),)

def assessments(c):return {x.claim.claim_id:x for x in c.verification.claims} if c.verification else {}

def evidence_map(c):
    return {e.evidence_id:e for e in (*c.verification.supporting_evidence,*c.verification.conflicting_evidence)} if c.verification else {}

def grounded(c,claim_id):
    a=assessments(c).get(claim_id)
    if a is None or a.status!='CONFIRMED' or not a.supporting_evidence_ids:return False
    refs=evidence_map(c)
    return any((e:=refs.get(id)) is not None and e.claim_id==claim_id and e.scope_key==a.claim.scope_key and
        e.integrity_status=='VALID' and e.is_current and e.hash and e.raw_document_id and e.observation_id and
        e.authority_level in ('official','authoritative') and e.directness=='direct' and e.stance=='support' and
        not e.exclusion_reasons for id in a.supporting_evidence_ids)

def facts(c):
    r=c.analysis
    if not r:return ()
    return (*r.risk_factors,*r.mitigating_factors,r.exploitation_signal,r.patch_availability,*r.recommended_actions)

def decision(blocking,warning=False):
    if 'FATAL' in blocking:return 'FAILED'
    if 'HUMAN' in blocking:return 'HUMAN_REVIEW_REQUIRED'
    if 'REPLAN' in blocking:return 'REPLAN_REQUIRED'
    return 'PASS_WITH_WARNINGS' if warning else 'PASS'
