"""Synthetic provenance fixtures; no exploits executed, no live network."""
import hashlib
from uuid import uuid4
import pytest
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select, func
from app.db import models as m
from app.utils.time import utcnow


def api_module():
    import importlib
    try:
        return importlib.import_module('app.enrichment.poc_artifacts')
    except ModuleNotFoundError:
        pytest.fail('Typed PoC artifact projection is not implemented')


def candidate(db, seed, *, usable=False, age=0, validating=None):
    from datetime import timedelta
    now=utcnow()-timedelta(days=age)
    # Store the exact public source excerpt; do not mutate existing Evidence.
    body=b'SYNTHETIC static association. No exploit was executed.'
    raw=m.RawDocument(source_id=seed.sources[0].id,external_id='synthetic-poc-'+uuid4().hex,
        source_url='https://github.com/test/fixture',retrieved_at=now,content_type='text/plain',
        raw_payload=body,content_hash=hashlib.sha256(body).hexdigest(),publisher='SYNTHETIC',completeness='complete')
    db.add(raw);db.flush()
    obs=m.SourceObservation(source_id=raw.source_id,raw_document_id=raw.id,external_id=raw.external_id,
        record_type='repository',retrieved_at=now,http_status=200,lineage_key='synthetic-poc',
        publisher='SYNTHETIC',parse_status='parsed',normalizer_version='SYNTHETIC')
    db.add(obs);db.flush()
    p=m.PocCandidate(vulnerability_id=seed.vuln.id,source_id=raw.source_id,observation_id=obs.id,
        url='https://github.com/test/'+uuid4().hex,canonical_url='https://github.com/test/'+uuid4().hex,
        repository='test/fixture',candidate_type='repository',status='confirmed' if usable else 'candidate',
        usability_status='verified_usable' if usable else 'not_evaluated',first_seen_at=now,last_seen_at=now,
        details={'description':'SYNTHETIC candidate','language':'Python','association_only':True})
    db.add(p);db.flush()
    value={'url':p.url,'usability':'verified_usable'} if usable else {'url':p.url,'association':'candidate'}
    claim=m.Claim(claim_key=uuid4().hex,vulnerability_id=seed.vuln.id,poc_candidate_id=p.id,
        claim_type='POC_USABILITY' if usable else 'POC_ASSOCIATION',predicate='POC_USABILITY' if usable else 'POC_ASSOCIATION',
        value_json=value,scope_key='synthetic-'+uuid4().hex,adopted=usable,verification_status='confirmed' if usable else 'pending')
    db.add(claim);db.flush()
    e=m.Evidence(claim_id=claim.id,source_id=raw.source_id,raw_document_id=raw.id,observation_id=obs.id,
        scope_key=claim.scope_key,evidence_type='repository_readme',stance='support',
        excerpt=body.decode(),excerpt_hash=hashlib.sha256(body).hexdigest(),source_url=raw.source_url,
        retrieved_at=now,locator={'text_span':[0,len(body)]},locator_key='synthetic-poc',
        observed_value=value,publisher='SYNTHETIC',lineage_key=obs.lineage_key,
        details={'explicit':True,'validated_exploit':usable if validating is None else validating})
    db.add(e);db.flush()
    return p,claim,e


def human_result(db, claim, e):
    result=m.VerificationResult(claim_id=claim.id,claim_revision=claim.revision,decision_key=uuid4().hex,
        status='confirmed',verification_method='human',reason_summary='SYNTHETIC pre-existing validation',
        verified_at=utcnow(),verified_by_type='human',verified_by_id='SYNTHETIC reviewer')
    db.add(result);db.flush()
    db.add(m.VerificationEvidence(verification_result_id=result.id,claim_id=claim.id,evidence_id=e.id));db.flush()
    return result


