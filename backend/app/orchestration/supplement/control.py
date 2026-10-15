"""Borrow original deadlines/cancellation monitor; never reset the logical clock."""
from app.orchestration.control import InvestigationControl,InvestigationAbort
from app.orchestration.contracts import ClaimReceipt
from app.orchestration.lifecycle import transition
from app.orchestration.supplement.contracts import TERMINAL


class ControlStore:
    def __init__(self,store):self.store=store;self.engine=store.engine;self.policy=store.policy
    def read(self,id,*,actor):
        r=self.store.read(id,actor)
        if r.summary.cancel_requested:
            return r.context.model_copy(update={'cancel_requested_at':r.summary.started_at})
        return r.context
    def creation_guard(self,id,*,actor):return self.store.creation_guard(id,actor)
    def advance(self,id,*,actor,worker_token,expected_revision,event,**updates):
        def advance(r):
            if r.context.revision!=expected_revision:raise ValueError('STALE_REVISION')
            if r.summary.cancel_requested:raise ValueError('CANCELLED')
            if r.summary.status in TERMINAL:raise ValueError('ALREADY_TERMINAL')
            r.context=transition(r.context,event)
            r.context=type(r.context).model_validate({**r.context.model_dump(mode='python'),**updates})
            if event.stage in ('VERIFYING','ANALYZING','INTEGRATING'):
                r.summary=r.summary.model_copy(update={'status':event.stage})
        return self.store.mutate(id,actor,worker_token,advance).context
    def heartbeat(self,id,*,actor,worker_token):
        self.store.guard(id,actor,worker_token)
        self.store.mutate(id,actor,worker_token,lambda r:None)


class SupplementControl(InvestigationControl):
    def __init__(self,store,record):
        super().__init__(ControlStore(store),ClaimReceipt(logical_id=record.spec.parent_investigation_id,
            fresh=True,context=record.context,worker_token=record.worker_token))
        self.supplement_store=store
    def check_start(self):
        try:self.supplement_store.guard(self.id,self.actor,self.token)
        except ValueError as exc:
            code=str(exc);self._abort(code);raise InvestigationAbort(code) from None
        super().check_start()
    def reserve_stage(self,calls):
        try:self.supplement_store.guard(self.id,self.actor,self.token,required_calls=calls)
        except ValueError as exc:raise InvestigationAbort(str(exc)) from None


class AcquisitionControl:
    """Same cooperative control, but the extra Run never replaces the original Run."""
    def __init__(self,parent):self.parent=parent
    def __getattr__(self,name):return getattr(self.parent,name)
    def run_started(self,saved):
        def update(r):r.summary=r.summary.model_copy(update={'acquisition_run_id':saved.run_id})
        self.parent.supplement_store.mutate(self.parent.id,self.parent.actor,self.parent.token,update)
    def run_finished(self,saved):pass
