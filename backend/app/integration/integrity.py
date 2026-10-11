"""Typed identities and exact source references; formal receipt auth is in Loader."""
from app.agents.contracts import fingerprint
from app.integration.rules_common import check,finish,assessments,evidence_map,facts

def check_integrity(c):
    issues=[];i,v,r=c.investigation,c.verification,c.analysis
    def fail(code,msg,refs=()):issues.append(check('integrity',code,msg,'FATAL',refs=refs))
    arts=[a for a in (i,v,r) if a]
    if len({a.artifact_id for a in arts})!=len(arts):fail('DUPLICATE_ARTIFACT','Duplicate artifact identity')
    for key,a in (('investigation',i),('verification',v),('analysis',r)):
        ref=getattr(c.request,key)
        if a and ref and (a.run_id,a.task_id,a.artifact_id,a.schema_version)!=(ref.run_id,ref.task_id,ref.artifact_id,ref.schema_version):fail('ARTIFACT_REFERENCE_MISMATCH','Result identity differs from reference')
    if i and v and (v.source_run_id,v.source_artifact_id)!=(i.run_id,i.artifact_id):fail('VERIFICATION_HANDOFF_MISMATCH','Verification does not consume selected investigation')
    if i and v and r and r.input_artifact_ids!=(i.artifact_id,v.artifact_id):fail('ANALYSIS_HANDOFF_MISMATCH','Analysis does not consume selected source artifacts')
    if v:
        ids=[a.claim.claim_id for a in v.claims]
        if len(ids)!=len(set(ids)):fail('DUPLICATE_CLAIM','Duplicate claim decision')
        es=(*v.supporting_evidence,*v.conflicting_evidence);seen={}
        for e in es:
            if e.evidence_id in seen and seen[e.evidence_id]!=fingerprint(e.model_dump(mode='json')):fail('EVIDENCE_ID_COLLISION','Same evidence id has different content')
            seen[e.evidence_id]=fingerprint(e.model_dump(mode='json'))
        refs=evidence_map(c)
        for a in v.claims:
            for id in (*a.supporting_evidence_ids,*a.conflicting_evidence_ids):
                if id not in refs:fail('EVIDENCE_REFERENCE_INVALID','Claim points to missing evidence',(id,))
            if i and a.claim.vulnerability_id!=i.vulnerability_id:fail('CLAIM_TARGET_MISMATCH','Claim belongs to a different vulnerability',(a.claim.claim_id,))
        if c.verification_source:
            source=c.verification_source
            if v.source_snapshot_hash!=fingerprint(source.model_dump(mode='json')):fail('SOURCE_SNAPSHOT_HASH_INVALID','Verification source hash changed')
            originals={a.claim_id:a for a in source.claims}
            for a in v.claims:
                raw=originals.get(a.claim.claim_id)
                # The existing B2 kernel adds the evaluated status to a Claim.
                # Value/scope/revision remain the sealed source facts.
                if raw is None or fingerprint(raw.model_dump(mode='json',exclude={'status'}))!=fingerprint(a.claim.model_dump(mode='json',exclude={'status'})):fail('CLAIM_REVISION_MISMATCH','Verification claim changed relative to original source',(a.claim.claim_id,))
        for f in facts(c):
            for id in getattr(f,'evidence_ids',()):
                if id not in refs:fail('EVIDENCE_REFERENCE_INVALID','Downstream fact points to missing evidence',(id,))
            for id in getattr(f,'claim_ids',()):
                if id not in assessments(c):fail('CLAIM_REFERENCE_INVALID','Downstream fact points to missing claim',(id,))
        if r:
            for ref in r.evidence_refs:
                e=refs.get(ref.get('evidence_id'))
                if e is None or ref.get('hash')!=e.hash or ref.get('reference')!=e.reference or ref.get('claim_id')!=e.claim_id:
                    fail('EVIDENCE_REFERENCE_INVALID','Risk evidence pointer does not match the verification source')
    return finish('integrity',issues)