def test_artifact_is_typed_and_association_does_not_verify_exploit(db,seed):
    module=api_module();p,claim,e=candidate(db,seed)
    got=module.poc_page(db,seed.vuln.id)
    item=next(x for x in got.items if x.id==p.id)
    assert got.status=='POC_CANDIDATE' and item.status=='POC_CANDIDATE'
    assert item.evidence_ref==(e.id,) and item.language=='Python'
    assert item.verified_time is None and item.exploit_executed is False
    with pytest.raises(ValidationError):item.status='VERIFIED_EXPLOIT'


def test_verified_requires_current_human_result_and_linked_evidence(db,seed):
    module=api_module();p,c,e=candidate(db,seed,usable=True)
    assert module.poc_page(db,seed.vuln.id).status=='POC_CANDIDATE'
    result=human_result(db,c,e)
    page=module.poc_page(db,seed.vuln.id);item=next(x for x in page.items if x.id==p.id)
    assert item.status=='VERIFIED_EXPLOIT' and item.verified_time==result.verified_at
    c.revision+=1;db.flush()
    assert module.poc_page(db,seed.vuln.id).status=='POC_CANDIDATE'


def test_conflict_cannot_be_verified(db,seed):
    module=api_module();p,c,e=candidate(db,seed,usable=True);human_result(db,c,e)
    c.verification_status='conflict';db.flush()
    assert module.poc_page(db,seed.vuln.id).status=='POC_CANDIDATE'


def test_future_human_verification_cannot_establish_current_usability(db,seed):
    from datetime import timedelta
    module=api_module();p,c,e=candidate(db,seed,usable=True)
    result=m.VerificationResult(claim_id=c.id,claim_revision=c.revision,decision_key=uuid4().hex,
        status='confirmed',verification_method='human',reason_summary='SYNTHETIC future result',
        verified_at=utcnow()+timedelta(days=2),verified_by_type='human',verified_by_id='SYNTHETIC')
    db.add(result);db.flush()
    db.add(m.VerificationEvidence(verification_result_id=result.id,claim_id=c.id,evidence_id=e.id));db.flush()
    assert module.poc_page(db,seed.vuln.id).status=='POC_CANDIDATE'


def test_candidate_source_must_match_its_original_observation(db,seed):
    module=api_module();p,c,e=candidate(db,seed)
    p.source_id=seed.sources[1].id;db.flush()
    assert module.poc_page(db,seed.vuln.id).status=='NO_EVIDENCE'


def test_stale_validation_cannot_borrow_freshness_from_another_evidence(db,seed):
    module=api_module();p,c,old=candidate(db,seed,usable=True,age=60)
    other,_,base=candidate(db,seed)
    fresh=m.Evidence(claim_id=c.id,source_id=base.source_id,raw_document_id=base.raw_document_id,
        observation_id=base.observation_id,scope_key=c.scope_key,evidence_type=base.evidence_type,
        stance='support',excerpt=base.excerpt,excerpt_hash=base.excerpt_hash,source_url=base.source_url,
        retrieved_at=base.retrieved_at,locator=base.locator,locator_key='synthetic-fresh-nonvalidating',
        observed_value=c.value_json,publisher=base.publisher,lineage_key=base.lineage_key,details={'explicit':True})
    db.add(fresh);db.flush();result=human_result(db,c,old)
    db.add(m.VerificationEvidence(verification_result_id=result.id,claim_id=c.id,evidence_id=fresh.id));db.flush()
    item=next(x for x in module.poc_page(db,seed.vuln.id).items if x.id==p.id)
    assert item.status=='POC_CANDIDATE'


