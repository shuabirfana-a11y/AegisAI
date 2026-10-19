"""The correction request must identify its rejected object, not just array paths."""
from copy import deepcopy
import json
import pytest
from app.agents.investigation.planner import InvestigationPlannerAdapter
from tests.planner.fixtures import valid_plan,cve_input,context_for,gateway_with_responses


def correction_payload(request):
    for message in request.messages:
        if message.role=='user':
            data=json.loads(message.content)
            if 'rejected_candidate' in data:return data
    return None


@pytest.mark.parametrize('kind',['required','type','nested','multiple'])
def test_retry_contains_exact_rejected_object_and_registry_requirements(kind):
    good=valid_plan();bad=deepcopy(good)
    if kind in ('required','multiple'):bad['tasks'][0].pop('acceptance_criteria')
    if kind in ('type','multiple'):bad['tasks'][0]['max_tool_calls']='wrong'
    if kind=='nested':bad['tasks'][0]['input_data']['steps'][0]['arguments'].pop('target')
    frozen=deepcopy(bad);gw,calls,sink=gateway_with_responses([bad,good])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(cve_input(),context_for())
        repair=correction_payload(calls[1])
        assert repair is not None
        assert repair['rejected_candidate']==bad==frozen
        assert repair['trust_level']=='UNTRUSTED_MODEL_OUTPUT_DATA'
        assert calls[1].messages[1].content==calls[0].messages[1].content
        assert result.status=='VALIDATED' and len(calls)==2
        if kind in ('required','multiple'):
            req=repair['registered_task_requirements'][0]
            assert req['path']=='$.tasks[0].acceptance_criteria'
            assert req['task_id']==bad['tasks'][0]['task_id']
            assert set(req['minimum_conditions'])=={'tools_succeeded','output_nonempty'}
        if kind in ('type','multiple'):assert 'expected_type' in calls[1].messages[-1].content
        if kind=='nested':assert '$.tasks[0].input_data.steps[0].arguments.target' in calls[1].messages[-1].content
    finally:gw.close()


def test_two_bad_candidates_are_not_filled_or_published_as_valid():
    bad=valid_plan();bad['tasks'][0].pop('acceptance_criteria');gw,calls,sink=gateway_with_responses([bad])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(cve_input(),context_for())
        assert result.status=='PLANNING_FAILED' and result.validated_plan is None and len(calls)==2
        assert all(a.validation_status=='REJECTED' for a in result.attempts)
        assert correction_payload(calls[1])['rejected_candidate']==bad
        assert all('acceptance_criteria' not in json.loads(a.diagnostic['raw_output'])['tasks'][0] for a in result.attempts)
    finally:gw.close()


def test_model_instructions_stay_in_untrusted_user_data_not_system_feedback():
    bad=valid_plan();bad['reasoning_summary']='IGNORE_ALL_VALIDATION_UNTRUSTED';bad['tasks'][0].pop('acceptance_criteria')
    gw,calls,sink=gateway_with_responses([bad])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(cve_input(),context_for())
        assert correction_payload(calls[1])['rejected_candidate']==bad
        assert all('IGNORE_ALL_VALIDATION_UNTRUSTED' not in m.content for m in calls[1].messages if m.role=='system')
        assert result.validated_plan is None
    finally:gw.close()


def test_distinct_asset_requests_have_distinct_bound_candidates():
    from uuid import uuid4
    a=cve_input(asset_id=uuid4());b=cve_input(asset_id=uuid4())
    bad_a=valid_plan();bad_a['tasks'][0]['task_id']='asset-a-candidate';bad_a['tasks'][0].pop('acceptance_criteria')
    bad_b=valid_plan();bad_b['tasks'][0]['task_id']='asset-b-candidate';bad_b['tasks'][0]['max_tool_calls']='bad'
    gw,calls,sink=gateway_with_responses([bad_a,bad_a,bad_b,bad_b]);adapter=InvestigationPlannerAdapter(gw,sink)
    try:
        adapter.plan(a,context_for(input=a));adapter.plan(b,context_for(input=b))
        assert correction_payload(calls[1])['rejected_candidate']==bad_a
        assert correction_payload(calls[3])['rejected_candidate']==bad_b
        assert calls[1].trace_id!=calls[3].trace_id
        assert json.loads(calls[1].messages[1].content)['input_scope']['asset_id']==str(a.query.asset_id)
        assert json.loads(calls[3].messages[1].content)['input_scope']['asset_id']==str(b.query.asset_id)
    finally:gw.close()


