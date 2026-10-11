import re
from app.assistant.router import route
from app.runtime.contracts import json_bytes
from app.planner.schemas import PlannerContext, PlannerInput

def build_context(input: PlannerInput, actor, policy, planner_run_id, trace_id):
    # Revalidate mutable nested request/component instances before taking the snapshot.
    captured = PlannerInput.model_validate_json(input.model_dump_json())
    q = captured.query
    routed = route(q.question, target=q.target,
                   asset_id=str(q.asset_id) if q.asset_id else None, mode=q.mode)
    component = captured.component.model_dump(mode='json') if captured.component else None
    if component is None:
        matches = re.findall(r'\b(vllm|mlflow|pytorch|torch|langchain|transformers)\s+([0-9]+(?:\.[0-9]+){1,3}(?:[a-zA-Z0-9.+-]*))',
                             q.question, re.I)
        if len(matches)==1:
            component={'name':matches[0][0].lower(), 'version':matches[0][1]}
    targets=list(dict.fromkeys(([q.target] if q.target else []) +
                  re.findall(r'\bCVE-\d{4}-\d{4,}\b', q.question.upper())))
    scope={'targets':targets, 'asset_id':str(q.asset_id) if q.asset_id else None,
           'component_id':str(captured.component_id) if captured.component_id else None,
           'snapshot_id':str(captured.snapshot_id) if captured.snapshot_id else None,
           'component':component, 'question':q.question,
           'asset_analysis':bool(q.asset_id or captured.component_id or component or routed.get('asset'))}
    return PlannerContext(planner_run_id=planner_run_id,trace_id=trace_id,actor=actor,
        policy=policy, route_json=json_bytes(routed,65536).decode(),
        scope_json=json_bytes(scope,65536).decode())
