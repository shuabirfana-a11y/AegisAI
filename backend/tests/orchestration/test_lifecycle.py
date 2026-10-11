from uuid import uuid4
from datetime import timedelta
import pytest
from app.utils.time import utcnow
from tests.orchestration.test_contracts_scope import request


def context():
    from app.orchestration.contracts import InvestigationContext,request_fingerprint
    from app.orchestration.scope import resolve_scope
    raw=request();now=utcnow()
    return InvestigationContext(logical_investigation_id=uuid4(),owner='alice',original_request=raw,
        request_hash=request_fingerprint(raw),resolved_scope=resolve_scope(raw,actor='alice'),
        created_at=now,updated_at=now,deadline_at=now+timedelta(seconds=300))


def test_lifecycle_orders_real_stages_and_terminal_status():
    from app.orchestration.contracts import StageEvent
    from app.orchestration.lifecycle import transition
    ctx=context()
    for stage in ('PLANNING','INVESTIGATING','VERIFYING','ANALYZING','INTEGRATING','COMPOSING'):
        ctx=transition(ctx,StageEvent(stage=stage,code='ENTER'))
    ctx=transition(ctx,StageEvent(stage='COMPLETED',code='SEALED',overall_status='SUCCEEDED'))
    assert ctx.current_stage=='COMPLETED' and ctx.overall_status=='SUCCEEDED'
    assert [e.stage for e in ctx.events]==['PLANNING','INVESTIGATING','VERIFYING','ANALYZING','INTEGRATING','COMPOSING','COMPLETED']


@pytest.mark.parametrize('terminal,status',[('CANCELLED','CANCELLED'),('FAILED','FAILED'),('WAITING_REVIEW','REVIEW_REQUIRED')])
def test_terminal_cannot_restart_or_complete(terminal,status):
    from app.orchestration.contracts import StageEvent
    from app.orchestration.lifecycle import transition
    ctx=context()
    if terminal=='WAITING_REVIEW':
        ctx=transition(ctx,StageEvent(stage='INTEGRATING',code='GATE'))
        ctx=transition(ctx,StageEvent(stage='COMPOSING',code='ANSWER'))
    ctx=transition(ctx,StageEvent(stage=terminal,overall_status=status,code='STOP'))
    for next_stage in ('PLANNING','COMPLETED'):
        with pytest.raises(ValueError,match='ILLEGAL_STAGE_TRANSITION'):
            transition(ctx,StageEvent(stage=next_stage,code='INVALID'))


def test_optional_skips_are_only_toward_gate_not_risk():
    from app.orchestration.contracts import StageEvent
    from app.orchestration.lifecycle import transition
    ctx=transition(context(),StageEvent(stage='PLANNING',code='START'))
    with pytest.raises(ValueError,match='ILLEGAL_STAGE_TRANSITION'):
        transition(ctx,StageEvent(stage='ANALYZING',code='BYPASS'))
    assert transition(ctx,StageEvent(stage='INTEGRATING',code='NO_RUNTIME')).current_stage=='INTEGRATING'
