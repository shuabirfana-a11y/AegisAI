from app.tooling.attestation import claim_key,evidence_key

def integrate(artifacts,*,claims_attested=frozenset(),evidence_attested=frozenset()):
    if any(a.status in ('failed','blocked') for a in artifacts):return {'status':'REPLAN_REQUIRED','reason':'Required tasks failed or handoff was rejected'}
    claims=[c for a in artifacts for c in a.claims]
    if any(c.get('verification_status')=='CONFIRMED' and not c.get('trusted') for c in claims):
        return {'status':'FAILED','reason':'A claimed confirmation did not pass the existing scoped trust service'}
    for artifact in artifacts:
        for claim in artifact.claims:
            if claim.get('verification_status')!='CONFIRMED':continue
            if claim_key(claim) not in claims_attested:
                return {'status':'FAILED','reason':'Claim was not attested by a current trusted gateway output'}
            if not any(ref.get('claim_id')==str(claim.get('id')) and ref.get('claim_revision')==claim.get('revision')
                and ref.get('verified') is True and ref.get('stance')=='support' and ref.get('raw_document_id')
                and ref.get('url') and ref.get('locator') and ref.get('evidence_id') and evidence_key(ref) in evidence_attested for ref in artifact.evidence_refs):
                return {'status':'FAILED','reason':'Confirmation lacks current scoped supporting provenance'}
    if any(c.get('verification_status')=='CONFLICT' for c in claims):return {'status':'HUMAN_REVIEW_REQUIRED','reason':'Source claims conflict; review required'}
    # Asset uncertainty is surfaced without converting an unknown match into safety.
    for a in artifacts:
        for result in a.result.get('tool_results',[]):
            if result.get('tool')=='get_asset_risks' and any(r.get('match_status')=='UNCERTAIN' for r in result.get('data',{}).get('items',[])):
                return {'status':'HUMAN_REVIEW_REQUIRED','reason':'Asset identity, range or freshness remains uncertain'}
    warned=any(a.warnings or a.unresolved or a.status=='partial' for a in artifacts)
    return {'status':'PASS_WITH_WARNINGS' if warned else 'PASS','reason':'Accepted structured handoffs; source assertions remain explicitly scoped'}