def test_human_result_cannot_verify_evidence_acquired_after_review(db,seed):
    from datetime import timedelta
    module=api_module();p,c,old=candidate(db,seed,usable=True,age=10,validating=False)
    other,_,base=candidate(db,seed)
    fresh=m.Evidence(claim_id=c.id,source_id=base.source_id,raw_document_id=base.raw_document_id,
        observation_id=base.observation_id,scope_key=c.scope_key,evidence_type=base.evidence_type,
        stance='support',excerpt=base.excerpt,excerpt_hash=base.excerpt_hash,source_url=base.source_url,
        retrieved_at=base.retrieved_at,locator=base.locator,locator_key='synthetic-later-validation',
        observed_value=c.value_json,publisher=base.publisher,lineage_key=base.lineage_key,
        details={'explicit':True,'validated_exploit':True})
    db.add(fresh);db.flush()
    result=m.VerificationResult(claim_id=c.id,claim_revision=c.revision,decision_key=uuid4().hex,
        status='confirmed',verification_method='human',reason_summary='SYNTHETIC earlier result',
        verified_at=utcnow()-timedelta(days=2),verified_by_type='human',verified_by_id='SYNTHETIC')
    db.add(result);db.flush()
    for e in (old,fresh):db.add(m.VerificationEvidence(verification_result_id=result.id,claim_id=c.id,evidence_id=e.id))
    db.flush()
    assert next(x for x in module.poc_page(db,seed.vuln.id).items if x.id==p.id).status=='POC_CANDIDATE'


def test_absence_reports_search_state_without_fake_artifact(db,seed):
    page=api_module().poc_page(db,seed.vuln.id)
    assert page.status=='NO_EVIDENCE' and page.items==() and page.search_status=='NOT_RUN'
    assert page.omitted_count==1 and page.warnings


def test_damaged_provenance_is_omitted(db,seed):
    module=api_module();p,c,e=candidate(db,seed)
    # An invalid source URL must not poison the valid page or leak credentials.
    p.url='https://user:credential@github.com/test/private';db.flush()
    page=module.poc_page(db,seed.vuln.id)
    assert page.status=='NO_EVIDENCE' and 'credential' not in page.model_dump_json()


def test_public_projection_excludes_asset_scoped_evidence(db,seed):
    module=api_module();p,c,e=candidate(db,seed)
    c.poc_candidate_id=None;c.asset_component_id=seed.component.id;db.flush()
    assert module.poc_page(db,seed.vuln.id).status=='NO_EVIDENCE'


def test_page_status_is_independent_of_current_page_and_reads_are_pure(db,seed):
    module=api_module();p,c,e=candidate(db,seed);p2,c2,e2=candidate(db,seed,usable=True);human_result(db,c2,e2)
    before=db.scalar(select(func.count()).select_from(m.VerificationResult))
    page=module.poc_page(db,seed.vuln.canonical_id,offset=99,limit=1)
    assert page.status=='VERIFIED_EXPLOIT' and page.total==2 and page.items==()
    assert db.scalar(select(func.count()).select_from(m.VerificationResult))==before


@pytest.mark.parametrize('url',['javascript:alert(1)','file:///tmp/poc','http://127.0.0.1/poc',
    'https://user:pass@github.com/a/b','https://github.com/a/b?api_key=secret','not-a-url',
    'http://service.local./poc','http://service.internal./poc',
    'https://github.com/a/b?X-Amz-Credential=SYNTHETIC&X-Amz-Signature=SYNTHETIC',
    'https://github.com/a/b?auth_token=SYNTHETIC','https://github.com/a/b#access_token=SYNTHETIC'])
def test_invalid_reference_is_rejected(url):
    module=api_module()
    with pytest.raises(ValidationError):TypeAdapter(module.PublicReference).validate_python(url)


def test_invalid_state_or_missing_evidence_is_rejected():
    module=api_module()
    now=utcnow()
    data=dict(id=uuid4(),vulnerability_id=uuid4(),source='GITHUB',reference='https://github.com/test/fixture',
        title='SYNTHETIC',created_time=now,evidence_ref=(),association_status='candidate',usability_status='not_evaluated')
    with pytest.raises(ValidationError):module.POCArtifact(**data,status='POC_CANDIDATE')
    with pytest.raises(ValidationError):module.POCArtifact(**{**data,'evidence_ref':(uuid4(),)},status='BAD')
    with pytest.raises(ValidationError):module.POCArtifact(**{**data,'source':'','evidence_ref':(uuid4(),)},status='POC_CANDIDATE')


