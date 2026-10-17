"""Bounded serial adapter over the existing single-asset HTTP service.

No new planner, security rules, executor or generative summary lives here.
"""
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from pydantic import ValidationError
from app.db.session import transaction
from app.assistant.contracts import QueryRequest
from app.planner.schemas import PlannerInput
from app.tooling.contracts import ResolutionInput
from app.orchestration.contracts import InvestigationRequest, InvestigationOptions, TERMINAL_STAGES
from app.investigation_api.schemas import ContextRequiredResponse, checked_key
from app.investigation_api.errors import ApiFailure
from app.orchestration.service import InvestigationBusy
from app.agents.analysis.reader import AnalysisReader
from app.agents.analysis.context_store import AnalysisContextStore
from app.investigation_api.projection import public_copy
from app.investigation_api.multi_asset_schemas import BatchResponse
from app.investigation_api.multi_asset_repository import BatchRepository, TERMINAL, snapshot
from app.utils.time import utcnow

logger=logging.getLogger('aegisai.multi_asset')


class MultiAssetService:
    def __init__(self,engine,single,*,max_assets=None,poll_seconds=.2,cancel_grace=5):
        limit=int(os.environ.get('AEGIS_BATCH_MAX_ASSETS','5')) if max_assets is None else max_assets
        if not isinstance(limit,int) or not 1<=limit<=20:raise ValueError('Batch asset limit must be 1..20')
        self.engine=engine;self.single=single;self.repo=BatchRepository(engine,max_assets=limit)
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='multi-asset-api')
        self.lock=Lock();self.active={};self.closed=False
        self.poll_seconds=poll_seconds;self.cancel_grace=cancel_grace

    def create(self,request,*,actor,header_key=None):
        key=checked_key(request.idempotency_key,header_key)
        with self.lock:
            if self.closed:raise ApiFailure('SERVICE_UNAVAILABLE','批量服务正在关闭。',status=503,retryable=True)
            config=self.single.gateway.config
            record,fresh=self.repo.create(request,key,actor,config.provider,config.model)
            if fresh:
                event=Event();id=record.response.batch_id;self.active[id]=(actor,event)
                try:self.pool.submit(self._run,id,actor,event)
                except Exception:
                    self.active.pop(id,None)
                    self._finish(id,actor,'FAILED','WORKER_NOT_STARTED')
                    raise
        result=self.get(record.response.batch_id,actor=actor)
        result.reused=not fresh
        return result

    def get(self,id,*,actor):
        record=self.repo.read(id,actor)
        # Validate before any reconciliation or cancellation side effects.
        for item in record.response.items:
            if item.investigation_id:self._bound_child(item,actor,record.response.vulnerability_id)
        # Reconcile only previously admitted children after restart or a slow
        # cancellation. This never starts work, re-plans or calls a model.
        if record.response.execution_status in TERMINAL:
            for index,item in enumerate(record.response.items):
                if item.execution_status=='RUNNING':
                    try:
                        if record.response.cancel_requested_at or record.response.execution_status=='TIMED_OUT':
                            self._cancel_child(item,actor)
                        self._collect(id,index,actor)
                    except Exception:
                        logger.error('Previously admitted child still requires reconciliation')
            record=self.repo.read(id,actor)
        # Bind every recorded child to this asset, target and deterministic key.
        for item in record.response.items:
            if item.investigation_id:
                child=self._bound_child(item,actor,record.response.vulnerability_id)
                context=child.context;p=context.original_request.planner_input
                if item.execution_status in ('COMPLETED','FAILED'):
                    if context.current_stage not in TERMINAL_STAGES:raise ValueError('BATCH_CHILD_NOT_TERMINAL')
                    if item.execution_status=='COMPLETED' and context.current_stage in ('FAILED','CANCELLED'):
                        raise ValueError('BATCH_CHILD_EXECUTION_INVALID')
                if item.error_code=='CHILD_RESULT_UNAVAILABLE' and (
                    item.execution_status not in ('FAILED','RUNNING') or item.impact!='UNKNOWN' or
                    item.risk_level!='UNKNOWN' or item.priority!='REVIEW_REQUIRED' or item.recommended_actions):
                    raise ValueError('BATCH_UNAVAILABLE_RESULT_INVALID')
                if (context.original_request.request_key!=item.child_request_key or
                    p.query.asset_id!=item.snapshot.asset_id or p.component_id!=item.snapshot.selected_component_id or
                    p.query.target!=record.response.vulnerability_id or
                    (item.artifact_references and item.artifact_references!=context.artifact_references) or
                    (item.integration_result_id and item.integration_result_id!=context.integration_result_id) or
                    (item.answer_id and item.answer_id!=context.answer_id)):
                    raise ValueError('BATCH_CHILD_BINDING_INVALID')
                if item.execution_status in ('COMPLETED','FAILED') and item.error_code!='CHILD_RESULT_UNAVAILABLE':
                    if hasattr(self.single,'supplements'):
                        state=self.single.status(item.investigation_id,actor=actor)
                        if item.result_version!=state.result_version or item.supplement!=state.supplement:
                            raise ValueError('BATCH_SUPPLEMENT_BINDING_INVALID')
                    version={'version':item.result_version} if hasattr(self.single,'supplements') else {}
                    artifacts=self.single.artifacts(item.investigation_id,actor=actor,**version)
                    answer=self.single.answer(item.investigation_id,actor=actor,**version) if child.answer else None
                    if item.planner_run_id!=context.planner_run_id:raise ValueError('BATCH_PLANNER_BINDING_INVALID')
                    if (item.artifact_references!=context.artifact_references or
                        item.integration_result_id!=context.integration_result_id or item.answer_id!=context.answer_id or
                        item.evaluation_time!=(artifacts.analysis.evaluation_time if artifacts.analysis else None)):
                        raise ValueError('BATCH_RESULT_REFERENCES_INVALID')
                    if artifacts.analysis and item.snapshot_valid and not self._sealed_snapshot_matches(item,child,actor):
                        raise ValueError('BATCH_ANALYSIS_SNAPSHOT_INVALID')
                    for key,value in self._decision(answer,artifacts,item.snapshot_valid).items():
                        if getattr(item,key)!=value:raise ValueError('BATCH_DECISION_BINDING_INVALID')
        response=BatchResponse.model_validate(public_copy(record.response.model_dump(mode='json')))
        # The general projection suppresses raw tool_calls. This narrow contract
        # carries only IDs, the fixed read-only tool name and execution statuses;
        # never tool arguments, output text, credentials or worker metadata.
        for public_item,stored_item in zip(response.items,record.response.items):
            public_item.supplement=stored_item.supplement
        if any(i.execution_status=='RUNNING' for i in response.items) and response.execution_status in TERMINAL:
            response.recovery_required=True
            response.warnings=(*response.warnings,'CHILD_STOP_NOT_YET_CONFIRMED')
        if response.execution_status not in TERMINAL and (utcnow()-response.updated_at).total_seconds()>90:
            response.recovery_required=True
            response.warnings=(*response.warnings,'WORKER_HEARTBEAT_STALE_NO_AUTOMATIC_REPLAY')
        return response

    def _bound_child(self,item,actor,target=None,*,version=None):
        reader=self.single.result if hasattr(self.single,'result') else self.single.reader.get_result
        selected={'version':item.result_version if version is None else version} if hasattr(self.single,'supplements') else {}
        child=reader(item.investigation_id,actor=actor,**selected)
        request=child.context.original_request;p=request.planner_input
        selected=next((c for c in item.snapshot.components if c.component_id==item.snapshot.selected_component_id),None)
        if (request.request_key!=item.child_request_key or p.query.asset_id!=item.snapshot.asset_id or
            p.component_id!=item.snapshot.selected_component_id or (target and p.query.target!=target) or
            request.investigation_options.objective_profile!='asset_risk_v1' or
            selected is None or p.component is None or p.component.version!=selected.version or
            p.component.name!=selected.name or p.component.package_name!=selected.package_name or
            p.component.ecosystem!=selected.ecosystem or p.component.purl!=selected.purl):
            raise ValueError('BATCH_CHILD_BINDING_INVALID')
        return child

    def _sealed_snapshot_matches(self,item,child,actor):
        found=AnalysisReader(self.engine).read(child.context.analysis_run_id,actor=actor)
        if len(found.artifacts)!=1:return False
        sealed=AnalysisContextStore(self.engine).read(found.artifacts[0].context_id,actor=actor).inputs.asset
        c=next(c for c in item.snapshot.components if c.component_id==item.snapshot.selected_component_id)
        return (sealed.asset_id==item.snapshot.asset_id and sealed.component_id==c.component_id and
            sealed.component==c.name and sealed.deployed_version==c.version and sealed.inventory_revision==c.inventory_revision and
            sealed.package_identifier_id==str(c.package_identifier_id) and sealed.package_name==c.package_name and
            sealed.ecosystem==c.ecosystem and sealed.namespace==c.namespace and sealed.purl==c.purl and
            sealed.environment==item.snapshot.environment and sealed.exposure==item.snapshot.exposure and
            sealed.is_demo==item.snapshot.is_demo)

    @staticmethod
    def _decision(answer,artifacts,valid):
        result=dict(impact='UNKNOWN',risk_level='UNKNOWN',priority='REVIEW_REQUIRED',recommended_actions=(),
            gate_status=answer.integration_status if answer else None,verification_status=None,
            claim_ids=(),evidence_ids=(),citations=(),evidence_observations=())
        if answer:
            result.update(claim_ids=tuple(x.claim_id for x in (*answer.verified_claims,*answer.disputed_claims)),
                evidence_ids=answer.evidence_references,citations=answer.citations,evidence_observations=answer.evidence_observations)
        risk=answer.risk_assessment if answer else None
        if risk:
            result['verification_status']=risk.verification_status
            if valid and risk.conclusion_scope=='ACCEPTED':
                result.update(impact='AFFECTED' if risk.affected is True else 'NOT_AFFECTED' if risk.affected is False else 'UNKNOWN',
                    risk_level=risk.risk_level,priority=risk.priority,
                    recommended_actions=tuple(x for x in answer.recommended_actions if x.conclusion_scope=='ACCEPTED'))
        elif artifacts.verification:result['verification_status']=artifacts.verification.verification_status
        return result

    def cancel(self,id,*,actor):
        def stop(record):
            r=record.response
            if r.execution_status in TERMINAL:return
            r.cancel_requested_at=r.cancel_requested_at or utcnow();r.execution_status='CANCEL_REQUESTED'
            for item in r.items:
                if item.execution_status=='RUNNING':self._cancel_child(item,actor)
        self.repo.mutate(id,actor,stop)
        with self.lock:
            active=self.active.get(id)
            if active:active[1].set()
        if active is None:
            # No restart replay: terminate admission and retain any known child
            # for read-only reconciliation instead of leaving a dead queue.
            record=self.repo.read(id,actor)
            if record.response.execution_status not in TERMINAL:self._finish(id,actor,'CANCELLED')
        return self.get(id,actor=actor)

    def _cancel_child(self,item,actor):
        if item.investigation_id:
            self._bound_child(item,actor)
            self.single.cancel(item.investigation_id,actor=actor)
            return
        # A timed-out creation ACK may still have a pending committed claim.
        # Reuse the single service's existing intent mechanism; do not create a
        # replacement request or assume that a missing immediate read is final.
        with self.single.lock:
            pending=self.single.pending.get((actor,item.child_request_key))
            if pending:pending.cancel_requested.set()
        existing=self.single.repository.by_key(actor,item.child_request_key)
        if existing:
            bound=item.model_copy(update={'investigation_id':existing[0].logical_investigation_id})
            self._bound_child(bound,actor)
            self.single.cancel(bound.investigation_id,actor=actor)

    def _finish(self,id,actor,state,reason=None):
        def finish(record):
            r=record.response
            r.execution_status=state;r.finished_at=utcnow()
            for item in r.items:
                if item.execution_status=='NOT_STARTED':
                    item.execution_status='NOT_EXECUTED';item.error_code=reason or state
                if item.execution_status=='RUNNING':
                    item.warnings=(*item.warnings,'CANCELLATION_REQUESTED_CHILD_MAY_STILL_BE_RUNNING')
            r.cancellation_observed=bool(r.cancel_requested_at) and not any(i.execution_status=='RUNNING' for i in r.items)
            if reason:r.warnings=tuple(dict.fromkeys((*r.warnings,reason)))
        return self.repo.mutate(id,actor,finish)

    def _matches(self,snap,actor):
        with transaction(self.engine) as db:
            return snapshot(db,snap.asset_id,actor).inventory_hash==snap.inventory_hash

    def _start(self,id,index,actor):
        def admit(record):
            r=record.response;item=r.items[index]
            if r.cancel_requested_at or utcnow()>=r.deadline_at or item.execution_status!='NOT_STARTED':return
            if not self._matches(item.snapshot,actor):
                item.execution_status='NEED_CONTEXT';item.snapshot_valid=False
                item.unresolved_items=('INVENTORY_CHANGED_NEW_BATCH_REQUIRED',);return
            if (r.deadline_at-utcnow()).total_seconds()<1:return
            # Commit the stable key/admission BEFORE a child can commit. A
            # process crash therefore leaves a reconcilable RUNNING intent.
            item.execution_status='RUNNING'
        admitted=self.repo.mutate(id,actor,admit)
        if admitted.response.items[index].execution_status!='RUNNING':return admitted
        def start(record):
            r=record.response;item=r.items[index]
            if item.execution_status!='RUNNING':return
            if r.cancel_requested_at or utcnow()>=r.deadline_at:
                item.execution_status='NOT_EXECUTED';item.error_code='CANCELLED_BEFORE_CHILD_CREATION';return
            # Before single.create is entered, failure is known not to have
            # created a child. Release admission instead of leaving an orphan
            # RUNNING intent that could block all later batches indefinitely.
            try:
                if not self._matches(item.snapshot,actor):
                    item.execution_status='NEED_CONTEXT';item.snapshot_valid=False
                    item.unresolved_items=('INVENTORY_CHANGED_NEW_BATCH_REQUIRED',);return
                c=next(c for c in item.snapshot.components if c.component_id==item.snapshot.selected_component_id)
                remaining=int((r.deadline_at-utcnow()).total_seconds())
                if remaining<1:
                    item.execution_status='NOT_EXECUTED';item.error_code='DEADLINE_BEFORE_CHILD_CREATION'
                    return
                request=InvestigationRequest(planner_input=PlannerInput(query=QueryRequest(
                    question=f'分析 {c.name} {c.version} 部署是否受 {r.vulnerability_id} 影响及风险优先级。',
                    target=r.vulnerability_id,asset_id=item.snapshot.asset_id,request_key=item.child_request_key),
                    component_id=c.component_id,component=ResolutionInput(name=c.name,package_name=c.package_name,
                        ecosystem=c.ecosystem,version=c.version,purl=c.purl)),
                    investigation_options=InvestigationOptions(objective_profile='asset_risk_v1',
                        timeout_seconds=min(record.request.child_timeout_seconds,remaining)))
            except ValidationError:
                item.execution_status='NEED_CONTEXT';item.error_code='CHILD_INPUT_INCOMPATIBLE'
                item.missing_fields=('component_input',)
                return
            except Exception:
                item.execution_status='FAILED';item.error_code='CHILD_PREPARATION_FAILED'
                return
            item.execution_status='RUNNING'
            try:
                created=self.single.create(request,actor=actor)
                if isinstance(created,ContextRequiredResponse):
                    item.execution_status='NEED_CONTEXT';item.missing_fields=created.missing_fields
                else:item.investigation_id=created.investigation_id
            except ApiFailure as exc:
                # ACK may time out after persistence; never generate another key.
                existing=self.single.repository.by_key(actor,item.child_request_key)
                if existing:item.investigation_id=existing[0].logical_investigation_id
                elif exc.code=='CREATION_ACK_TIMEOUT':
                    item.error_code=exc.code
                    item.warnings=('CHILD_CREATION_ACK_PENDING_NOT_FAILED',)
                else:item.execution_status='FAILED';item.error_code=exc.code
            except InvestigationBusy:
                item.execution_status='FAILED';item.error_code='INVESTIGATION_BUSY'
            except Exception:
                # Even a non-API exception can occur in the post-commit ACK
                # projection. Keep the durable admission and never advance on
                # uncertainty about whether the child started.
                item.error_code='CHILD_CREATION_UNCERTAIN'
                item.warnings=('CHILD_CREATION_REQUIRES_RECONCILIATION',)
        return self.repo.mutate(id,actor,start)

    def _collect(self,id,index,actor):
        record=self.repo.read(id,actor);item=record.response.items[index]
        if item.execution_status!='RUNNING':return True
        if item.investigation_id is None:
            existing=self.single.repository.by_key(actor,item.child_request_key)
            if existing is None:
                with self.single.lock:pending=self.single.pending.get((actor,item.child_request_key))
                if pending is not None:return False
                # Close the race with a claim completing between the first read
                # and pending removal; all reads remain scoped to the same key.
                existing=self.single.repository.by_key(actor,item.child_request_key)
            if existing is None:
                # Absence in this process is not proof that another process's
                # delayed claim has stopped. Retain admission until reconciled.
                return False
            def bind(record):record.response.items[index].investigation_id=existing[0].logical_investigation_id
            record=self.repo.mutate(id,actor,bind);item=record.response.items[index]
        state=self.single.status(item.investigation_id,actor=actor) if hasattr(self.single,'supplements') else None
        if state and not state.processing_complete:return False
        # A supplement may publish between two reads. Select the completed
        # status version first, then bind every result/source read to that same
        # immutable version; never combine v1 references with a v2 decision.
        version={'version':state.result_version} if state else {}
        child=self._bound_child(item,actor,record.response.vulnerability_id,**version)
        if child.context.current_stage not in TERMINAL_STAGES:return False
        artifacts=self.single.artifacts(item.investigation_id,actor=actor,**version)
        answer=self.single.answer(item.investigation_id,actor=actor,**version) if child.answer else None
        valid=self._matches(item.snapshot,actor)
        analysis=artifacts.analysis
        c=next(c for c in item.snapshot.components if c.component_id==item.snapshot.selected_component_id)
        if analysis and (analysis.asset_id!=item.snapshot.asset_id or analysis.version!=c.version or
                         analysis.inventory_revision!=c.inventory_revision):valid=False
        if analysis and not self._sealed_snapshot_matches(item,child,actor):valid=False
        def save(record):
            it=record.response.items[index]
            if it.execution_status!='RUNNING':return
            it.execution_status='FAILED' if child.context.current_stage in ('FAILED','CANCELLED') else 'COMPLETED'
            it.error_code=child.context.error_code
            it.planner_run_id=child.context.planner_run_id
            it.artifact_references=child.context.artifact_references
            it.integration_result_id=child.context.integration_result_id
            it.answer_id=child.context.answer_id
            if state:
                it.result_version=state.result_version
                it.supplement=state.supplement
            for key,value in self._decision(answer,artifacts,valid).items():setattr(it,key,value)
            it.unresolved_items=answer.unresolved_items if answer else child.context.unresolved_items
            it.warnings=answer.warnings if answer else child.context.warnings
            it.snapshot_valid=valid
            if analysis:it.evaluation_time=analysis.evaluation_time
            if not valid:
                it.unresolved_items=(*it.unresolved_items,'INVENTORY_CHANGED_SNAPSHOT_NOT_CONFIRMED')
        self.repo.mutate(id,actor,save)
        return True

    def _run(self,id,actor,wake):
        try:
            self.repo.mutate(id,actor,lambda rec:setattr(rec.response,'execution_status','RUNNING'))
            for index in range(len(self.repo.read(id,actor).response.items)):
                current=self.repo.read(id,actor).response
                if current.cancel_requested_at or utcnow()>=current.deadline_at:break
                started=self._start(id,index,actor)
                if started.response.items[index].execution_status!='RUNNING':continue
                stopping_since=None
                while not self._collect_guarded(id,index,actor):
                    current=self.repo.read(id,actor).response
                    stopping=bool(current.cancel_requested_at) or utcnow()>=current.deadline_at
                    if stopping:
                        if stopping_since is None:
                            stopping_since=time.monotonic()
                            self._cancel_child(current.items[index],actor)
                        if time.monotonic()-stopping_since>=self.cancel_grace:break
                    else:
                        # Heartbeat is a coverage record, never a fabricated Agent event.
                        self.repo.mutate(id,actor,lambda rec:None)
                    wake.wait(self.poll_seconds);wake.clear()
                current=self.repo.read(id,actor).response
                if current.cancel_requested_at or utcnow()>=current.deadline_at:break
            current=self.repo.read(id,actor).response
            state='CANCELLED' if current.cancel_requested_at else 'TIMED_OUT' if utcnow()>=current.deadline_at else 'COMPLETED'
            self._finish(id,actor,state)
        except Exception as exc:
            logger.error('Batch worker stopped; exception_type=%s',type(exc).__name__)
            try:self._finish(id,actor,'FAILED','BATCH_WORKER_FAILED')
            except Exception:logger.error('Batch outcome persistence unavailable; manual recovery required')
        finally:
            with self.lock:self.active.pop(id,None)

    def _collect_guarded(self,id,index,actor):
        try:return self._collect(id,index,actor)
        except Exception as exc:
            logger.error('Child projection failed; exception_type=%s',type(exc).__name__)
            saved=self.repo.read(id,actor);item=saved.response.items[index]
            terminal=False
            if item.investigation_id:
                try:terminal=self._bound_child(item,actor).context.current_stage in TERMINAL_STAGES
                except Exception:pass
            def fail(record):
                it=record.response.items[index]
                if it.execution_status!='RUNNING':return
                try:self._cancel_child(it,actor)
                except Exception:pass
                if terminal:it.execution_status='FAILED'
                it.error_code='CHILD_RESULT_UNAVAILABLE'
                it.impact='UNKNOWN';it.risk_level='UNKNOWN';it.priority='REVIEW_REQUIRED'
                it.recommended_actions=()
                it.unresolved_items=(*it.unresolved_items,'CHILD_RESULT_REQUIRES_REVIEW')
            self.repo.mutate(id,actor,fail)
            return terminal

    def close(self):
        with self.lock:self.closed=True;active=list(self.active.items())
        for id,(actor,event) in active:
            try:self.cancel(id,actor=actor)
            except Exception:logger.error('Batch shutdown cancellation could not be acknowledged')
        self.pool.shutdown(wait=True,cancel_futures=False)
