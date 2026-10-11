"""Production producer formats found by the single independent final review."""
import base64,json,hashlib
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from app.utils.time import utcnow
from app.agents.verification.snapshot import scope_supported,_quoted
from app.agents.verification.rules import evaluate_snapshot
from app.agents.verification.context_store import VerificationContextStore
from app.enrichment.acquisition import decode_readme
from app.enrichment.evidence import EvidenceService
from tests.agents.verification.helpers import claim,evidence,context
from tests.agents.verification.conftest import verification_seed
from tests.agents.verification.test_end_to_end import source_for
from tests.agents.verification.test_snapshot import request
from tests.agents.verification.test_runtime import service

SCOPES={x['source_id']:x['authority_level'] for x in json.loads(
    (Path(__file__).parents[3]/'app/resources/sources.json').read_text(encoding='utf-8'))}


@pytest.mark.parametrize('key,kind,value,allowed',[
    ('CISA_KEV','KNOWN_EXPLOITED',{'known_exploited':True},True),
    ('CISA_KEV','KNOWN_EXPLOITED',{'known_exploited':False},False),
    ('CISA_KEV','AFFECTS_VERSION',{'raw_expression':'<=0.6'},False),
    ('OSV','AFFECTS_VERSION',{'ecosystem':'PyPI','package':'vllm','raw_expression':'<=0.6'},True),
    ('OSV','FIXED_VERSION',{'ecosystem':'PyPI','package':'vllm','version':'0.7'},True),
    ('OSV','KNOWN_EXPLOITED',{'known_exploited':True},False),
    ('CVE_LIST','AFFECTS_PRODUCT',{'ecosystem':'PyPI','package':'vllm'},True),
    ('CVE_LIST','POC_EXISTS',{'url':'https://example.invalid/poc'},False),
])
def test_catalog_scope_is_limited_to_its_existing_claim_contract(key,kind,value,allowed):
    c=claim(claim_type=kind,value=value)
    assert scope_supported(SCOPES[key],c,source_key=key)==allowed


def test_actual_kev_scope_reaches_original_positive_membership_rule():
    c=claim(claim_type='KNOWN_EXPLOITED',value={'known_exploited':True})
    e=evidence(source_key='CISA_KEV',source_type='kev_record',evidence_type='kev_record',
        authority_scope=SCOPES['CISA_KEV'],observed_value=c.value)
    assert evaluate_snapshot(context([c],[e])).verification_status=='CONFIRMED'


@pytest.mark.parametrize('repo,url,allowed',[
    ('vllm-project/vllm','https://api.github.com/repos/vllm-project/vllm/security-advisories/GHSA-xxxx-yyyy-zzzz',True),
    ('unrelated/repo','https://api.github.com/repos/vllm-project/vllm/security-advisories/GHSA-xxxx-yyyy-zzzz',False),
    ('vllm-project/vllm','https://api.github.com/repos/unrelated/repo/security-advisories/GHSA-xxxx-yyyy-zzzz',False),
])
def test_package_less_vendor_confirmation_binds_exact_repository(repo,url,allowed):
    c=claim(claim_type='VENDOR_CONFIRMED',value={'repository':repo,'advisory_id':'GHSA-xxxx-yyyy-zzzz',
        'cve':'CVE-2099-9999001'},scope_key='vendor:'+repo)
    assert scope_supported('vllm-project/vllm',c,source_key='VENDOR_VLLM',reference={'url':url})==allowed


def test_github_is_static_candidate_evidence_not_version_or_exploit_authority():
    scope='Public hosting metadata; no exploit authority'
    c=claim(claim_type='POC_ASSOCIATION',value={'url':'https://github.com/example/poc','repository':'example/poc'})
    e=evidence(source_key='GITHUB',source_type='repository_readme',evidence_type='repository_readme',
        authority_level='community',authority_scope=scope,observed_value=c.value,
        reference={'url':'https://api.github.com/repos/example/poc/readme'},details={'classification':'CANDIDATE','explicit':True})
    got=evaluate_snapshot(context([c],[e]))
    assert got.verification_status=='PENDING' and got.confidence<=0.49
    assert not scope_supported(scope,claim(),source_key='GITHUB')
    assert not scope_supported('FIRST EPSS probability only',c,source_key='EPSS')


def payload(text):
    return {'encoding':'base64','size':len(text.encode()),'content':base64.b64encode(text.encode()).decode()}