def test_http_query_is_read_only_typed_paginated_and_not_found(db,seed,engine):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.api.dependencies import get_session
    candidate(db,seed);app=create_app(engine);app.dependency_overrides[get_session]=lambda:db
    path='/api/v1/intelligence/vulnerabilities/'+seed.vuln.canonical_id+'/poc'
    client=TestClient(app)
    response=client.get(path)
    assert response.status_code==200, response.text
    assert response.json()['status']=='POC_CANDIDATE'
    assert client.get(path+'?limit=101').status_code==422
    assert client.post(path).status_code==405
    assert client.get('/api/v1/intelligence/vulnerabilities/not-found/poc').status_code==404


def test_poc_openapi_has_all_fields_and_exact_states():
    from app.main import create_app
    schema=create_app().openapi()
    assert '/api/v1/intelligence/vulnerabilities/{id}/poc' in schema['paths']
    dto=schema['components']['schemas']['POCArtifact']
    assert {'id','vulnerability_id','source','reference','title','description','language','status',
        'created_time','verified_time','evidence_ref'}<=set(dto['properties'])
    assert set(dto['properties']['status']['enum'])=={'NO_EVIDENCE','POC_CANDIDATE','VERIFIED_EXPLOIT'}


def test_existing_enricher_emits_evidence_linked_artifact_after_verification(db,seed):
    import base64,httpx
    from test_phase7_enrichers import acquire
    from app.enrichment.service import EnrichmentService
    from app.enrichment.enrichers.poc import PocEnricher
    cve=seed.vuln.canonical_id
    repo={'full_name':'research/'+cve,'description':'SYNTHETIC static reproduction candidate',
        'language':'Python','owner':{'login':'research'},'fork':False}
    readme=('SYNTHETIC '+cve+' vllm 0.8.2; reproduction description only.').encode()
    def handler(req):
        if '/search/' in req.url.path:return httpx.Response(200,json={'total_count':1,'incomplete_results':False,'items':[repo]})
        return httpx.Response(200,json={'encoding':'base64','content':base64.b64encode(readme).decode(),'size':len(readme)})
    acq=acquire(db,handler)
    svc=EnrichmentService(acq.factory,http=acq.http,enrichers=[PocEnricher()])
    try:result=svc.run(seed.vuln.canonical_id,'poc')[0]
    finally:acq.http.close()
    assert result.status!='FAILED',result.errors
    snapshot=result.artifacts.get('poc_snapshot')
    assert snapshot is not None
    item=next(x for x in snapshot['items'] if x['title']=='research/'+cve)
    assert item['status']=='POC_CANDIDATE' and item['language']=='Python'
    assert item['evidence_ref'] and item['verification'] and item['exploit_executed'] is False
    job=db.get(m.EnrichmentJob,result.task_id)
    assert job.result['artifacts']['poc_snapshot']==snapshot


def test_list_detail_and_poc_endpoint_have_consistent_provenance_status(db,seed):
    from app.monitoring.views import vulnerability_view
    module=api_module();p,c,e=candidate(db,seed,usable=True);human_result(db,c,e)
    assert vulnerability_view(db,seed.vuln.id).poc_status==module.poc_page(db,seed.vuln.id).status=='VERIFIED_EXPLOIT'
    p.source_id=seed.sources[1].id;db.flush()
    assert vulnerability_view(db,seed.vuln.id).poc_status==module.poc_page(db,seed.vuln.id).status=='NO_EVIDENCE'


@pytest.mark.parametrize('payload,locator',[(b'[]',{'json_pointer':'/content'}),(b'{}',{'json_pointer':[]}),
    (b'{"encoding":"base64","content":[],"size":0}',{'json_pointer':'/content'}),
    (b'{"encoding":"base64","content":{"value":"SYNTHETIC"},"size":0}',{'json_pointer':'/content'})])
