"""History is read-only; validate delivery against its frozen revision."""
from app.agents.contracts import fingerprint
from app.orchestration.contracts import InvestigationResult,TERMINAL_STAGES
from app.orchestration.answer_contracts import AnswerEnvelope
from app.orchestration.answer_sources import AnswerSourcesLoader
from app.orchestration.composer import AnswerComposer
from app.orchestration.store import status_snapshot


class InvestigationReader:
    def __init__(self,store):self.store=store;self.sources=AnswerSourcesLoader(store.engine)

    def read(self,id,*,actor):
        context,ns=self.store.read_audit(id,actor=actor);raw=ns['answer']
        if ns['answer_hash']!=fingerprint(raw):raise ValueError('ANSWER_HASH_INVALID')
        answer=AnswerEnvelope.model_validate(raw) if raw is not None else None
        if answer:
            if context.error_code and answer.integration_status is None:
                if context.integration_result_id:self.sources.load(context,actor=actor)
                expected=AnswerComposer().failure(context,code=context.error_code,cancelled=context.overall_status=='CANCELLED')
            else:
                source,gate,_=self.sources.load(context,actor=actor)
                expected=AnswerComposer().compose(context,source,gate)
            if expected!=answer or context.answer_id!=answer.answer_id:raise ValueError('ANSWER_CONTENT_BINDING_INVALID')
            state={'COMPLETE':'SUCCEEDED','COMPLETE_WITH_WARNINGS':'SUCCEEDED_WITH_WARNINGS','INCOMPLETE':'INCOMPLETE',
                'REVIEW_REQUIRED':'REVIEW_REQUIRED','FAILED':'FAILED','CANCELLED':'CANCELLED'}[answer.answer_status]
            if context.overall_status!=state or context.current_stage not in TERMINAL_STAGES:raise ValueError('ANSWER_STATE_BINDING_INVALID')
        elif context.answer_id is not None or context.current_stage in TERMINAL_STAGES:
            raise ValueError('TERMINAL_ANSWER_MISSING')
        return InvestigationResult(context=context,status=status_snapshot(context,ns),answer=answer)
