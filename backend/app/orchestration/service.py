"""Opt-in upper synchronous investigation service; old public entry is untouched."""
from threading import BoundedSemaphore
from app.orchestration.contracts import (InvestigationPolicy,InvestigationResult,capture_request,valid_actor)
from app.orchestration.contracts import InvestigationStatus
from app.orchestration.control import InvestigationControl,InvestigationAbort
from app.orchestration.store import PostgresInvestigationStore
from app.orchestration.adapters import AgentServices
from app.orchestration.handoff import (select_investigation,artifact_ref,build_verification_request,
    verification_admitted,build_analysis_request,build_integration_request)
from app.orchestration.reader import InvestigationReader
from app.orchestration.answer_sources import AnswerSourcesLoader
from app.orchestration.composer import AnswerComposer
from app.orchestration.trace import build_trace


class InvestigationBusy(RuntimeError):pass
_PROCESS_SLOTS=BoundedSemaphore(2)


class InvestigationOrchestrator:
    def __init__(self,engine,model_gateway,*,policy=None):
        self.engine=engine;self.model_gateway=model_gateway;self.policy=policy or InvestigationPolicy()
        self.store=PostgresInvestigationStore(engine,policy=self.policy)
        self._slots=BoundedSemaphore(self.policy.max_active)

    def get_status(self,id,*,actor):return self.store.status(id,actor=actor)
    def get_result(self,id,*,actor):return InvestigationReader(self.store).read(id,actor=actor)
    def get_trace(self,id,*,actor):return build_trace(self.store,self.get_result(id,actor=actor),actor=actor)
    def cancel(self,id,*,actor):return self.store.request_cancel(id,actor=actor)

    def investigate(self,request,*,actor):
        valid_actor(actor);request=capture_request(request)
        local_taken=self._slots.acquire(blocking=False)
        process_taken=local_taken and _PROCESS_SLOTS.acquire(blocking=False)
        if not process_taken:
            if local_taken:self._slots.release()
            # Same-key callers should still be able to read their own running request.
            from sqlalchemy import select
            from app.db import models as m
            from app.db.session import transaction
            from app.orchestration.contracts import TYPE,NAMESPACE,request_fingerprint
            from app.assistant.storage import IdempotencyConflict
            with transaction(self.engine) as db:
                row=db.scalar(select(m.AgentRun).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==actor,
                    m.AgentRun.details[NAMESPACE]['request_key'].astext==request.request_key))
                if row is None:raise InvestigationBusy('INVESTIGATION_BUSY')
                if row.details[NAMESPACE]['request_hash']!=request_fingerprint(request):
                    raise IdempotencyConflict('Investigation key has different request content')
                id=row.id
            return self.get_result(id,actor=actor)
        control=None
        try:
            claim=self.store.claim(request,actor=actor)
            if not claim.fresh:return self.get_result(claim.logical_id,actor=actor)
            control=InvestigationControl(self.store,claim);control.start()
            control.event('PLANNING','START')
            services=AgentServices(self.engine,self.model_gateway,control)
            refs=[];optional=()
            saved,investigation,plan=services.investigate(claim.context.resolved_scope,
                claim.context.stage_keys['planner'],actor)
            control.check_start()
            if saved.planning_status!='VALIDATED' or investigation is None:
                raise InvestigationAbort('PLANNING_FAILED' if saved.planning_status=='PLANNING_FAILED' else 'PLANNING_INCOMPLETE')
            selection=select_investigation(investigation,claim.context.resolved_scope,plan)
            optional=selection.optional_tasks
            if selection.artifact:refs.append(artifact_ref(selection.artifact))
            control.event('INVESTIGATING','INVESTIGATION_READ',artifact_references=tuple(refs),unresolved_items=selection.reasons)
            if selection.admission in ('CONTINUE','VERIFY_ONLY'):
                control.check_start();control.event('VERIFYING','START')
                verification=services.verify(build_verification_request(selection,claim.context.stage_keys['verification']),actor)
                control.check_start()
                if len(verification.artifacts)==1:refs.append(artifact_ref(verification.artifacts[0]))
                control.event('VERIFYING','VERIFICATION_READ',artifact_references=tuple(refs))
                if selection.admission=='CONTINUE' and verification_admitted(verification,selection.artifact):
                    control.check_start();control.event('ANALYZING','START')
                    analysis=services.analyze(build_analysis_request(selection,verification.artifacts[0],
                        claim.context.resolved_scope,claim.context.stage_keys['analysis']),actor)
                    control.check_start()
                    if len(analysis.artifacts)==1:refs.append(artifact_ref(analysis.artifacts[0]))
                    control.event('ANALYZING','ANALYSIS_READ',artifact_references=tuple(refs))
            control.check_start();context=control.event('INTEGRATING','START')
            result=services.integrate(build_integration_request(context,refs,optional_tasks=optional),actor)
            control.check_start()
            if result.persistence!='STORED':raise InvestigationAbort('GATE_NOT_STORED')
            control.event('INTEGRATING','GATE_'+result.status,integration_result_id=result.integration_id,
                gate_logical_investigation_id=result.logical_investigation_id,gate_input_hash=result.input_hash,
                objective_hash=result.objective_hash,warnings=result.warnings,unresolved_items=result.unresolved_items)
            context=control.event('COMPOSING','ANSWER_PENDING')
            source,gate,_=AnswerSourcesLoader(self.engine).load(context,actor=actor)
            answer=AnswerComposer().compose(context,source,gate)
            for attempt in range(4):
                control.check_start();context=self.store.read(control.id,actor=actor)
                try:
                    self.store.seal(control.id,actor=actor,worker_token=control.token,expected_revision=context.revision,answer=answer)
                    break
                except ValueError as exc:
                    if str(exc) not in ('STALE_REVISION','CANCELLED','DEADLINE_EXCEEDED'):raise
                    if str(exc) in ('CANCELLED','DEADLINE_EXCEEDED'):raise InvestigationAbort(str(exc)) from None
                    if attempt==3:raise
            return self.get_result(claim.logical_id,actor=actor)
        except Exception as exc:
            if control is None:raise
            code=control.abort_code or (exc.code if isinstance(exc,InvestigationAbort) else 'ORCHESTRATION_FAILED')
            try:
                self.store.seal_stop(control.id,actor=actor,worker_token=control.token,code=code)
                return self.get_result(control.id,actor=actor)
            except Exception:
                # Commit outcome can be unknown after a connection failure.
                # Deliver the last observed snapshot, explicitly unconfirmed.
                c=control.last_context
                status=InvestigationStatus(logical_investigation_id=c.logical_investigation_id,current_stage=c.current_stage,
                    overall_status=c.overall_status,planner_run_id=c.planner_run_id,investigation_run_id=c.investigation_run_id,
                    verification_run_id=c.verification_run_id,analysis_run_id=c.analysis_run_id,
                    cancel_requested=c.cancel_requested_at is not None,recovery_required=True,warnings=c.warnings,
                    error_code=c.error_code,revision=c.revision,updated_at=c.updated_at)
                return InvestigationResult(context=c,status=status,persistence='NOT_STORED',delivery_error='ORCHESTRATION_PERSISTENCE_FAILED')
        finally:
            try:
                if control is not None:control.close()
            finally:
                _PROCESS_SLOTS.release();self._slots.release()