def test_malformed_readme_or_locator_is_invalid_evidence_not_api_failure(payload,locator):
    from types import SimpleNamespace
    module=api_module();sid,rid,oid,cid=[uuid4() for _ in range(4)]
    raw=SimpleNamespace(id=rid,source_id=sid,source_url='https://github.com/test/fixture',
        raw_payload=payload,content_hash=hashlib.sha256(payload).hexdigest())
    obs=SimpleNamespace(source_id=sid,raw_document_id=rid)
    ev=SimpleNamespace(raw_document_id=rid,observation_id=oid,source_id=sid,source_url=raw.source_url,
        scope_key='scope',excerpt=payload.decode(),excerpt_hash=hashlib.sha256(payload).hexdigest(),
        locator=locator,evidence_type='repository_readme')
    class Session:
        def get(self,kind,key):return raw if kind is m.RawDocument else obs
    assert module.intact_evidence(Session(),ev,SimpleNamespace(scope_key='scope')) is False


def test_long_evidence_history_preserves_current_candidate_with_explicit_bounds(db,seed):
    module=api_module();p,c,e=candidate(db,seed)
    for i in range(130):
        db.add(m.Evidence(claim_id=c.id,source_id=e.source_id,raw_document_id=e.raw_document_id,
            observation_id=e.observation_id,scope_key=e.scope_key,evidence_type=e.evidence_type,stance=e.stance,
            excerpt=e.excerpt,excerpt_hash=e.excerpt_hash,source_url=e.source_url,retrieved_at=e.retrieved_at,
            locator=e.locator,locator_key='synthetic-history-'+str(i),observed_value=e.observed_value,
            publisher=e.publisher,lineage_key=e.lineage_key,details=e.details))
    db.flush()
    item=next(x for x in module.poc_page(db,seed.vuln.id).items if x.id==p.id)
    assert item.status=='POC_CANDIDATE' and len(item.evidence)==128
    assert item.omitted_evidence_count==3


def test_history_clipping_preserves_the_actual_validating_evidence(db,seed):
    module=api_module();p,c,e=candidate(db,seed,usable=True);result=human_result(db,c,e)
    for i in range(130):
        other=m.Evidence(claim_id=c.id,source_id=e.source_id,raw_document_id=e.raw_document_id,
            observation_id=e.observation_id,scope_key=e.scope_key,evidence_type=e.evidence_type,stance=e.stance,
            excerpt=e.excerpt,excerpt_hash=e.excerpt_hash,source_url=e.source_url,retrieved_at=e.retrieved_at,
            locator=e.locator,locator_key='synthetic-nonvalidating-'+str(i),observed_value=e.observed_value,
            publisher=e.publisher,lineage_key=e.lineage_key,details={'explicit':True})
        db.add(other);db.flush()
        db.add(m.VerificationEvidence(verification_result_id=result.id,claim_id=c.id,evidence_id=other.id))
    db.flush()
    item=next(x for x in module.poc_page(db,seed.vuln.id).items if x.id==p.id)
    assert item.status=='VERIFIED_EXPLOIT' and item.omitted_evidence_count==3
    assert next(x for x in item.evidence if x.id==e.id).supports_exploit_validation is True


def test_malformed_readme_keeps_search_evidence_and_partial_snapshot(db,seed):
    import httpx
    from test_phase7_enrichers import acquire
    from app.enrichment.service import EnrichmentService
    from app.enrichment.enrichers.poc import PocEnricher
    def handler(req):
        return httpx.Response(200,json={'items':[{'full_name':'research/'+seed.vuln.canonical_id,
            'owner':{'login':'research'}}],'total_count':1}) if '/search/' in req.url.path else httpx.Response(200,json=[])
    acq=acquire(db,handler)
    try:result=EnrichmentService(acq.factory,http=acq.http,enrichers=[PocEnricher()]).run(seed.vuln.canonical_id,'poc')[0]
    finally:acq.http.close()
    assert result.status=='PARTIAL' and result.artifacts['poc_snapshot']['total']==1
    assert result.artifacts['poc_snapshot']['items'][0]['status']=='POC_CANDIDATE'
    assert result.artifacts['poc_snapshot']['items'][0]['evidence']
