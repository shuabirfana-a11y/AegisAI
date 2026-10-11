"""Only upper stage transitions; never modifies Runtime task state."""
from app.orchestration.contracts import InvestigationContext, StageEvent, TERMINAL_STAGES

NEXT={
    'CREATED':{'PLANNING','INTEGRATING','FAILED','CANCELLED'},
    'PLANNING':{'INVESTIGATING','INTEGRATING','FAILED','CANCELLED'},
    'INVESTIGATING':{'VERIFYING','INTEGRATING','FAILED','CANCELLED'},
    'VERIFYING':{'ANALYZING','INTEGRATING','FAILED','CANCELLED'},
    'ANALYZING':{'INTEGRATING','FAILED','CANCELLED'},
    'INTEGRATING':{'COMPOSING','FAILED','CANCELLED'},
    'COMPOSING':{'COMPLETED','WAITING_REVIEW','FAILED','CANCELLED'},
}


def transition(context: InvestigationContext,event: StageEvent) -> InvestigationContext:
    context=InvestigationContext.model_validate_json(context.model_dump_json())
    event=StageEvent.model_validate_json(event.model_dump_json())
    old=context.current_stage
    if old in TERMINAL_STAGES or (event.stage!=old and event.stage not in NEXT[old]):
        raise ValueError('ILLEGAL_STAGE_TRANSITION')
    status=event.overall_status or context.overall_status
    if event.stage in TERMINAL_STAGES:
        expected={'COMPLETED':{'SUCCEEDED','SUCCEEDED_WITH_WARNINGS','INCOMPLETE'},
                  'WAITING_REVIEW':{'REVIEW_REQUIRED'},'FAILED':{'FAILED'},'CANCELLED':{'CANCELLED'}}
        if status not in expected[event.stage]:raise ValueError('TERMINAL_STATUS_REQUIRED')
    elif status!='RUNNING':raise ValueError('NONTERMINAL_STATUS_INVALID')
    value=context.model_dump(mode='json')
    value.update(current_stage=event.stage,overall_status=status,updated_at=event.at,
                 events=[*[e.model_dump(mode='json') for e in context.events],event.model_dump(mode='json')],
                 revision=context.revision+1)
    if event.stage in TERMINAL_STAGES:value['finished_at']=event.at
    return InvestigationContext.model_validate(value)
