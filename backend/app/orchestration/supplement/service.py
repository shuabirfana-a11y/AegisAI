"""One targeted read, then original deterministic verification/risk/Gate services."""
from uuid import uuid5,NAMESPACE_URL
from app.orchestration.supplement.contracts import SupplementView,SupplementSummary,SupplementToolCall
from app.orchestration.supplement.policy import decide
from app.orchestration.supplement.store import SupplementStore,runs,tool_count
from app.orchestration.supplement.control import SupplementControl,AcquisitionControl
from app.orchestration.supplement.runtime import SupplementRuntime
from app.orchestration.control import InvestigationAbort
from app.orchestration.adapters import AgentServices
from app.orchestration.handoff import (artifact_ref,ArtifactSelection,build_verification_request,
    build_analysis_request,build_integration_request)
from app.agents.investigation.reader import InvestigationReader
from app.agents.asset_observations import InvestigationArtifactReference
from app.orchestration.answer_sources import AnswerSourcesLoader
from app.orchestration.composer import AnswerComposer
from app.agents.contracts import fingerprint
from app.db.session import transaction
from app.db import models as m
from sqlalchemy import select

def novel_evidence(evidence,prior,claim_ids):
    def identity(e):return fingerprint([e.claim_id,e.hash,e.observed_value,e.stance])
    seen={identity(e) for e in prior};old_ids={e.evidence_id for e in prior};new=[]
    for e in evidence:
        key=identity(e)
        if e.claim_id in claim_ids and e.evidence_id not in old_ids and key not in seen and e.integrity_status=='VALID':
            new.append(e.evidence_id);seen.add(key)
    return tuple(new)

