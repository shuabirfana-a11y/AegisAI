"""Explicit internal opt-in; it does not change Planner, Assistant or HTTP routes."""
from app.agents.verification.context_store import VerificationContextStore
from app.agents.verification.runtime import VerificationRuntimeAdapter
from app.agents.verification.reader import VerificationReader


class EvidenceVerificationService:
    def __init__(self,engine,*,policy=None):
        self.contexts=VerificationContextStore(engine)
        self.runtime=VerificationRuntimeAdapter(engine,policy=policy)
        self.reader=VerificationReader(engine)

    def run(self,request,*,actor):
        context=self.contexts.capture(request,actor=actor)
        return self.runtime.run_context(context,actor=actor)

    def read_results(self,run_id,*,actor):
        return self.reader.read(run_id,actor=actor)
