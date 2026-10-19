"""Explicit investigation entry. Existing public Assistant/Planner flows are unchanged."""
import json
from contextlib import nullcontext
from app.planner.schemas import PlannerInput
from app.planner.context import build_context
from app.planner.trace import PlannerTraceStore
from app.runtime.contracts import RuntimePolicy,TaskPlan
from app.agents.investigation.planner import InvestigationPlannerAdapter
from app.agents.investigation.planning import InvestigationPlan
from app.agents.investigation.validation import validate_investigation_plan
from app.agents.investigation.agent import IntelligenceInvestigationAgent
from app.agents.investigation.registry import create_investigation_registry
from app.agents.investigation.runtime import InvestigationRuntimeAdapter
from app.agents.investigation.reader import InvestigationReader

class IntelligenceInvestigationService:
    def __init__(self,engine,model_gateway,*,policy=None,observer=None):
        self.engine=engine;self.policy=policy or RuntimePolicy()
        self.observer=observer
        self.store=PlannerTraceStore(engine)
        self.planner=InvestigationPlannerAdapter(model_gateway,self.store)
        self.runtime=InvestigationRuntimeAdapter(engine,registry=create_investigation_registry(IntelligenceInvestigationAgent()),
            policy=self.policy,model_gateway=model_gateway)
    def plan_and_run(self,input,actor):
        captured=PlannerInput.model_validate_json(input.model_dump_json())
        with self.observer.creation_guard() if self.observer is not None else nullcontext():
            if self.observer is not None:self.observer.before_planning()
            saved,fresh=self.store.create(captured,actor,self.policy,model_identity=self.planner.model_identity,
                prompt_version=self.planner.prompt_version,registry_version=self.planner.registry_version)
            if self.observer is not None:self.observer.planner_created(saved)
        context=build_context(captured,actor,self.policy,saved.planner_run_id,saved.trace_id)
        if captured.candidate_reference:
            context=context.model_copy(update={'scope_json':json.dumps({**context.scope,
                'candidate_reference':captured.candidate_reference},sort_keys=True)})
        if fresh:saved=self.store.complete(saved.planner_run_id,actor,self.planner.plan(captured,context))
        elif saved.planning_status=='PLANNING':return saved
        if self.observer is not None:self.observer.planner_completed(saved)
        if saved.planning_status!='VALIDATED':return saved
        audit=self.store.read(saved.planner_run_id,actor)
        context=context.model_copy(update={'model_calls_json':json.dumps([a.model_call for a in audit.attempts])})
        validated=validate_investigation_plan(InvestigationPlan.model_validate_json(audit.validated_plan.candidate_json),context)
        if self.observer is not None:self.observer.before_runtime()
        runtime=self.runtime.run_plan(TaskPlan.model_validate_json(validated.runtime_plan_json),actor,'planner-runtime:'+str(saved.planner_run_id))
        return self.store.link_runtime(saved.planner_run_id,actor,runtime)
    def read_results(self,run_id,actor):return InvestigationReader(self.engine).read(run_id,actor)
    def read_planner_trace(self,planner_id,actor):return self.store.read(planner_id,actor)
