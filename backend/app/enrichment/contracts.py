from datetime import datetime
from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator

CONTENT_TRUST='UNTRUSTED_EXTERNAL_CONTENT'

class EnrichmentStatus(StrEnum):
    SUCCESS='SUCCESS'
    PARTIAL='PARTIAL'
    NO_RESULT='NO_RESULT'
    FAILED='FAILED'
    CONFLICT='CONFLICT'

class VerificationStatus(StrEnum):
    CONFIRMED='CONFIRMED'
    PENDING='PENDING'
    INSUFFICIENT_EVIDENCE='INSUFFICIENT_EVIDENCE'
    CONFLICT='CONFLICT'
    REJECTED='REJECTED'

class ClaimType(StrEnum):
    AFFECTS_PRODUCT='AFFECTS_PRODUCT'
    AFFECTS_VERSION='AFFECTS_VERSION'
    FIXED_VERSION='FIXED_VERSION'
    POC_EXISTS='POC_EXISTS'
    POC_ASSOCIATION='POC_ASSOCIATION'
    PATCH_EXISTS='PATCH_EXISTS'
    FIX_COMMIT='FIX_COMMIT'
    KNOWN_EXPLOITED='KNOWN_EXPLOITED'
    VENDOR_CONFIRMED='VENDOR_CONFIRMED'
    EXPLOIT_CONDITION='EXPLOIT_CONDITION'
    REMEDIATION='REMEDIATION'
    CVSS_SCORE='CVSS_SCORE'

class EnrichmentError(BaseModel):
    code:str
    source:str|None=None
    retryable:bool=False
    detail:str='Controlled failure; see trace'

class EnrichmentResult(BaseModel):
    model_config=ConfigDict(extra='forbid')
    task_id:UUID
    enrichment_type:str
    target_id:UUID
    status:EnrichmentStatus
    claims_created:int=Field(default=0,ge=0)
    evidence_created:int=Field(default=0,ge=0)
    candidates_created:int=Field(default=0,ge=0)
    sources_checked:list[dict]=Field(default_factory=list)
    warnings:list[str]=Field(default_factory=list)
    errors:list[EnrichmentError]=Field(default_factory=list)
    retryable:bool=False
    started_at:datetime
    finished_at:datetime
    duration_ms:float=Field(ge=0)
    trace_id:UUID
    artifacts:dict=Field(default_factory=dict)
    content_trust_level:str=CONTENT_TRUST

    @model_validator(mode='after')
    def timing(self):
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None or self.finished_at<self.started_at:
            raise ValueError('Terminal result requires ordered aware times')
        return self

class InvestigationArtifact(BaseModel):
    task_id:UUID
    target:UUID
    result:EnrichmentStatus
    claims:list[UUID]=Field(default_factory=list)
    evidence:list[UUID]=Field(default_factory=list)
    candidates:list[UUID]=Field(default_factory=list)
    unresolved:list[str]=Field(default_factory=list)
    errors:list[EnrichmentError]=Field(default_factory=list)
    dependencies:list[str]=Field(default_factory=list)
    trace_id:UUID
    content_trust_level:str=CONTENT_TRUST

DB_VERIFY={'CONFIRMED':'confirmed','PENDING':'pending','INSUFFICIENT_EVIDENCE':'insufficient','CONFLICT':'conflict','REJECTED':'rejected'}
API_VERIFY={v:k for k,v in DB_VERIFY.items()}
