"""Explicit user inputs only; no real advisories or benchmark answers."""
import importlib
from copy import deepcopy
from uuid import uuid4
import pytest


def normalize(question,values=None,bindings=None):
    try:mod=importlib.import_module('app.agents.investigation.normalization')
    except ModuleNotFoundError:pytest.fail('Question normalization is missing')
    return mod.normalize_question(question,values or {},bindings or {})


def test_explicit_component_version_and_cve_are_extracted_from_question():
    q='我的 vLLM 0.6.0 是否受 CVE-2099-9999001 影响？'
    n=normalize(q)
    assert n.vulnerability_id=='CVE-2099-9999001'
    assert n.component['name']=='vllm' and n.version=='0.6.0'
    assert n.objective==q and n.task_type=='version_impact'
    assert n.provenance['version']=='QUESTION_EXPLICIT_COMPONENT_VERSION'


def test_cvss_version_and_advisory_range_are_not_asset_version():
    n=normalize('查询 CVE-2099-9999001 的 CVSS 3.1 和影响范围 vLLM <0.7.0。')
    assert n.version is None and n.component['name']=='vllm'
    assert n.task_type=='vulnerability_fact'


def test_missing_context_stays_unknown_and_does_not_create_asset():
    n=normalize('分析某AI框架漏洞风险')
    assert n.vulnerability_id is n.component is n.version is None
    assert n.asset_context=={} and n.input_status=='INPUT_REQUIRED'
    assert n.task_type=='asset_risk'


def test_explicit_context_binding_preserved_without_mutation():
    aid=str(uuid4());cid=str(uuid4())
    values={'target':'CVE-2099-9999001','component':'private-component','version':'2.0','ecosystem':'PyPI'}
    saved=deepcopy(values)
    n=normalize('分析此演示资产的风险',values,{'asset_id':aid,'component_id':cid})
    assert n.version=='2.0' and n.asset_context=={'asset_id':aid,'component_id':cid}
    assert values==saved and n.provenance['version']=='INPUT_CONTEXT'


def test_explicit_null_version_is_not_filled_from_question():
    n=normalize('vLLM 0.6.0 是否受 CVE-2099-9999001 影响？',{'component':'vllm','version':None})
    assert n.version is None and n.input_status=='INPUT_REQUIRED'


def test_disagreeing_user_context_is_rejected_before_planning():
    with pytest.raises(ValueError,match='NORMALIZATION_INPUT_CONFLICT'):
        normalize('vLLM 0.6.0 是否受 CVE-2099-9999001 影响？',{'component':'vllm','version':'9.9'})


def test_multiple_component_versions_remain_ambiguous():
    n=normalize('vLLM 0.6.0 和 torch 2.5.1 有什么风险？')
    assert n.component is None and n.version is None
    assert n.input_status=='AMBIGUOUS' and n.warnings


def test_conflict_intent_is_not_a_verification_verdict():
    n=normalize('CVE-2099-9999001 的两个来源影响范围冲突，请调查证据。')
    assert n.task_type=='evidence_conflict'
    assert not {'verification_status','expected_answer','confirmed'}&set(n.model_dump())


def test_normalizer_rejects_nested_gold_metadata():
    with pytest.raises(ValueError,match='LABEL_METADATA_FORBIDDEN'):
        normalize('调查问题',{'component':{'name':'vllm','nested':{'expected_answer':'AFFECTED'}}})


@pytest.mark.parametrize('value',['UNKNOWN','unknown','未知',''])
def test_absent_version_marker_is_not_a_version_observation(value):
    n=normalize('此vLLM是否受影响？',{'component':'vllm','version':value})
    assert n.version is None and n.component['version'] is None


def test_explicit_asset_conditions_are_preserved_but_no_identity_is_created():
    n=normalize('分析vLLM资产风险',{'component':'vllm','environment':'staging','exposure':'private'})
    assert n.asset_context=={'environment':'staging','exposure':'private'}
    assert 'asset_context' in n.missing_fields


@pytest.mark.parametrize('text',[
    'Affected range for CVE-2099-9999001: vLLM 0.6.0 to 0.7.0',
    'CVE-2099-9999001 的受影响版本为 vLLM 0.6.0 至 0.7.0',
    'vLLM 0.6.0 and earlier: CVE-2099-9999001',
])
def test_advisory_ranges_are_never_deployment_version(text):
    assert normalize(text).version is None


@pytest.mark.parametrize('top,nested',[('0.6','0.7'),(None,'0.7')])
def test_conflicting_nested_and_top_version_is_rejected(top,nested):
    with pytest.raises(ValueError,match='NORMALIZATION_INPUT_CONFLICT'):
        normalize('调查输入',{'component':{'name':'vllm','version':nested},'version':top})


def test_sentence_period_is_not_part_of_version():
    assert normalize('My vLLM 0.6.0. Is it affected?').version=='0.6.0'


def test_official_fix_does_not_conflict_with_declared_deployment():
    n=normalize('Installed version is 0.6.0; official fixed version vLLM 0.6.1.',
        {'component':'vllm','version':'0.6.0'})
    assert n.version=='0.6.0'


def test_declared_component_cannot_override_different_deployment_in_question():
    with pytest.raises(ValueError,match='NORMALIZATION_INPUT_CONFLICT'):
        normalize('My deployed vLLM 0.6.0 is affected?',{'component':'torch','version':'2.0'})


@pytest.mark.parametrize('range_text',['0.6.0 - 0.7.0','0.6.0–0.7.0','0.6.0 or earlier','0.6.0 and older','0.6.0..0.7.0'])
def test_advisory_forms_with_unknown_deployment_remain_unknown(range_text):
    text='CVE-2099-9999001 applies to vLLM '+range_text+'; my deployed version is unknown.'
    assert normalize(text).version is None


def test_fixed_in_is_not_deployment_and_separate_deployment_sentence_is_kept():
    assert normalize('CVE-2099-9999001 is fixed in vLLM 0.6.1; my deployed version is unknown.').version is None
    assert normalize('The affected range is below 0.7.0. My deployment is vLLM 0.6.0 for CVE-2099-9999001.').version=='0.6.0'
