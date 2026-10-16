"""Actual HTTP + stored source quote + Runtime + Risk, SYNTHETIC not Benchmark."""
import json,hashlib
from uuid import uuid4,UUID
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.db import models as m
from app.db.session import transaction
from app.main import create_app
from app.utils.time import utcnow
from tests.investigation_api.test_multi_asset_database import setup_batch
from tests.investigation_api.test_multi_asset_chain import plans,configure,HEADERS,wait
from tests.planner.fixtures import gateway_with_responses

def source_constraint(engine,seed):
    now=utcnow()
    with transaction(engine) as db:
        fixed=db.scalar(select(m.Claim).where(m.Claim.vulnerability_id==seed.vulnerability_id,m.Claim.claim_type=='FIXED_VERSION'))
        ev=db.scalar(select(m.Evidence).where(m.Evidence.claim_id==fixed.id))
        official=db.get(m.Source,ev.source_id)
        payload=json.dumps({'vulnerabilities':[{'patched_versions':'>= 0.7.0'}]}).encode()
        raw=m.RawDocument(source_id=official.id,external_id=seed.cve+'-fixed',source_url=official.base_url,
            published_at=now,retrieved_at=now,content_type='application/json',raw_payload=payload,
            content_hash=hashlib.sha256(payload).hexdigest(),publisher=official.name)
        db.add(raw);db.flush()
        obs=m.SourceObservation(source_id=official.id,raw_document_id=raw.id,external_id=raw.external_id,
            record_type='vulnerability',retrieved_at=now,parse_status='parsed',publisher=official.name,
            lineage_key='SYNTHETIC-shared-upstream:'+str(official.id),normalizer_version='TEST',
            normalized_payload={'canonical_id':seed.cve})
        db.add(obs);db.flush()
        value={**fixed.value_json,'version':None,'raw_expression':'>= 0.7.0'}
        fixed.value_json=value
        quote=json.dumps('>= 0.7.0');quote_hash=hashlib.sha256(quote.encode()).hexdigest()
        locator={'json_pointer':'/vulnerabilities/0/patched_versions'}
        db.add(m.Evidence(claim_id=fixed.id,source_id=official.id,raw_document_id=raw.id,observation_id=obs.id,
            scope_key=fixed.scope_key,evidence_type='official_vendor_advisory',stance='support',
            excerpt=quote,excerpt_hash=quote_hash,source_url=raw.source_url,
            published_at=now,retrieved_at=now,locator=locator,locator_key='fixed-constraint',
            observed_value=value,publisher=official.name,lineage_key=obs.lineage_key,details={'explicit':True}))
        index=m.Source(source_key='SYNTHETIC_INDEX_'+uuid4().hex,name='SYNTHETIC reprint',source_type='osv',
            category='vulnerability',authority_level='authoritative',authority_scope='vulnerability affected versions fixes',
            acquisition_method='fixture',base_url='https://example.invalid/SYNTHETIC_REPRINT')
        db.add(index);db.flush()
        index_raw=m.RawDocument(source_id=index.id,external_id=seed.cve+'-index-fixed',source_url=index.base_url,
            published_at=now,retrieved_at=now,content_type='application/json',raw_payload=payload,
            content_hash=hashlib.sha256(payload).hexdigest(),publisher=official.name)
        db.add(index_raw);db.flush()
        index_obs=m.SourceObservation(source_id=index.id,raw_document_id=index_raw.id,external_id=index_raw.external_id,
            record_type='vulnerability',retrieved_at=now,parse_status='parsed',publisher=official.name,
            lineage_key=obs.lineage_key,normalizer_version='TEST',normalized_payload={'canonical_id':seed.cve})
        db.add(index_obs);db.flush()
        parsed={**value,'version':'0.7.0'}
        duplicate=m.Claim(claim_key='SYNTHETIC_DUP_'+uuid4().hex,vulnerability_id=seed.vulnerability_id,
            package_identifier_id=seed.package_id,claim_type='FIXED_VERSION',predicate='FIXED_VERSION',
            scope_key=fixed.scope_key,value_json=parsed)
        db.add(duplicate);db.flush()
        db.add(m.Evidence(claim_id=duplicate.id,source_id=index.id,raw_document_id=index_raw.id,observation_id=index_obs.id,
            scope_key=duplicate.scope_key,evidence_type='normalized_version',stance='support',
            excerpt=quote,excerpt_hash=quote_hash,source_url=raw.source_url,
            published_at=now,retrieved_at=now,locator=locator,locator_key='fixed',
            observed_value=parsed,publisher=official.name,lineage_key=obs.lineage_key,details={'explicit':True}))
        # The index is intentionally a reprint, not another official authority.
        return {str(fixed.id),str(duplicate.id)},value

def test_source_fixed_constraint_reaches_two_assets_without_cross_version_pollution(engine,monkeypatch):
    seed,old=setup_batch(engine);old.close()
    ids,original=source_constraint(engine,seed)
    gw,calls,_=gateway_with_responses(plans(seed));configure(monkeypatch,seed)
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            reply=client.post('/api/investigations/batches',headers=HEADERS,json={
                'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)],
                'idempotency_key':uuid4().hex})
            assert reply.status_code==202,reply.text
            result=wait(client,reply.json()['batch_id'])
            rows={i['snapshot']['asset_id']:i for i in result['items']}
            assert rows[str(seed.asset_id)]['impact']=='AFFECTED',result
            assert rows[str(seed.second_asset_id)]['impact']=='NOT_AFFECTED',result
            for item in rows.values():
                answer=client.get('/api/investigations/'+item['investigation_id']+'/answer',headers=HEADERS)
                assert answer.status_code==200,answer.text
                facts=answer.json()['verified_claims']
                scopes=[f['value']['impact_scope'] for f in facts if f['claim_type']=='FIXED_VERSION']
                assert len(scopes)==1 and set(scopes[0]['source_claim_ids'])==ids
                assert scopes[0]['fixed_version']=='0.7.0' and scopes[0]['verification_state']=='CONFIRMED'
                assert scopes[0]['evidence_refs'] and scopes[0]['asset_id']==item['snapshot']['asset_id']
                affect=next(f for f in facts if f['claim_type']=='AFFECTS_VERSION')
                assert affect['value']['impact_scope']['affected_version_range']
            assert len(calls)==2
        with transaction(engine) as db:
            rows=list(db.scalars(select(m.Claim).where(m.Claim.id.in_([UUID(x) for x in ids]))))
            assert any(c.value_json==original for c in rows)
    finally:gw.close()
