"""One bounded structured Gateway call; candidates never grant trust or execution."""
import json
from pathlib import Path
from typing import Literal
from pydantic import Field
from app.enrichment.contracts import ClaimType
from app.enrichment.versions import canonical_value
from app.llm.schemas import StructuredRequest
from app.agents.verification.schemas import Bounded,Identifier

PROMPT_VERSION='verification-assist-v1'


class ModelHint(Bounded):
    claim_id:Identifier
    evidence_id:Identifier
    quote:str=Field(min_length=1,max_length=1200)
    source_field:Literal['content']
    proposed_type:ClaimType
    proposed_value:dict
    matching_hint:str=Field(max_length=500)


class ModelHintResponse(Bounded):
    hints:tuple[ModelHint,...]=Field(default=(),max_length=8)


class ModelAssistResult(ModelHintResponse):
    warnings:tuple[str,...]=()
    model_calls:tuple[dict,...]=()


def validate_hints(hints,snapshot):
    valid=[];warnings=list(hints.warnings)
    claims={c.claim_id:c for c in snapshot.claims}
    evidence={e.evidence_id:e for e in snapshot.evidence}
    for candidate in hints.hints:
        c=claims.get(candidate.claim_id);e=evidence.get(candidate.evidence_id)
        if (c is None or e is None or e.claim_id!=c.claim_id or candidate.quote not in e.content[:1200] or
            candidate.proposed_type!=c.claim_type or canonical_value(c.claim_type,candidate.proposed_value)!=canonical_value(c.claim_type,c.value)):
            warnings.append('MODEL_HINT_REJECTED: ID, exact quote, type or value not grounded')
        else:valid.append(candidate)
    return ModelAssistResult(hints=tuple(valid),warnings=tuple(dict.fromkeys(warnings)),model_calls=hints.model_calls)


def assist_claims(context,*,gateway,remaining_seconds):
    if not context.request.model_assistance:return ModelAssistResult()
    if remaining_seconds<1:return ModelAssistResult(warnings=('MODEL_ASSIST_BUDGET_EXHAUSTED',))
    prompt=Path(__file__).with_name('verification_assist_v1.txt').read_text(encoding='utf-8')
    fragments=[]
    by_id={c.claim_id:c for c in context.snapshot.claims}
    for e in context.snapshot.evidence[:8]:
        c=by_id.get(e.claim_id)
        if c is None:continue
        fragments.append({'claim_id':c.claim_id,'claim_type':c.claim_type,'value':c.value,
                          'evidence_id':e.evidence_id,'content':e.content[:1200],'source_field':'content'})
    if not fragments:return ModelAssistResult(warnings=('MODEL_ASSIST_NO_GROUNDED_INPUT',))
    request=StructuredRequest(messages=[{'role':'system','content':prompt},
        {'role':'user','content':json.dumps({'content_trust':'UNTRUSTED_EXTERNAL_CONTENT','fragments':fragments},ensure_ascii=False)}],
        max_output_tokens=512,temperature=0.0,trace_id=str(context.context_id),schema_name='verification_hints')
    try:
        got=gateway.generate_structured(request,output_model=ModelHintResponse)
        call={'request_id':got.request_id,'provider':got.provider,'model':got.model,'function':got.function,
              'usage':got.usage.model_dump(mode='json'),'latency':got.duration_ms,'status':got.status,
              'error':got.error.model_dump(mode='json') if got.error else None,'prompt_version':PROMPT_VERSION}
        if got.status!='success':return ModelAssistResult(warnings=('MODEL_ASSIST_FAILED: '+got.error.code,),model_calls=(call,))
        hints=ModelHintResponse.model_validate(got.data.data)
        return validate_hints(ModelAssistResult(hints=hints.hints,model_calls=(call,)),context.snapshot)
    except Exception:
        # Gateway normally envelopes failures; preserve unexpected adapter/config failures too.
        return ModelAssistResult(warnings=('MODEL_ASSIST_FAILED: unavailable bounded structured response',))
