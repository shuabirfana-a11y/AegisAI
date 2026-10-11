from tests.integration.helpers import request

def test_trace_reference_redacts_credentials_and_tokens(engine,gate_chain):
    from app.integration.snapshot import IntegrationSnapshotReader
    from app.integration.evaluator import IntegrationGateEvaluator
    from app.integration.trace import build_integration_trace
    c=gate_chain;ctx=IntegrationSnapshotReader(engine).capture(request(c),actor=c.seed.actor)
    first=ctx.verification.supporting_evidence[0]
    changed=first.model_copy(update={'reference':{'url':' HTTPS://user:PRIVATE_PASS@example.invalid/advisory?token=PRIVATE_TOKEN ',
        'locator':{'authorization':'PRIVATE_AUTH','X-API-Key':'PRIVATE_KEY','client_secret':'PRIVATE_SECRET','line':1}},
        'lineage_key':'PRIVATE_LINEAGE:user:PRIVATE_PASS'})
    v=ctx.verification.model_copy(update={'supporting_evidence':(changed,*ctx.verification.supporting_evidence[1:])})
    captured=ctx.model_copy(update={'verification':v})
    result=IntegrationGateEvaluator().evaluate(captured)
    trace=build_integration_trace(captured,result,1)
    for text in (result.model_dump_json(),trace.model_dump_json()):
        assert all(s not in text for s in ('PRIVATE_PASS','PRIVATE_TOKEN','PRIVATE_AUTH','PRIVATE_KEY','PRIVATE_SECRET','PRIVATE_LINEAGE'))
    assert result.evidence_references[0]['reference']['url']=='https://example.invalid/advisory'
    assert result.evidence_references[0]['reference']['locator']['line']==1
    assert captured.verification.supporting_evidence[0]==changed
