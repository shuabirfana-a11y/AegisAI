"""Actual source-format disagreement, without a model or database fixture."""
import json,sys
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.enrichment.evidence import origin
from app.enrichment.rules import evaluate_claim

def original_pair():
    return json.loads((ROOT/'work/final-evidence-quality-review/origin-reproduction.json').read_text(encoding='utf-8'))

def test_declared_upstream_and_advisory_snapshot_have_one_origin():
    data=original_pair()
    origins=[origin(SimpleNamespace(**o)) for o in data['observations']]
    assert set(origins)=={'github:advisory-database'}

def test_original_pair_cannot_confirm_by_double_counting():
    data=original_pair();wires=[]
    for o,w in zip(data['observations'],data['wires']):
        wires.append({**w,'lineage':origin(SimpleNamespace(**o)),'retrieved_at':datetime.fromisoformat(w['retrieved_at'])})
    result=evaluate_claim(data['kind'],data['value'],wires,datetime.fromisoformat(data['evaluation_time']))
    assert result['independent_groups']==['github:advisory-database']
    assert result['status']=='INSUFFICIENT_EVIDENCE'

GHSA='GHSA-aaaa-bbbb-cccc'
UPSTREAM=f'https://github.com/github/advisory-database/blob/main/advisories/github-reviewed/2025/01/{GHSA}/{GHSA}.json'
def observation(url,*,identifier=GHSA):
    return SimpleNamespace(external_id=identifier,lineage_key='raw-origin',normalized_payload={
        'external_id':identifier,'packages':[{'name':'torch','ecosystem':'PyPI'}],
        'upstream_lineage':[url],'references':[]})

def test_exact_declared_advisory_database_origin_precedes_package_hint():
    assert origin(observation(UPSTREAM))=='github:advisory-database'

def test_existing_maintainer_primary_reference_keeps_precedence():
    o=observation(UPSTREAM)
    o.normalized_payload['references']=[{'url':f'https://github.com/pytorch/pytorch/security/advisories/{GHSA}'}]
    assert origin(o)=='github:pytorch/pytorch'

@pytest.mark.parametrize('url',[
    UPSTREAM.replace('github.com/','github.com.evil.invalid/'),
    UPSTREAM.replace('https://','http://'),
    UPSTREAM.replace('github.com/','user@github.com/'),
    UPSTREAM.replace('github/advisory-database/','another/advisory-database/'),
    UPSTREAM.replace(GHSA,'GHSA-dddd-eeee-ffff'),
])
def test_unrelated_or_spoofed_origin_does_not_merge(url):
    assert origin(observation(url))=='github:pytorch/pytorch'

def test_conflicting_observation_identifiers_do_not_supply_origin():
    o=observation(UPSTREAM);o.normalized_payload['ghsa_id']='GHSA-dddd-eeee-ffff'
    assert origin(o)=='github:pytorch/pytorch'

def test_original_package_fallback_still_works_without_declared_source():
    assert origin(observation('https://example.org/review'))=='github:pytorch/pytorch'

def test_genuinely_independent_origins_are_not_collapsed():
    now=datetime.now(timezone.utc)
    a=SimpleNamespace(external_id='independent-a',normalized_payload={},lineage_key='publisher:a')
    b=SimpleNamespace(external_id='independent-b',normalized_payload={},lineage_key='publisher:b')
    evidence=[{'id':str(i),'lineage':origin(o),'authority':'authoritative','explicit':True,'is_current':True,
        'stance':'support','value':{'version':'1.0.1'},'retrieved_at':now,'evidence_type':'structured_source'} for i,o in enumerate([a,b])]
    assert evaluate_claim('FIXED_VERSION',{'version':'1.0.1'},evidence,now)['status']=='CONFIRMED'
