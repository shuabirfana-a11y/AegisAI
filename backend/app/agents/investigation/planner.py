"""TaskPlanner adapter; original Planner source and default behavior stay intact."""
import json
from pathlib import Path
from app.planner.llm_planner import LLMTaskPlanner,_REPAIRABLE,_TRANSIENT,issue
from app.planner.schemas import PlannerAttempt,PlanningOutcome
from app.planner.validator import PlanValidationError,missing_fields
from app.llm.schemas import StructuredRequest,Message,CallRecord
from app.tooling.contracts import REGISTRY
from app.agents.investigation.planning import InvestigationPlan,scoped_plan_model
from app.agents.investigation.validation import validate_investigation_plan
from app.agents.investigation.roles import ROLES,PROMPT_VERSION,REGISTRY_VERSION
from app.agents.investigation.normalization import normalize_question
from app.agents.investigation.templates import template_guidance

class InvestigationPlannerAdapter(LLMTaskPlanner):
    def __init__(self,gateway,trace_sink):
        super().__init__(gateway,trace_sink)
        self._investigation_prompt=Path(__file__).with_name('investigation_plan_v6.txt').read_text(encoding='utf-8')
    @property
    def prompt_version(self):return PROMPT_VERSION
    @property
    def registry_version(self):return REGISTRY_VERSION
    def plan(self,input,context):
        missing=missing_fields(context.scope,context.policy)
        role_fields={'vulnerability_lookup':{'target','version'},'evidence_search':{'target'},'asset_lookup':{'asset_id'}}
        scope=context.scope
        normalized=normalize_question(scope['question'],{'targets':scope['targets'],'component':scope.get('component')},
            {k:scope[k] for k in ('asset_id','component_id','snapshot_id') if scope.get(k)},extract_literals=False)
        targets=[{'target':t} for t in scope['targets']]
        component={k:v for k,v in (scope.get('component') or {}).items() if v is not None}
        exact={n:targets for n in ('get_vulnerability','get_evidence','get_claims','relation_query')}
        if scope.get('candidate_reference'):
            exact['get_evidence']=[{**t,'candidate_reference':scope['candidate_reference']} for t in targets]
            exact['get_vulnerability']=[{**t,'candidate_reference':scope['candidate_reference']} for t in targets]
        exact['inspect_component_version']=[{**t,**component} for t in targets] if component.get('version') else []
        exact['semantic_search']={'query':scope['question']}
        exact['get_asset']={'asset_id':scope['asset_id']} if scope.get('asset_id') else None
        payload={'input_scope':context.scope,'normalized_goal':normalized.model_dump(mode='json'),
            'task_template':template_guidance(normalized),'permissions':sorted(context.policy.permissions),
            'runtime_policy':context.policy.model_dump(mode='json'),
            'roles':{k:{'allowed_tools':sorted(r.tools),'minimum_criteria':sorted(r.criteria)} for k,r in ROLES.items()},
            'tool_inputs':{n:REGISTRY[n].input.model_json_schema() for n in sorted(set().union(*(r.tools for r in ROLES.values())))},
            'missing_fields':sorted(missing&{'target','asset_id','version'}),
            'missing_fields_by_role':{k:sorted(missing&fields) for k,fields in role_fields.items()},
            'exact_tool_arguments':exact}
        attempts=[];issues=();output_model=scoped_plan_model(context)
        for index in (1,2):
            messages=[Message(role='system',content=self._investigation_prompt),
                      Message(role='user',content=json.dumps(payload,ensure_ascii=True,allow_nan=False))]
            if index==2:messages.append(Message(role='system',content='Previous candidate rejected. Return complete JSON. Codes: '+
                json.dumps([{'code':e.code,'path':e.path} for e in issues])))
            captured=[]
            result=self.gateway.generate_structured(StructuredRequest(messages=messages,trace_id=str(context.trace_id),
                temperature=0.0,max_output_tokens=min(self.gateway.config.max_output_tokens,4096)),output_model=output_model,output_observer=captured.append)
            metadata=CallRecord.model_validate({k:v for k,v in result.model_dump().items() if k in CallRecord.model_fields}).model_dump(mode='json')
            current=context.model_copy(update={'model_calls_json':json.dumps([a.model_call for a in attempts]+[metadata])})
            validated=None; retry=False
            if result.status=='success':
                try:validated=validate_investigation_plan(InvestigationPlan.model_validate(result.data.data),current);issues=()
                except PlanValidationError as exc:issues=exc.issues;retry=True
                except (ValueError,TypeError):issues=(issue('SCHEMA_VALIDATION_FAILED'),);retry=True
            else:
                issues=(issue(result.error.code),)
                retry=result.error.code in _REPAIRABLE or result.error.code in _TRANSIENT and result.error.retryable
            attempt=PlannerAttempt(attempt_index=index,model_call=metadata,diagnostic=captured[0].model_dump(mode='json') if captured else None,
                raw_unavailable_reason=None if captured else 'NO_TEXT_RESPONSE',issues=issues,validation_status='VALIDATED' if validated else 'REJECTED')
            attempts.append(attempt)
            try:self.trace_sink.record_attempt(current,attempt)
            except Exception:return PlanningOutcome(status='PLANNING_FAILED',issues=(issue('AUDIT_WRITE_FAILED'),),attempts=tuple(attempts))
            if validated:return PlanningOutcome(status='VALIDATED',validated_plan=validated,attempts=tuple(attempts))
            if not retry:break
        return PlanningOutcome(status='PLANNING_FAILED',issues=issues,attempts=tuple(attempts))

