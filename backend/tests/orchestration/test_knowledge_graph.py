"""Existing Agent chain -> immutable graph projection, synthetic dedicated DB."""
from uuid import uuid4
import pytest
from app.db.session import transaction
from app.knowledge.investigation_graph import load_linked_investigation
from app.knowledge.security_graph import build_security_graph


def test_saved_agent_artifacts_bind_a_complete_risk_graph(completed_chain,engine):
    seed,request,service,result,calls=completed_chain
    before=len(calls)
    linked=load_linked_investigation(engine,result.context.logical_investigation_id,seed.actor)
    with transaction(engine) as db:
        graph=build_security_graph(db,seed.cve,seed.actor,linked=linked)
    assert graph.gate_status==result.answer.integration_status
    assert graph.answer_id==str(result.answer.answer_id)
    assert {'VULNERABILITY','COMPONENT','VERSION','ASSET','EVIDENCE','RISK'} <= {n.type for n in graph.nodes}
    risk=next(n for n in graph.nodes if n.type=='RISK')
    assert risk.data['historical_snapshot'] is True
    assert risk.data['level']==result.answer.risk_assessment.risk_level
    assert len(graph.agent_references)==3 and len(calls)==before
    assert any(e.type=='HAS_RISK' for e in graph.edges)
    assert any(e.type=='SUPPORTED_BY' for e in graph.edges)


def test_saved_graph_honors_root_owner_and_target(completed_chain,engine):
    seed,_,_,result,_=completed_chain
    with pytest.raises(LookupError):load_linked_investigation(engine,result.context.logical_investigation_id,'another-owner')
    with pytest.raises(LookupError):load_linked_investigation(engine,uuid4(),seed.actor)
    linked=load_linked_investigation(engine,result.context.logical_investigation_id,seed.actor)
    linked['canonical_id']='CVE-2099-0000001'
    with transaction(engine) as db:
        with pytest.raises(ValueError,match='TARGET'):build_security_graph(db,seed.cve,seed.actor,linked=linked)


def test_risk_support_uses_only_factors_that_influenced_the_saved_decision(completed_chain,engine):
    from app.orchestration.answer_sources import AnswerSourcesLoader
    seed,_,_,result,_=completed_chain
    source,_,_=AnswerSourcesLoader(engine).load(result.context,actor=seed.actor)
    expected={e for f in (*source.analysis.risk_factors,*source.analysis.mitigating_factors)
        if f.influences_decision and not f.rejected_reason for e in f.evidence_ids}
    linked=load_linked_investigation(engine,result.context.logical_investigation_id,seed.actor)
    assert set(linked['evidence_ids'])==expected


def test_gate_block_and_changed_inventory_do_not_become_current_high_risk(completed_chain,engine):
    seed,_,_,result,_=completed_chain
    linked=load_linked_investigation(engine,result.context.logical_investigation_id,seed.actor)
    linked['gate_status']='REPLAN_REQUIRED'
    with transaction(engine) as db:
        graph=build_security_graph(db,seed.cve,seed.actor,linked=linked)
    risk=next(n for n in graph.nodes if n.type=='RISK')
    assert risk.data['level']=='UNKNOWN' and risk.data['affected'] is None
    linked=load_linked_investigation(engine,result.context.logical_investigation_id,seed.actor)
    linked['inventory_revision']=(linked.get('inventory_revision') or 1)+1
    with transaction(engine) as db:
        graph=build_security_graph(db,seed.cve,seed.actor,linked=linked)
    risk=next(n for n in graph.nodes if n.type=='RISK')
    assert risk.data['level']=='UNKNOWN' and risk.data['is_stale'] is True
