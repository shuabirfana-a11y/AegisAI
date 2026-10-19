"""CNA inline constraints are ranges, never a guessed fixed release."""
from copy import deepcopy
from datetime import datetime,timezone
from uuid import uuid4
import pytest
from app.normalizers.cve import normalize
from app.enrichment.versions import intervals,contains

NOW=datetime(2026,10,17,tzinfo=timezone.utc)

def record(version,**extra):
    return {'dataType':'CVE_RECORD','dataVersion':'5.2',
        'cveMetadata':{'cveId':'CVE-2099-9999008','state':'PUBLISHED'},
        'containers':{'cna':{'descriptions':[{'lang':'en','value':'SYNTHETIC version scope'}],
            'affected':[{'product':'vllm','versions':[{'version':version,'status':'affected',**extra}]}]}}}

@pytest.mark.parametrize('expression,inside,outside',[
    ('< 4.8.2','4.8.1','4.8.2'),('<= 4.8.2','4.8.2','4.8.3'),
    ('>= 4.1.0, < 4.8.2','4.2.0','4.0.0'),('<4.8.2,>=4.1.0','4.2.0','4.0.0'),
    ('== 4.8.2','4.8.2','4.8.1'),('>= 4.1.0','5.0.0','4.0.0')])
def test_inline_cna_constraint_survives_downstream_version_consumption(expression,inside,outside):
    source=record(expression);before=deepcopy(source)
    result=normalize(source,uuid4(),NOW);scope=result.affected_versions[0]
    assert source==before and scope['parse_status']=='parsed'
    assert scope['package']['name']=='vllm' and scope['package']['ecosystem']=='PyPI'
    value={**scope,'ecosystem':'PyPI'}
    assert intervals(value) is not None
    assert contains(value,inside) is True and contains(value,outside) is False
    assert not result.fixed_versions and scope['fixed'] is None
    assert expression in scope['raw_expression']
    assert scope['locator']=='/containers/cna/affected/0/versions/0'

@pytest.mark.parametrize('extra',[{'versionType':'semver'},{'changes':[{'at':'4.1.0','status':'unaffected'}]},
    {'lessThan':'5.0.0'},{'lessThanOrEqual':'5.0.0'}])
def test_unsupported_or_mixed_scope_is_not_silently_reinterpreted(extra):
    scope=normalize(record('<4.8.2',**extra),uuid4(),NOW).affected_versions[0]
    assert scope['parse_status']=='unsupported'
    assert scope['fixed'] is None

@pytest.mark.parametrize('literal',['n/a','<banana','<4.8.2 || >=5.0.0','latest'])
def test_invalid_inline_values_remain_unsupported(literal):
    result=normalize(record(literal),uuid4(),NOW)
    assert result.affected_versions[0]['parse_status']!='parsed'
    assert not result.fixed_versions

def test_structured_bounds_and_exact_version_keep_existing_semantics():
    for source,inside,outside in [(record('4.1.0',lessThan='4.8.2'),'4.2.0','4.8.2'),
            (record('4.8.2'),'4.8.2','4.8.1')]:
        result=normalize(source,uuid4(),NOW);scope=result.affected_versions[0]
        assert scope['parse_status']=='parsed' and not result.fixed_versions
        # Existing exact/structured projection is unchanged by the inline adapter.
        assert scope['package']['name']=='vllm'


def test_same_raw_reprocesses_under_new_normalizer_without_overwriting_old_observation(db):
    import json
    from sqlalchemy import select
    from app.db import models as m
    from app.db.persistence import store_raw
    from app.repositories.sources import source_registry
    from app.repositories import ingestion
    from app.normalizers import cve
    from app.services.versions import blank
    from app.enrichment.context import EnrichmentContext
    from app.enrichment.enrichers.version import VersionEnricher
    from app.enrichment.verification import VerificationService
    source=source_registry(db,'CVE_LIST');payload=record('< 4.8.2')
    raw=store_raw(db,source_id=source.id,external_id=payload['cveMetadata']['cveId'],
        source_url='https://example.invalid/SYNTHETIC-cna',retrieved_at=NOW,
        content_type='application/json',raw_payload=json.dumps(payload).encode(),
        publisher='SYNTHETIC',completeness='complete')
    new=normalize(payload,raw.id,NOW);old=new.model_copy(deep=True)
    scope=old.affected_versions[0]
    old.affected_versions[0]={**scope,**blank(scope['raw_expression'])}
    original_version=ingestion.NORMALIZER_VERSIONS['CVE_LIST']
    try:
        ingestion.NORMALIZER_VERSIONS['CVE_LIST']='cve-normalizer-v0.2'
        ingestion.persist_record(db,source,raw,old)
        ingestion.NORMALIZER_VERSIONS['CVE_LIST']=cve.VERSION
        replay=ingestion.persist_record(db,source,raw,new)
    finally:ingestion.NORMALIZER_VERSIONS['CVE_LIST']=original_version
    assert replay['outcome']=='updated'
    observations=list(db.scalars(select(m.SourceObservation).where(m.SourceObservation.raw_document_id==raw.id,
        m.SourceObservation.parse_status=='parsed')))
    assert len(observations)==2
    by_version={x.normalizer_version:x for x in observations}
    assert by_version['cve-normalizer-v0.2'].normalized_payload['affected_versions'][0]['parse_status']=='unsupported'
    assert by_version[cve.VERSION].normalized_payload['affected_versions'][0]['parse_status']=='parsed'
    assert len({x.raw_document_id for x in observations})==1
    ctx=EnrichmentContext.load(db,payload['cveMetadata']['cveId'])
    class NoNetwork:
        checked=[]
        def fetch(self,*a,**k):pytest.fail('CNA range recovery must not invent remote evidence')
    out=VersionEnricher().investigate(ctx,db,NoNetwork())
    claims=[db.get(m.Claim,x) for x in out.claims]
    affected=[x for x in claims if x.claim_type=='AFFECTS_VERSION']
    assert affected and not any(x.claim_type=='FIXED_VERSION' for x in claims)
    assert contains(affected[0].value_json,'4.8.1') is True
    assert contains(affected[0].value_json,'4.8.2') is False
    assert VerificationService.verify(db,affected[0],now=NOW).status=='insufficient'