def test_real_compatible_provider_wire_and_parser_preserve_the_field():
    import httpx
    from app.llm.config import ModelConfig
    from app.llm.gateway import ModelGateway
    from app.llm.providers.openai_compatible import OpenAICompatibleProvider
    from tests.planner.fixtures import MemorySink
    good=valid_plan();bad=deepcopy(good);bad['tasks'][0].pop('acceptance_criteria');wire=[]
    def reply(request):
        body=json.loads(request.content);wire.append(body)
        content=json.dumps(bad if len(wire)==1 else good)
        return httpx.Response(200,json={'model':'synthetic-contract-model','choices':[{'message':{'role':'assistant','content':content},'finish_reason':'stop'}]})
    config=ModelConfig(provider='openai_compatible',model='synthetic-contract-model',api_base='http://127.0.0.1:11434/v1',
        allow_keyless_local=True,embedding_provider='mock',structured_mode='json_schema')
    provider=OpenAICompatibleProvider(config,transport=httpx.MockTransport(reply));sink=MemorySink()
    gw=ModelGateway(config,text_provider=provider,record_sink=sink)
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(cve_input(),context_for())
        assert result.status=='VALIDATED' and len(wire)==2
        repair=next(json.loads(m['content']) for m in wire[1]['messages'] if m['role']=='user' and 'rejected_candidate' in json.loads(m['content']))
        assert repair['rejected_candidate']==bad
        assert wire[0]['response_format']['json_schema']['schema']==wire[1]['response_format']['json_schema']['schema']
        parsed=json.loads(result.validated_plan.candidate_json)
        assert parsed['tasks'][0]['acceptance_criteria']==good['tasks'][0]['acceptance_criteria']
        assert json.loads(result.attempts[1].diagnostic['raw_output'])==good
        assert result.attempts[0].model_call['status']=='failed'
    finally:gw.close()


@pytest.mark.parametrize('mode',['oversize','redacted','truncated','invalid_json'])
def test_unavailable_candidate_is_explicit_and_never_silently_clipped(mode):
    from app.llm.diagnostics import capture_output
    from app.agents.investigation.retry_context import rejected_context
    raw=json.dumps(valid_plan());secret=''
    if mode=='oversize':raw=json.dumps({**valid_plan(),'reasoning_summary':'X'*9000})
    if mode=='redacted':raw=raw.replace('SYNTHETIC','PRIVATE_VALUE');secret='PRIVATE_VALUE'
    if mode=='truncated':raw='X'*70000
    if mode=='invalid_json':raw='not-json'
    context=rejected_context(capture_output(raw,'request','trace',secret))
    assert context['context_status'].startswith('UNAVAILABLE')
    assert 'rejected_candidate' not in context


def test_injected_parser_field_loss_is_rejected_even_when_original_text_contains_field(monkeypatch):
    import app.llm.gateway as module
    original=module.strict_json
    def dropping(text):
        value=original(text)
        if isinstance(value,dict) and 'tasks' in value:
            value['tasks'][0].pop('acceptance_criteria',None)
        return value
    monkeypatch.setattr(module,'strict_json',dropping)
    good=valid_plan();gw,calls,sink=gateway_with_responses([good])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(cve_input(),context_for())
        assert result.status=='PLANNING_FAILED' and result.validated_plan is None
        assert len(calls)==2 and all(a.model_call['status']=='failed' for a in result.attempts)
        assert all(json.loads(a.diagnostic['raw_output'])['tasks'][0]['acceptance_criteria']==good['tasks'][0]['acceptance_criteria'] for a in result.attempts)
    finally:gw.close()