class EvidenceSupplementService:
    def __init__(self,engine,gateway,*,enabled=False):
        self.engine=engine;self.gateway=gateway;self.enabled=enabled;self.store=SupplementStore(engine)
    def read(self,parent,*,actor):
        record=self.store.read(parent,actor)
        if record is None:return None
        return SupplementView(summary=record.summary,result=record.result or record.original)
    def summary(self,parent,*,actor):
        view=self.read(parent,actor=actor)
        return view.summary if view else self.store.read_decision(parent,actor)
    def maybe_run(self,original,*,actor):
        parent=original.context.logical_investigation_id
        def stopped(reason,status='NOT_ELIGIBLE'):
            summary=SupplementSummary(parent_investigation_id=parent,
                parent_integration_id=original.context.integration_result_id,status=status,reason=reason,
                error_code=reason if status=='FAILED' else None)
            if self.enabled:self.store.save_decision(summary,actor)
            return SupplementView(summary=summary,result=original)
        if not self.enabled:return stopped('SERVER_POLICY_DISABLED','DISABLED')
        old=self.read(parent,actor=actor)
        if old:return old  # interrupted work is not replayed
        try:spec,reason=decide(self.engine,original,actor)
        except ValueError as exc:
            if str(exc) not in ('NEED_CONTEXT','INVENTORY_CHANGED','CANCELLED','BATCH_SCOPE_INVALID'):
                stopped('SUPPLEMENT_ADMISSION_FAILED','FAILED')
                raise
            return stopped(str(exc))
        if spec is None:return stopped(reason)
        from app.orchestration.service import _PROCESS_SLOTS
        if not _PROCESS_SLOTS.acquire(blocking=False):return stopped('PROCESS_CAPACITY_EXHAUSTED')
        try:return self._execute(original,spec,actor,stopped)
        finally:_PROCESS_SLOTS.release()

    def _execute(self,original,spec,actor,stopped):
        parent=original.context.logical_investigation_id
        try:record,fresh=self.store.claim(original,spec,actor)
        except ValueError as exc:
            code=str(exc)
            if code not in ('BATCH_SUPPLEMENT_BUDGET_EXHAUSTED','TOTAL_TOOL_BUDGET_EXHAUSTED',
                'DEADLINE_EXCEEDED','CANCELLED','INVENTORY_CHANGED'):
                stopped('SUPPLEMENT_CLAIM_FAILED','FAILED')
                raise
            return stopped(code)
        if not fresh:return self.read(parent,actor=actor)
        control=SupplementControl(self.store,record);control.start()
        try:
            control.reserve_stage(len(spec.claim_ids)+2)
            runtime=SupplementRuntime(self.engine,record);runtime.bind_execution_control(AcquisitionControl(control))
            saved=runtime.run_fixed(actor)
            acquired=InvestigationReader(self.engine).read(saved.run_id,actor)
            with transaction(self.engine) as db:
                records=list(db.scalars(select(m.ToolCallRecord).where(m.ToolCallRecord.agent_run_id==saved.run_id).order_by(m.ToolCallRecord.sequence_no)))
                count=len(records)
                calls=tuple(SupplementToolCall(record_id=c.id,tool=c.tool_name,status=c.status,
                    evidence_ids=tuple(e['evidence_id'] for e in c.output_summary.get('evidence_refs',[]) if e.get('evidence_id'))) for c in records)
                errors={e.get('code') for c in records for e in c.output_summary.get('errors',[])}
            def save_calls(r):r.summary=r.summary.model_copy(update={'extra_acquisition_calls':count,'extra_total_tool_calls':count,'tool_calls':calls})
            self.store.mutate(parent,actor,control.token,save_calls)
            control.check_start()
            if 'PERMISSION_DENIED' in errors:
                raise InvestigationAbort('ACCESS_DENIED')
            if errors & {'UNKNOWN_TOOL','INVALID_INPUT','INVALID_STATE','OUTPUT_LIMIT'}:
                raise InvestigationAbort('SUPPLEMENT_FAILED')
            if len(acquired.artifacts)!=1 or acquired.artifacts[0].runtime_status!='SUCCESS' or acquired.artifacts[0].partial_result:
                raise InvestigationAbort('SOURCE_LOOKUP_INCOMPLETE')
            source,_,_=AnswerSourcesLoader(self.engine).load(original.context,actor=actor)
            ref=artifact_ref(acquired.artifacts[0])
            def bind(r):r.summary=r.summary.model_copy(update={'acquisition_artifact':ref})
            self.store.mutate(parent,actor,control.token,bind)
            inv=source.investigation
            selection=ArtifactSelection(artifact=inv,admission='CONTINUE',
                supporting_artifacts=tuple(InvestigationArtifactReference(run_id=r.run_id,task_id=r.task_id,artifact_id=r.artifact_id) for r in spec.supporting_artifacts),
                asset_id=original.context.resolved_scope.planner_input.query.asset_id,
                component_id=original.context.resolved_scope.planner_input.component_id)
            request=build_verification_request(selection,record.context.stage_keys['verification']).model_copy(update={'supplement_id':record.summary.supplement_id})
            # Capture raw provenance through the normal Reader first, then refuse
            # unchanged material before creating any new verification execution.
            from app.agents.verification.snapshot import InvestigationSnapshotReader
            snapshot=InvestigationSnapshotReader(self.engine).read(request,actor=actor)
            new=novel_evidence(snapshot.evidence,source.verification_source.evidence,spec.claim_ids)
            if not new:raise InvestigationAbort('NO_NEW_USABLE_EVIDENCE')
            def found(r):r.summary=r.summary.model_copy(update={'new_evidence_ids':new})
            self.store.mutate(parent,actor,control.token,found)
            services=AgentServices(self.engine,self.gateway,control)
            control.reserve_stage(2);control.event('VERIFYING','SUPPLEMENT_REVERIFY')
            ver=services.verify(request,actor);control.check_start()
            if len(ver.artifacts)!=1:raise InvestigationAbort('VERIFICATION_ARTIFACT_MISSING')
            refs=(spec.source_artifact,artifact_ref(ver.artifacts[0]))
            control.event('VERIFYING','VERIFICATION_READ',artifact_references=refs)
            # Conflicts are never adjudicated by this round. Persist the same
            # Gate's human-review result, with no additional risk operation.
            if not ver.artifacts[0].conflicts and not ver.artifacts[0].partial_result:
                control.reserve_stage(1);control.event('ANALYZING','SUPPLEMENT_REANALYZE')
                risk=services.analyze(build_analysis_request(selection,ver.artifacts[0],record.context.resolved_scope,record.context.stage_keys['analysis']),actor)
                control.check_start()
                if len(risk.artifacts)==1:refs=(*refs,artifact_ref(risk.artifacts[0]))
                control.event('ANALYZING','ANALYSIS_READ',artifact_references=refs)
            context=control.event('INTEGRATING','SUPPLEMENT_GATE')
            gate=services.integrate(build_integration_request(context,refs),actor);control.check_start()
            if gate.persistence!='STORED':raise InvestigationAbort('GATE_NOT_STORED')
            context=control.event('INTEGRATING','GATE_'+gate.status,integration_result_id=gate.integration_id,
                gate_logical_investigation_id=gate.logical_investigation_id,gate_input_hash=gate.input_hash,
                objective_hash=gate.objective_hash,warnings=gate.warnings,unresolved_items=gate.unresolved_items)
            context=control.event('COMPOSING','SUPPLEMENT_ANSWER_PENDING')
            source,gate,_=AnswerSourcesLoader(self.engine).load(context,actor=actor)
            answer=AnswerComposer().compose(context,source,gate,answer_id=uuid5(NAMESPACE_URL,str(record.summary.supplement_id)+':answer-v2'))
            with transaction(self.engine) as db:
                total=tool_count(db,set(runs(context))-set(runs(original.context)))
            self.store.mutate(parent,actor,control.token,lambda r:setattr(r,'summary',r.summary.model_copy(update={'extra_total_tool_calls':count+total})))
            self.store.publish(parent,actor,control.token,answer)
        except Exception as exc:
            code=control.abort_code or (exc.code if isinstance(exc,InvestigationAbort) else 'SUPPLEMENT_FAILED')
            # Count real persisted failed/timeout calls as well, without rerunning.
            record=self.store.read(parent,actor)
            with transaction(self.engine) as db:
                acquired_count=tool_count(db,{record.summary.acquisition_run_id} if record.summary.acquisition_run_id else set())
                stage_count=tool_count(db,set(runs(record.context))-set(runs(original.context)))
            self.store.mutate(parent,actor,control.token,lambda r:setattr(r,'summary',r.summary.model_copy(
                update={'extra_acquisition_calls':acquired_count,'extra_total_tool_calls':acquired_count+stage_count})))
            self.store.stop(parent,actor,control.token,code)
        finally:control.close()
        return self.read(parent,actor=actor)
