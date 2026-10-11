import copy
import pytest
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import AgentFrameworkError
from tests.agents.investigation.test_end_to_end import run


@pytest.mark.parametrize('mutation',['status','implementation','receipt'])
def test_reader_rejects_inconsistent_execution_snapshot(engine,investigation_seed,mutation):
    svc,saved,_,_=run(engine,investigation_seed)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,saved.runtime_run_id);original=copy.deepcopy(row.details)
        edited=copy.deepcopy(original);ns=edited['runtime_v1']
        if mutation=='status':ns['traces']['lookup']['status']='FAILED'
        elif mutation=='implementation':ns['plan']['route']['professional_agents_v1']['bindings']['lookup']['implementation_key']='unknown-v999'
        else:ns['artifacts']['lookup']['tool_calls'][0]['sequence_no']+=999
        row.details=edited
    try:
        with pytest.raises(AgentFrameworkError,match='AGENT_TRACE_INVALID'):
            svc.read_results(saved.runtime_run_id,investigation_seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,saved.runtime_run_id).details=original
