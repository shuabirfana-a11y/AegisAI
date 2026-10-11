from dataclasses import dataclass,field
import httpx
from app.enrichment.contracts import CONTENT_TRUST

@dataclass
class WorkOutcome:
    status:str='NO_RESULT'
    claims:list=field(default_factory=list)
    evidence:list=field(default_factory=list)
    candidates:list=field(default_factory=list)
    checked:list=field(default_factory=list)
    warnings:list=field(default_factory=list)
    errors:list=field(default_factory=list)
    unresolved:list=field(default_factory=list)
    artifacts:dict=field(default_factory=dict)

def failure(exc,source):
    status=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else None
    code='RATE_LIMIT' if status in (403,429) else 'SOURCE_HTTP_ERROR' if status else 'SOURCE_TIMEOUT' if isinstance(exc,httpx.TimeoutException) else 'PARSER_ERROR'
    return {'code':code,'source':source,'retryable':status in (403,429,500,502,503,504) or isinstance(exc,(httpx.TimeoutException,httpx.NetworkError)),
        'detail':'Controlled '+type(exc).__name__}

class BaseEnricher:
    name='base'
    depends_on=()
    sources=()
    timeout={'http_seconds':30,'retries':2,'bounded_records':5}
    acceptance='Checked declared scope; saved evidence and explicit unresolved/error state'
    side_effects=('immutable raw/observation','scoped claims/evidence','typed candidate/snapshot','real timeline event')
    def investigate(self,context,session,acquisition):raise NotImplementedError

    def finish(self,outcome,acquisition,start):
        outcome.checked=list(acquisition.checked[start:])
        if outcome.errors:outcome.status='PARTIAL' if outcome.claims or outcome.candidates else 'FAILED'
        return outcome
