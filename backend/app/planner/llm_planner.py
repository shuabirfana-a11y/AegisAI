"""Bounded structured model planning, separate from deterministic task execution."""
import json
from pathlib import Path
from app.llm.gateway import ModelGateway
from app.llm.schemas import CallRecord, StructuredRequest, Message
from app.planner.interface import PlannerTraceSink
from app.planner.schemas import (ModelIdentity, PlannerPlan, PlanningOutcome, PlannerAttempt,
                                 ValidationIssue, PROMPT_VERSION, REGISTRY_VERSION)
from app.planner.registry import TASK_REGISTRY, MISSING_FIELDS
from app.planner.validator import validate_plan, PlanValidationError, missing_fields
from app.tooling.contracts import REGISTRY

_REPAIRABLE=frozenset({'INVALID_JSON','SCHEMA_VALIDATION_FAILED','OUTPUT_TRUNCATED','INVALID_RESPONSE'})
_TRANSIENT=frozenset({'TIMEOUT','NETWORK_ERROR','RATE_LIMITED','PROVIDER_ERROR'})

def issue(code,path='$'):
    return ValidationIssue(code=code,path=path,message='Planning failed; no candidate executed.')

class LLMTaskPlanner:
    def __init__(self, gateway: ModelGateway, trace_sink: PlannerTraceSink):
        self.gateway=gateway
        self.trace_sink=trace_sink
        self._prompt=Path(__file__).with_name('prompts').joinpath('task_plan_v1.txt').read_text(encoding='utf-8')

    @property
    def model_identity(self):
        c=self.gateway.config
        return ModelIdentity(provider=c.provider,model=c.model,is_mock=c.provider=='mock')
    @property
    def prompt_version(self):return PROMPT_VERSION
    @property
    def registry_version(self):return REGISTRY_VERSION

    def plan(self,input,context):
        roles={kind:{'allowed_tools':sorted(role.tools),'minimum_criteria':sorted(role.criteria)}
               for kind,role in TASK_REGISTRY.items()}
        payload={'input_scope':context.scope,'permissions':sorted(context.policy.permissions),
            'runtime_policy':context.policy.model_dump(mode='json'),'roles':roles,
            'tool_inputs':{n:REGISTRY[n].input.model_json_schema() for role in TASK_REGISTRY.values() for n in role.tools},
            'missing_fields':sorted(missing_fields(context.scope,context.policy)&MISSING_FIELDS)}
        attempts=[];issues=();validated=None
        for index in (1,2):
            messages=[Message(role='system',content=self._prompt),
                      Message(role='user',content=json.dumps(payload,ensure_ascii=True,allow_nan=False))]
            if index==2:
                messages.append(Message(role='system',content='Previous candidate rejected. Return complete JSON. Codes: '+
                    json.dumps([{'code':e.code,'path':e.path} for e in issues])))
            captured=[]
            result=self.gateway.generate_structured(StructuredRequest(messages=messages,
                trace_id=str(context.trace_id),max_output_tokens=min(self.gateway.config.max_output_tokens,4096)),
                output_model=PlannerPlan,output_observer=captured.append)
            metadata=CallRecord.model_validate({k:v for k,v in result.model_dump().items()
                if k in CallRecord.model_fields}).model_dump(mode='json')
            calls=[a.model_call for a in attempts]+[metadata]
            current=context.model_copy(update={'model_calls_json':json.dumps(calls)})
            retry=False
            if result.status=='success':
                try:
                    candidate=PlannerPlan.model_validate(result.data.data)
                    validated=validate_plan(candidate,current)
                    issues=()
                except PlanValidationError as exc:
                    issues=exc.issues;retry=True
                except (ValueError,TypeError):
                    issues=(issue('SCHEMA_VALIDATION_FAILED'),);retry=True
            else:
                issues=(issue(result.error.code),)
                retry=result.error.code in _REPAIRABLE or (result.error.code in _TRANSIENT and result.error.retryable)
            attempt=PlannerAttempt(attempt_index=index,model_call=metadata,
                diagnostic=captured[0].model_dump(mode='json') if captured else None,
                raw_unavailable_reason=None if captured else 'NO_TEXT_RESPONSE',
                issues=issues,validation_status='VALIDATED' if validated else 'REJECTED')
            attempts.append(attempt)
            try:self.trace_sink.record_attempt(current,attempt)
            except Exception:
                return PlanningOutcome(status='PLANNING_FAILED',issues=(issue('AUDIT_WRITE_FAILED'),),attempts=tuple(attempts))
            if validated:
                return PlanningOutcome(status='VALIDATED',validated_plan=validated,attempts=tuple(attempts))
            if not retry:break
        return PlanningOutcome(status='PLANNING_FAILED',issues=issues,attempts=tuple(attempts))
