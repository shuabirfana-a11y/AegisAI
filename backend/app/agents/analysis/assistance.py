"""The model may reorder existing explanations/actions; it cannot write operational facts."""
import json
from pathlib import Path
from typing import Literal
from pydantic import Field
from app.llm.schemas import StructuredRequest
from app.agents.verification.schemas import Bounded

PROMPT_VERSION='analysis-explanation-v1'


class ExplanationDraft(Bounded):
    explanation_sections: tuple[Literal['impact','exploitation','exposure','remediation','uncertainty'],...] = Field(max_length=5)
    factor_ids: tuple[str,...] = Field(max_length=128)
    action_ids: tuple[str,...] = Field(max_length=32)


class ExplanationResult(Bounded):
    reasoning_summary: str
    action_ids: tuple[str,...]
    status: Literal['DISABLED','SUCCEEDED','FAILED','SKIPPED']
    used: bool = False
    model_calls: tuple[dict,...] = ()
    warnings: tuple[str,...] = ()


def organize_explanation(context,assessment,*,gateway,remaining_seconds):
    base=dict(reasoning_summary=assessment.reasoning_summary,action_ids=tuple(a.action_id for a in assessment.recommended_actions))
    if not context.request.model_assistance:return ExplanationResult(**base,status='DISABLED')
    if remaining_seconds<1:return ExplanationResult(**base,status='SKIPPED',warnings=('MODEL_ASSIST_BUDGET_EXHAUSTED',))
    factors={f.factor_id:f for f in (*assessment.risk_factors,*assessment.mitigating_factors)}
    actions={a.action_id:a for a in assessment.recommended_actions}
    prompt=Path(__file__).with_name('analysis_explanation_v1.txt').read_text(encoding='utf-8')
    payload={'content_trust':'UNTRUSTED_EXTERNAL_CONTENT','immutable_decision':{
        'risk_level':assessment.risk_level,'priority':assessment.priority,'affected':assessment.affected,
        'version_match_status':assessment.version_match_status,'verification_status':assessment.verification_status},
        'factor_ids':list(factors),'action_ids':list(actions)}
    request=StructuredRequest(messages=[{'role':'system','content':prompt},
        {'role':'user','content':json.dumps(payload,ensure_ascii=False)}],max_output_tokens=512,temperature=0,
        trace_id=str(context.context_id),schema_name='analysis_explanation')
    calls=()
    try:
        got=gateway.generate_structured(request,output_model=ExplanationDraft)
        calls=({'request_id':got.request_id,'provider':got.provider,'model':got.model,'function':got.function,
            'usage':got.usage.model_dump(mode='json'),'latency':got.duration_ms,'status':got.status,
            'error':got.error.model_dump(mode='json') if got.error else None,'prompt_version':PROMPT_VERSION},)
        if got.status!='success':raise ValueError('Gateway did not return valid structured output')
        draft=ExplanationDraft.model_validate(got.data.data)
        if (len(draft.factor_ids)!=len(factors) or set(draft.factor_ids)!=set(factors) or
            len(draft.action_ids)!=len(actions) or set(draft.action_ids)!=set(actions) or
            len(set(draft.explanation_sections))!=len(draft.explanation_sections)):
            raise ValueError('Model changed mandatory grounded identifiers')
        text=assessment.reasoning_summary+' '+ ' '.join(factors[key].reason for key in draft.factor_ids)
        return ExplanationResult(reasoning_summary=text[:8000],action_ids=draft.action_ids,
            status='SUCCEEDED',used=True,model_calls=calls)
    except Exception:
        return ExplanationResult(**base,status='FAILED',used=True,model_calls=calls,
            warnings=('MODEL_ASSIST_FAILED: 解释回退至规则模板，原风险结论与动作依据保持不变。',))
