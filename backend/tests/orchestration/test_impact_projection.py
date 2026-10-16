"""Existing immutable answers stay compatible; new scope survives public DTOs."""
from tests.agents.verification.helpers import claim,evidence
from app.agents.verification.impact_normalization import normalize_bundle
from app.investigation_api.projection import public_copy
from app.orchestration.composer import safe_value

def test_public_artifact_retains_the_actual_range_field():
    value={'ecosystem':'PyPI','package':'vllm','range':'<2.4.3','parse_status':'parsed','headers':{'Authorization':'secret'}}
    got=public_copy({'value':value})['value']
    assert got['range']=='<2.4.3' and got['parse_status']=='parsed'
    assert 'headers' not in got

def test_legacy_fact_value_is_not_recomposed_with_new_fields():
    from app.orchestration.composer import project_fact_value
    c=claim(value={'ecosystem':'PyPI','package':'vllm','range':'<2.4.3','parse_status':'parsed'})
    assert project_fact_value(c,verification_state='CONFIRMED',confidence=0.95)==safe_value(c.value)

def test_normalized_confirmed_fact_delivers_scope_and_original_evidence_bindings():
    from app.orchestration.composer import project_fact_value
    c=claim(value={'ecosystem':'PyPI','package':'vllm','range':'<2.4.3','parse_status':'parsed'})
    e=evidence(observed_value=c.value)
    cs,es=normalize_bundle((c,),(e,))
    value=project_fact_value(cs[0],verification_state='CONFIRMED',confidence=0.95)
    got=public_copy({'value':value})['value'];assert got['range']=='<2.4.3'
    scope=got['impact_scope'];assert scope['verification_state']=='CONFIRMED'
    assert scope['affected_version_range'][0]['upper']=='2.4.3'
    assert scope['source_claim_ids']==['C1'] and scope['evidence_refs'][0]['source_claim_id']=='C1'
