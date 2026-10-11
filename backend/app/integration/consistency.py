"""Explicit cross-agent fact invariants; no risk/version algorithm is repeated."""
from app.integration.rules_common import check,finish,assessments,facts,grounded

def check_consistency(c):
    issues=[];v=c.verification;r=c.analysis
    def fail(code,msg):issues.append(check('consistency',code,msg,'FATAL'))
    if v and (v.verification_status=='CONFLICT' or v.conflicts or any(a.status=='CONFLICT' for a in v.claims)):
        issues.append(check('consistency','CRITICAL_EVIDENCE_CONFLICT','Critical sources need human adjudication','HUMAN',refs=tuple(a.claim.claim_id for a in v.claims if a.status=='CONFLICT')))
    if v is None:return (check('consistency','VERIFICATION_INPUT_MISSING','Cannot validate cross-agent facts without verification input','REPLAN'),)
    if not r:return finish('consistency',issues)
    if v and r.verification_status!=v.verification_status:fail('VERIFICATION_STATE_MISMATCH','Analysis status differs from selected verification')
    if r.affected is not None and v and v.verification_status!='CONFIRMED':fail('UNVERIFIED_IMPACT','Unverified input cannot become certain impact')
    if r.version_match_status=='UNKNOWN' and r.affected is not None:fail('UNKNOWN_IMPACT_ESCALATED','Unknown version cannot become affected or safe')
    if r.affected is True and r.asset_match_status!='MATCHED':fail('ASSET_IMPACT_CONTRADICTION','Non-matched asset cannot be confirmed affected')
    if r.version_match_result.status!=r.version_match_status or r.asset_match_result.status!=r.asset_match_status:
        fail('MATCH_RESULT_INCONSISTENT','Summary and detailed match verdict disagree')
    if r.version_match_result.affected!=r.affected and r.affected is not None:fail('IMPACT_RESULT_INCONSISTENT','Summary and version impact verdict disagree')
    claims=assessments(c)
    for f in facts(c):
        factual=(getattr(f,'provenance',None)=='verified_claim' and getattr(f,'influences_decision',False)) or getattr(f,'action_provenance',None)=='VERIFIED_CLAIM'
        if factual and any(claims.get(id) and claims[id].status!='CONFIRMED' for id in getattr(f,'claim_ids',())):
            fail('REJECTED_OR_UNRESOLVED_FACT_USED','Rejected or unresolved claim influences a certain decision')
    for status,signal,kinds in ((('KNOWN_EXPLOITED',),r.exploitation_signal,{'KNOWN_EXPLOITED'}),
        (('VERIFIED_POC_ASSOCIATION',),r.exploitation_signal,{'POC_EXISTS','POC_ASSOCIATION'}),
        (('CONFIRMED_PRESENT',),r.patch_availability,{'FIXED_VERSION','PATCH_EXISTS','FIX_COMMIT'})):
        if signal.status in status and (not signal.claim_ids or not all(grounded(c,id) and claims[id].claim.claim_type in kinds for id in signal.claim_ids)):
            fail('CANDIDATE_ESCALATED','Candidate/unknown cannot become confirmed exploitation or patch')
    for a in r.recommended_actions:
        if a.fixed_version:
            fix=[claims[id] for id in a.claim_ids if id in claims and grounded(c,id) and claims[id].claim.claim_type=='FIXED_VERSION']
            if (a.action_provenance!='VERIFIED_CLAIM' or not fix or not any(f.claim.value.get('version')==a.fixed_version for f in fix)
                or r.patch_availability.status!='CONFIRMED_PRESENT'):
                fail('UNSUPPORTED_PRECISE_PATCH','Exact release advice requires a matching verified fix claim')
        if a.patch_reference and a.action_provenance!='VERIFIED_CLAIM':fail('UNSUPPORTED_PRECISE_PATCH','Patch reference cannot be general precaution')
    asset=c.asset_snapshot
    if asset and (r.asset_id!=asset.asset_id or r.version!=asset.deployed_version):fail('INVENTORY_RESULT_MISMATCH','Analysis identity/version differs from its fixed inventory snapshot')
    return finish('consistency',issues)
