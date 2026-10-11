"""Internal opt-in analysis entry; does not change Planner or public endpoints."""
from app.agents.analysis.context_store import AnalysisContextStore
from app.agents.analysis.runtime import AnalysisRuntimeAdapter


class SecurityAnalysisService:
    def __init__(self,engine,*,policy=None):
        self.contexts=AnalysisContextStore(engine)
        self.runtime=AnalysisRuntimeAdapter(engine,policy=policy)

    def run(self,request,*,actor):
        context=self.contexts.capture(request,actor=actor)
        return self.runtime.run_context(context,actor=actor)

    def read_results(self,run_id,*,actor):
        from app.agents.analysis.reader import AnalysisReader
        return AnalysisReader(self.contexts.engine).read(run_id,actor=actor)
