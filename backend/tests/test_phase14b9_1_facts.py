"""Real relational provenance from SYNTHETIC HTTP fixtures, never gold data."""
import json
from types import SimpleNamespace
import httpx,pytest
from sqlalchemy import select,func
from app.db import models as m
from app.enrichment.source_facts import persist_source_facts
from app.agents.verification.snapshot import _claim,_evidence
from app.agents.verification.rules import evaluate_snapshot
from app.enrichment.acquisition import VENDORS
from app.utils.time import utcnow
from tests.test_phase7_enrichers import context,acquire
from tests.agents.verification.helpers import context as verification_context

@pytest.mark.parametrize('key',['VENDOR_LANGGRAPH','VENDOR_PYTORCH','VENDOR_VLLM'])
def test_same_generic_writer_reader_and_verifier_across_three_products(db,seed,key):
    ctx=context(db,seed);repo=VENDORS[key]
    body={'cve_id':ctx.canonical_id,'ghsa_id':ctx.aliases[0], 'state':'published',
        'summary':'SYNTHETIC exact summary for '+repo,'cwes':[{'cwe_id':'CWE-502'}]}
    doc=acquire(db,lambda req:httpx.Response(200,json=body)).fetch(key,
        'https://api.github.com/repos/'+repo+'/security-advisories/'+ctx.aliases[0],repo+':'+ctx.aliases[0],'github:'+repo)
    obs=db.get(m.SourceObservation,doc.observation_id)
    ids,eids=persist_source_facts(db,ctx,obs)
    assert len(ids)==len(eids)==2
    assert persist_source_facts(db,ctx,obs)==(ids,eids)
    claims=[];evidence=[]
    for cid,eid in zip(ids,eids):
        stored=db.get(m.Claim,cid);e=db.get(m.Evidence,eid)
        assert stored.verification_status=='pending' and not stored.adopted
        c=_claim({col.name:getattr(stored,'details' if col.name=='metadata' else col.name)
            for col in m.Claim.__table__.columns},'lookup',str(ctx.target_id))
        assert e.claim_id==stored.id and e.source_id==obs.source_id and e.raw_document_id==doc.raw_id
        raw=db.get(m.RawDocument,e.raw_document_id)
        assert e.source_url==raw.source_url and e.excerpt_hash and e.locator['json_pointer']
        ve=_evidence(db,e,c,{'source_key':key,'source_id':str(obs.source_id),'authority_level':'official',
            'authority_scope':repo,'claim_revision':stored.revision,'is_current':True},utcnow())
        assert ve.integrity_status=='VALID' and not ve.exclusion_reasons
        claims.append(c.model_copy(update={'evidence_ids':(str(e.id),)}));evidence.append(ve)
    result=evaluate_snapshot(verification_context(claims,evidence,include_source_facts=True))
    assert result.verification_status=='CONFIRMED'
    assert {x.claim.claim_type for x in result.claims}=={'CWE','SOURCE_FACT'}
    assert {x.evidence_id for x in result.supporting_evidence}==set(map(str,eids))
    e=db.get(m.Evidence,eids[0]);copy=SimpleNamespace(**{('details' if col.name=='metadata' else col.name):
        getattr(e,'details' if col.name=='metadata' else col.name) for col in m.Evidence.__table__.columns})
    copy.excerpt='SYNTHETIC tampered content'
    ve=_evidence(db,copy,claims[0],{'source_key':key,'authority_level':'official','authority_scope':repo,'is_current':True},utcnow())
    assert ve.integrity_status=='INVALID'
    assert evaluate_snapshot(verification_context([claims[0]],[ve],include_source_facts=True)).verification_status!='CONFIRMED'

@pytest.mark.parametrize('field,value',[('cve_id','CVE-2099-9999002'),('state','withdrawn')])
def test_wrong_root_or_withdrawn_source_cannot_create_formal_facts(db,seed,field,value):
    ctx=context(db,seed);key='VENDOR_VLLM';repo=VENDORS[key]
    body={'cve_id':ctx.canonical_id,'ghsa_id':ctx.aliases[0],'state':'published','summary':'SYNTHETIC','cwes':[{'cwe_id':'CWE-502'}],field:value}
    doc=acquire(db,lambda req:httpx.Response(200,json=body)).fetch(key,
        'https://api.github.com/repos/'+repo+'/security-advisories/'+ctx.aliases[0],repo+':'+ctx.aliases[0],'github:'+repo)
    before=db.scalar(select(func.count()).select_from(m.Claim))
    assert persist_source_facts(db,ctx,db.get(m.SourceObservation,doc.observation_id))==([],[])
    assert db.scalar(select(func.count()).select_from(m.Claim))==before
