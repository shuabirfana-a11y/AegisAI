"""SYNTHETIC bound scope transport; no Gold and no trust threshold changes."""
from copy import deepcopy
from uuid import uuid4
import pytest
from app.enrichment.version_scope import VersionScopeNormalizer
from app.agents.investigation.normalize import normalize_investigation
from tests.agents.investigation.helpers import detail, source, execution

def case():
    document={'vulnerabilities':[
        {'package':{'ecosystem':'pip','name':'example-engine'},
         'vulnerable_version_range':'>=4.0.0, <4.2.5','patched_versions':'4.2.5'},
        {'package':{'ecosystem':'pip','name':'example-engine'},
         'vulnerable_version_range':'<3.8.1','patched_versions':'3.8.1'}]}
    claims=[];refs=[]
    for index,version in enumerate(('4.2.5','3.8.1')):
        claim={'id':str(uuid4()),'revision':1,'claim_type':'FIXED_VERSION',
               'scope_key':'PyPI:example-engine','value_json':{'ecosystem':'PyPI',
               'package':'example-engine','version':version},'trusted':False,
               'verification_status':'UNVERIFIED','details':{}}
        ref=source(evidence_id=str(uuid4()),claim_id=claim['id'],claim_revision=1,
                   stance='support',hash='a'*64)
        scope=VersionScopeNormalizer().normalize('FIXED_VERSION',claim['value_json'],
            document=document,locator={'json_pointer':f'/vulnerabilities/{index}/patched_versions'},
            evidence_id=ref['evidence_id'],raw_document_id=ref['raw_document_id'],
            raw_hash=ref['hash'],integrity_verified=True)
        assert scope is not None
        ref['normalized_version_scope']=scope.model_dump(mode='json')
        claims.append(claim);refs.append(ref)
    data=detail();data['intelligence']['claims']=claims
    return data,refs

def project(data,refs):
    task,_,out=execution(data,refs)
    return normalize_investigation(task,out)

def test_bound_parallel_entries_reach_existing_comparator_without_becoming_confirmed():
    data,refs=case();result=project(data,refs)
    assert result.status=='COMPLETE' and not result.conflicts
    assert result.information_status=='CANDIDATE'
    assert all(ref['verified'] is False for ref in result.evidence)

@pytest.mark.parametrize('field',['evidence_id','raw_document_id','raw_hash','kind','value_hash','component','product'])
def test_tampered_scope_binding_keeps_conservative_conflict(field):
    data,refs=case()
    refs[0]['normalized_version_scope'][field]=('AFFECTS_VERSION' if field=='kind' else 'tampered')
    assert project(data,refs).status=='CONFLICT'

def test_missing_scope_keeps_existing_conflict_behavior():
    data,refs=case()
    for ref in refs:ref.pop('normalized_version_scope')
    assert project(data,refs).status=='CONFLICT'

def test_explicit_open_conflict_is_never_hidden_by_compatible_scopes():
    data,refs=case();data['intelligence']['conflicts']=[{'status':'open',
        'scope_key':'PyPI:example-engine','conflict_type':'VERSION_CONFLICT'}]
    result=project(data,refs)
    assert result.status=='CONFLICT' and result.conflicts

def test_projection_keeps_original_bound_proofs_immutable():
    data,refs=case();before=deepcopy((data,refs));project(data,refs)
    assert (data,refs)==before
