import pytest
from app.integration.contracts import OptionalTask
from app.integration.service import IntegrationService
from tests.integration.conftest import build_chain
from tests.integration.helpers import request

@pytest.mark.parametrize('mode,status',[('unknown','REPLAN_REQUIRED'),('overview','PASS_WITH_WARNINGS'),
    ('optional_failure','PASS_WITH_WARNINGS'),('required_partial','REPLAN_REQUIRED'),('conflict','HUMAN_REVIEW_REQUIRED'),('blocked','REPLAN_REQUIRED')])
def test_actual_service_chain_with_bounded_outcomes(engine,mode,status):
    chain=build_chain(engine,mode);kw={}
    if mode=='overview':kw['objective_profile']='overview_v1'
    if mode=='optional_failure':kw['optional_tasks']=(OptionalTask(run_id=chain.investigation.run_id,task_id='extra_source'),)
    svc=IntegrationService(engine);got=svc.evaluate(request(chain,**kw),actor=chain.seed.actor)
    assert got.status==status,got.blocking_issues
    assert len(set(got.source_run_ids))==3 and got.persistence=='STORED'
    assert svc.read(got.integration_id,actor=chain.seed.actor)==got
    if mode=='overview':
        assert chain.analysis.risk_level=='UNKNOWN' and chain.analysis.priority=='REVIEW_REQUIRED'
        assert 'OVERVIEW_BOUNDED_ABSTENTION' in got.warnings
    if mode.endswith('failure') or mode=='required_partial':
        from app.agents.investigation.reader import InvestigationReader
        art=next(a for a in InvestigationReader(engine).read(chain.investigation.run_id,chain.seed.actor).artifacts if a.task_id=='extra_source')
        assert art.runtime_status!='SUCCESS'
    if mode=='blocked':
        from app.agents.investigation.reader import InvestigationReader
        got_run=InvestigationReader(engine).read(chain.investigation.run_id,chain.seed.actor)
        assert 'blocked_child' in got_run.blocked_tasks and any(t.task_id=='blocked_child' and not t.attempted for t in got_run.traces)
