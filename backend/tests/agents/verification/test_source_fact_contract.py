"""Twenty hand-checked SYNTHETIC contract/guard cases, not Benchmark answers."""
import pytest
from datetime import timedelta
from app.enrichment.contracts import ClaimType
from app.enrichment.parsing import parse_advisory
from app.agents.verification.rules import evaluate_snapshot
from app.agents.verification.snapshot import scope_supported, CATALOG_SCOPES
from tests.agents.verification.helpers import claim, evidence, context

CASES = ['cve','ghsa','affected-lt','affected-lte','fixed','cvss','severity',
    'product-mismatch','component-mismatch','missing-version','insufficient-evidence',
    'agreeing-sources','conflicting-sources','official','blog','paper','multi-asset',
    'multi-hop','raw-not-convertible','claim-without-evidence']

def source():
    return {'cve_id':'CVE-2099-9999001','ghsa_id':'GHSA-test-test-test','state':'published',
        'summary':'SYNTHETIC exact source summary','cwes':[{'cwe_id':'CWE-502'}],
        'vulnerabilities':[{'package':{'ecosystem':'pip','name':'vllm'},
            'vulnerable_version_range':'<3.0','patched_versions':'3.0.0'}]}

def facts(payload):
    assert 'CWE' in set(ClaimType) and 'SOURCE_FACT' in set(ClaimType), 'Formal fact types missing'
    from app.enrichment.source_facts import extract_source_facts
    return extract_source_facts(payload,'CVE-2099-9999001',['GHSA-test-test-test'])

def fact_pair():
    c=claim(claim_type='CWE',value={'cwe':'CWE-502'},scope_key='cwe:CWE-502',package_identifier_id=None)
    e=evidence(observed_value=c.value,scope_key=c.scope_key)
    return c,e

@pytest.mark.parametrize('case',CASES)
def test_twenty_source_fact_and_preserved_guard_cases(case):
    if case in ('cve','ghsa'):
        payload=source()
        if case=='ghsa':payload['cve_id']=None
        items=facts(payload)
        assert {x['type'] for x in items}=={'CWE','SOURCE_FACT'}
        assert next(x for x in items if x['type']=='CWE')['value']=={'cwe':'CWE-502'}
        assert next(x for x in items if x['type']=='SOURCE_FACT')['value']['text']==payload['summary']
        payload['cve_id']='CVE-2099-9999002'
        assert facts(payload)==[]  # GHSA must not override a contradictory CVE.
    elif case in ('affected-lt','affected-lte','fixed','cvss','severity'):
        payload=source()
        if case=='affected-lte':payload['vulnerabilities'][0]['vulnerable_version_range']='<=3.0'
        payload['cvss_severities']={'cvss_v3':{'vector_string':'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H','score':9.8}}
        rows=parse_advisory(payload,'vllm-project/vllm',payload['cve_id'],[])['claims']
        if case.startswith('affected'):
            v=next(x['value'] for x in rows if x['type']=='AFFECTS_VERSION')
            assert v['range']==('<3.0' if case=='affected-lt' else '<=3.0')
        elif case=='fixed':assert next(x['value'] for x in rows if x['type']=='FIXED_VERSION')['version']=='3.0.0'
        else:
            v=next(x['value'] for x in rows if x['type']=='CVSS_SCORE')
            assert v['score']==9.8 and v['severity']=='critical' and v['version']=='3.1'
    elif case in ('product-mismatch','component-mismatch','missing-version','insufficient-evidence','multi-asset','claim-without-evidence'):
        c=claim();e=evidence()
        if case in ('product-mismatch','component-mismatch'):e=e.model_copy(update={'observed_value':{**e.observed_value,'package':'other-component'}})
        if case=='missing-version':c=claim(expression='older versions');e=evidence(expression='older versions')
        if case=='insufficient-evidence':e=e.model_copy(update={'hash':None,'raw_document_id':None})
        if case=='multi-asset':e=e.model_copy(update={'scope_key':'asset:B','claim_id':'OTHER-ASSET-CLAIM'})
        result=evaluate_snapshot(context([c],[] if case=='claim-without-evidence' else [e]))
        assert result.verification_status!='CONFIRMED'
        if case=='missing-version':assert result.claims[0].claim.value['raw_expression']=='older versions'
        else:assert not result.supporting_evidence
    elif case in ('agreeing-sources','conflicting-sources','multi-hop'):
        c=claim();e=evidence();e2=evidence('E2',lineage_key='vendor-two')
        if case=='conflicting-sources':e2=evidence('E2',expression='<0.7',lineage_key='vendor-two')
        result=evaluate_snapshot(context([c],[e,e2]))
        assert result.verification_status==('CONFLICT' if case=='conflicting-sources' else 'CONFIRMED')
        assert {x.evidence_id for x in result.supporting_evidence}|{x.evidence_id for x in result.conflicting_evidence}=={'E1','E2'}
        if case=='conflicting-sources':assert result.conflicts and result.conflicts[0].evidence_ids==('E1','E2')
    elif case in ('official','blog','paper'):
        c,e=fact_pair()
        if case!='official':
            e=e.model_copy(update={'authority_level':'secondary','source_type':'security_blog' if case=='blog' else 'research_paper',
                'evidence_type':'source_excerpt'})
        result=evaluate_snapshot(context([c],[e]))
        assert result.verification_status==('CONFIRMED' if case=='official' else 'PENDING')
        if case=='official':
            assert scope_supported(CATALOG_SCOPES['OSV'],c,source_key='OSV')
            assert evaluate_snapshot(context([c],[e.model_copy(update={'retrieved_at':e.retrieved_at-timedelta(days=31)})])).verification_status!='CONFIRMED'
        else:assert result.confidence<0.5
    elif case=='raw-not-convertible':
        payload=source();payload['cwes']=[];payload.pop('summary');payload['title']='probably CWE-502'
        assert facts(payload)==[]
        payload['summary']='older versions';payload['cwes']=[{'cwe_id':'arbitrary'}]
        rows=facts(payload)
        assert {x['type'] for x in rows}=={'SOURCE_FACT'}
        assert not any('version' in x['value'] for x in rows)

def test_auxiliary_fact_projection_is_typed_and_redacted():
    from app.orchestration.composer import safe_impact_value, project_fact_value
    c,e=fact_pair()
    assert project_fact_value(c,verification_state='CONFIRMED',confidence=.95)=={'cwe':'CWE-502'}
    assert safe_impact_value({'field':'summary','text':'source secret=abc123'})=={'field':'summary','text':'source secret=[REDACTED]'}
    assert safe_impact_value({'cwe':'not-a-cwe','secret':'abc'})=={}

def test_fact_selection_is_explicit_and_old_request_serialization_stays_identical():
    from app.agents.verification.schemas import VerificationRequest
    req=context().request
    assert 'include_source_facts' not in req.model_dump(mode='json')
    updated=VerificationRequest.model_validate({**req.model_dump(mode='json'),'include_source_facts':True})
    assert updated.include_source_facts is True
