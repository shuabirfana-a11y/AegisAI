"""The benchmark declares absence; it never fills answers or missing assets."""
import pytest


def test_contract_keeps_absent_version_explicit_and_does_not_guess():
    from evaluation.bench.question_contract import BenchmarkQuestionContract
    c=BenchmarkQuestionContract.from_input('version','原问题',{'target':'CVE-2099-90001','component':'torch'},
        {'asset_id':'owned-asset','component_id':'owned-component'})
    assert c.version is None and c.input_status=='INPUT_REQUIRED'
    assert c.missing_fields==('version',) and c.question=='原问题'


def test_overview_needs_no_deployment_version_and_complete_risk_is_ready():
    from evaluation.bench.question_contract import BenchmarkQuestionContract
    c=BenchmarkQuestionContract.from_input('facts','原问题',{'target':'CVE-2099-90001'}, {})
    assert c.input_status=='READY' and c.missing_fields==()
    c=BenchmarkQuestionContract.from_input('risk','原问题',{'target':'CVE-2099-90001','component':'torch','version':'2.0'},
        {'asset_id':'owned-asset','component_id':'owned-component'})
    assert c.version=='2.0' and c.input_status=='READY'


def test_contract_rejects_gold_and_reports_missing_owned_asset_binding():
    from evaluation.bench.question_contract import BenchmarkQuestionContract
    with pytest.raises(ValueError):
        BenchmarkQuestionContract.from_input('risk','原问题',{'expected_answer':{}},{})
    c=BenchmarkQuestionContract.from_input('risk','原问题',{'component':'torch','version':'2.0'}, {})
    assert set(c.missing_fields)=={'target','asset_id','component_id'}


@pytest.mark.parametrize('targets',[42,{'x':1},'CVE-2099-90001',0,{},False,[],None])
def test_target_container_has_controlled_validation(targets):
    from evaluation.bench.question_contract import BenchmarkQuestionContract
    if targets is None or isinstance(targets,list) and targets==[]:
        c=BenchmarkQuestionContract.from_input('facts','原问题',{'targets':targets},{})
        assert c.input_status=='INPUT_REQUIRED'
    else:
        with pytest.raises(ValueError):
            BenchmarkQuestionContract.from_input('facts','原问题',{'targets':targets},{})
