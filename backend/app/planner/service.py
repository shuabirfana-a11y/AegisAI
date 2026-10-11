"""Explicit service entry. The existing Assistant routes do not change."""
import json
from app.runtime.contracts import TaskPlan
from app.planner.context import build_context
from app.planner.schemas import PlannerInput
from app.planner.trace import PlannerTraceStore
from app.planner.validator import validate_plan
from app.planner.schemas import PlannerPlan

class PlannerService:
    def __init__(self,engine,planner,runtime,policy):
        if runtime.policy!=policy:raise ValueError('Planner and Runtime policies must agree')
        self.engine=engine;self.planner=planner;self.runtime=runtime;self.policy=policy
        self.store=PlannerTraceStore(engine)

    def plan_and_run(self,input:PlannerInput,actor:str):
        if self.runtime.policy!=self.policy:raise ValueError('Planner and Runtime policies must agree')
        captured=PlannerInput.model_validate_json(input.model_dump_json())
        saved,fresh=self.store.create(captured,actor,self.policy,model_identity=self.planner.model_identity,
            prompt_version=self.planner.prompt_version,registry_version=self.planner.registry_version)
        context=build_context(captured,actor,self.policy,saved.planner_run_id,saved.trace_id)
        if fresh:
            outcome=self.planner.plan(captured,context)
            saved=self.store.complete(saved.planner_run_id,actor,outcome)
        elif saved.planning_status=='PLANNING':return saved
        if saved.planning_status!='VALIDATED':return saved
        tr=self.store.read(saved.planner_run_id,actor)
        # Recompile the candidate even when a validated cached snapshot exists.
        context=context.model_copy(update={'model_calls_json':json.dumps([a.model_call for a in tr.attempts])})
        validated=validate_plan(PlannerPlan.model_validate_json(tr.validated_plan.candidate_json),context)
        runtime=self.runtime.run_plan(TaskPlan.model_validate_json(validated.runtime_plan_json),actor,
                                     'planner-runtime:'+str(saved.planner_run_id))
        return self.store.link_runtime(saved.planner_run_id,actor,runtime)

    def read_trace(self,planner_id,actor):return self.store.read(planner_id,actor)
