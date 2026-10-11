"""Breaks caught: context owner/role substitution and invalid Gateway permissions."""
import pytest
from app.tooling.gateway import ToolGateway,ToolContext
from tests.agents.analysis.helpers import module,request


def test_tool_uses_only_matching_owned_context(engine,analysis_source):
    src=analysis_source;ctx=module('context_store').AnalysisContextStore(engine).capture(request(src),actor=src.seed.actor)
    gateway=ToolGateway();toolctx=ToolContext(actor=src.seed.actor,database_url=engine.url.render_as_string(hide_password=False))
    try:module('registry').create_analysis_registry()
    except ModuleNotFoundError:pytest.fail('Analysis tools are not registered')
    got=gateway.invoke('analyze_risk_snapshot',{'context_id':str(ctx.context_id)},toolctx)
    assert got.status=='success' and got.data['assessment']['affected'] is True
    assert got.data['input_snapshot_hash']==ctx.input_snapshot_hash
    wrong=gateway.invoke('prioritize_remediation_snapshot',{'context_id':str(ctx.context_id)},toolctx)
    assert wrong.status=='failed'
    foreign=gateway.invoke('analyze_risk_snapshot',{'context_id':str(ctx.context_id)},ToolContext(actor='foreign',database_url=toolctx.database_url))
    assert foreign.status=='failed'


def test_extra_url_and_missing_read_permission_are_rejected():
    module('registry').create_analysis_registry()
    from uuid import uuid4
    gateway=ToolGateway()
    out=gateway.invoke('analyze_risk_snapshot',{'context_id':str(uuid4()),'url':'https://example.invalid'},ToolContext(actor='test'))
    assert out.errors[0]['code']=='INVALID_INPUT'
    out=gateway.invoke('analyze_risk_snapshot',{'context_id':str(uuid4())},ToolContext(actor='test',permissions=frozenset()))
    assert out.errors[0]['code']=='PERMISSION_DENIED'
