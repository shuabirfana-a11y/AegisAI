from uuid import uuid4
import pytest
from tests.agents.fixtures import task, context, outcome


def binding(item):
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    return AgentRouter(create_default_registry().freeze()).route(item,'vulnerability_lookup')


def test_agent_artifact_round_trip_preserves_provenance():
    from app.agents.artifacts import AgentArtifact
    from app.runtime.contracts import TaskArtifact
    item=task();source=outcome(item).artifact
    wrapped=AgentArtifact.from_task_artifact(source,binding(item))
    assert wrapped.to_task_artifact()==source
    assert wrapped.artifact_id==source.artifact_id and wrapped.evidence==source.evidence
    assert wrapped.confidence is None and wrapped.unresolved_items==tuple(source.unresolved_questions)
    with pytest.raises(ValueError):TaskArtifact.model_validate_json(wrapped.model_dump_json())


@pytest.mark.parametrize('mutation',['run','task','extra','missing','review','duplicate'])
def test_handoff_accepts_only_same_run_successful_dependencies(mutation):
    from app.agents.artifacts import build_handoff
    from app.agents.contracts import AgentFrameworkError
    ctx=context();first=task('first');second=task('second',deps=['first'])
    source=outcome(first,ctx).artifact;deps={'first':source};bindings={'first':binding(first)}
    if mutation=='run':deps['first']=source.model_copy(update={'run_id':uuid4()})
    if mutation=='task':deps['first']=source.model_copy(update={'task_id':'other'})
    if mutation=='extra':deps['extra']=source
    if mutation=='missing':deps={}
    if mutation=='review':deps['first']=source.model_copy(update={'status':'WAITING_REVIEW'})
    if mutation=='duplicate':
        second=task('second',deps=['first','other'])
        deps['other']=source.model_copy(update={'task_id':'other'})
        bindings['other']=binding(task('other'))
    with pytest.raises(AgentFrameworkError,match='AGENT_HANDOFF_INVALID'):
        build_handoff(second,ctx,deps,bindings)


def test_handoff_a_to_b_is_typed_and_preserves_dependency_ids():
    from app.agents.artifacts import build_handoff, AgentExecutionRequest
    ctx=context();first=task('first');second=task('second',deps=['first'])
    source=outcome(first,ctx).artifact
    inputs=build_handoff(second,ctx,{'first':source},{'first':binding(first)})
    request=AgentExecutionRequest(task=second,context=ctx,input_artifacts=inputs)
    assert request.input_artifacts[0].result==source.result
    assert request.input_artifacts[0].to_task_artifact()==source


@pytest.mark.parametrize('mutation',['nan','extra_field','oversize_extension'])
def test_handoff_revalidates_mutated_nested_data_and_size(mutation):
    from app.agents.artifacts import AgentArtifact
    from app.agents.contracts import AgentFrameworkError
    item=task();source=outcome(item).artifact
    if mutation=='nan':source.result['spoof']=float('nan')
    if mutation=='extra_field':source=source.model_copy(update={'surprise':'forged'})
    if mutation=='oversize_extension':
        source=source.model_copy(update={'result':{'blob':'x'*200000},'unresolved_questions':['y'*200000]})
    with pytest.raises(AgentFrameworkError,match='AGENT_ARTIFACT_INVALID'):
        AgentArtifact.from_task_artifact(source,binding(item))