@pytest.mark.parametrize('change,quote,valid',[
    ({},'SYNTHETIC decoded README',True),({},'invented quote',False),
    ({'encoding':'hex'},'SYNTHETIC decoded README',False),
    ({'content':'!invalid!'},'SYNTHETIC decoded README',False),
    ({'size':524289},'SYNTHETIC decoded README',False),
    ({'content':'YQ=='*200000},'SYNTHETIC decoded README',False),
])
def test_readme_quote_reconstructs_only_bounded_original_encoding(change,quote,valid):
    data={**payload('SYNTHETIC decoded README'),**change}
    raw=SimpleNamespace(raw_payload=json.dumps(data).encode())
    stored=SimpleNamespace(evidence_type='repository_readme',locator={'json_pointer':'/content'},excerpt=quote)
    assert _quoted(raw,stored)==valid


def test_decoded_readme_truncation_matches_producer_without_relaxing_other_types():
    text='SYNTHETIC '+('x'*3000);raw=SimpleNamespace(raw_payload=json.dumps(payload(text)).encode())
    stored=SimpleNamespace(evidence_type='repository_readme',locator={'json_pointer':'/content'},excerpt=text[:2400])
    assert _quoted(raw,stored)
    stored.evidence_type='structured_source'
    assert not _quoted(raw,stored)


def test_existing_readme_producer_reaches_real_gateway_as_candidate(engine):
    seed=verification_seed.__wrapped__(engine);now=utcnow();suffix=uuid4().hex
    with transaction(engine) as db:
        source=m.Source(source_key='GITHUB',name='GitHub',source_type='api',category='enrichment',
            authority_level='community',authority_scope='Public hosting metadata; no exploit authority',
            acquisition_method='fixture',base_url='https://api.github.com')
        from sqlalchemy import select
        existing=db.scalar(select(m.Source).where(m.Source.source_key=='GITHUB'))
        if existing:source=existing
        else:db.add(source);db.flush()
        text='SYNTHETIC '+seed.cve+' vLLM proof of concept README; not executed.'
        body=json.dumps(payload(text)).encode();url='https://api.github.com/repos/SYNTHETIC/'+suffix+'/readme'
        raw=m.RawDocument(source_id=source.id,external_id='readme:'+suffix,source_url=url,
            retrieved_at=now,content_type='application/json',raw_payload=body,
            content_hash=hashlib.sha256(body).hexdigest(),publisher='SYNTHETIC')
        db.add(raw);db.flush()
        obs=m.SourceObservation(source_id=source.id,raw_document_id=raw.id,external_id=raw.external_id,
            record_type='enrichment',retrieved_at=now,parse_status='parsed',lineage_key='github:SYNTHETIC/'+suffix,
            publisher='SYNTHETIC',normalizer_version='TEST',normalized_payload=payload(text))
        db.add(obs);db.flush()
        value={'url':'https://github.com/SYNTHETIC/'+suffix,'repository':'SYNTHETIC/'+suffix,'association':'candidate'}
        c=m.Claim(claim_key='SYNTHETIC-readme:'+suffix,vulnerability_id=seed.vulnerability_id,
            claim_type='POC_ASSOCIATION',predicate='POC_ASSOCIATION',scope_key='poc:SYNTHETIC/'+suffix,value_json=value)
        db.add(c);db.flush()
        stored=EvidenceService.add(db,c,obs,value,{'json_pointer':'/content'},evidence_type='repository_readme',
            details={'classification':'CANDIDATE'},excerpt=decode_readme(payload(text)))
        claim_id=str(c.id);evidence_id=str(stored.id)
    src=source_for(engine,seed);req=request(src,task_type='claim_validation',claim_ids=(claim_id,))
    ctx=VerificationContextStore(engine).capture(req,actor=seed.actor)
    e=next(e for e in ctx.snapshot.evidence if e.evidence_id==evidence_id)
    assert e.integrity_status=='VALID' and e.authority_level=='community'
    svc=service(engine);out=svc.read_results(svc.run(req,actor=seed.actor).run_id,actor=seed.actor)
    assert out.artifacts[0].verification_status=='PENDING'
    assert out.artifacts[0].supporting_evidence[0].evidence_id==evidence_id
    assert any('POC_NOT_EXECUTED' in x for x in out.artifacts[0].warnings)
