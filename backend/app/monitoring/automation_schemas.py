"""Bounded operator configuration and public automation DTOs; no storage rewrite."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,AwareDatetime

ExecutionMode=Literal['LIVE','MOCK','UNSPECIFIED']
LifecycleState=Literal['DISCOVERED','NORMALIZED','ENRICHING','VERIFIED','AVAILABLE']

class DTO(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)

class PipelineConfig(DTO):
    execution_mode:Literal['LIVE','MOCK']='LIVE'
    record_limit:int=Field(3,ge=1,le=100)
    target_budget:int=Field(20,ge=1,le=20)
    job_budget:int=Field(6,ge=0,le=20)
    asset_budget:int=Field(10,ge=0,le=100)
    cycle_seconds:float=Field(300,ge=1,le=3600,allow_inf_nan=False)
    allow_cve_bootstrap:bool=False

class CollectorSpec(DTO):
    source:str
    category:str
    adapter:str
    capability:Literal['LIVE_CAPABLE']='LIVE_CAPABLE'
    global_complete:Literal[False]=False
    scope:str

class SourceReceipt(DTO):
    source:str
    status:Literal['SUCCESS','PARTIAL','FAILED','NOT_DUE','BUSY','DISABLED','DEFERRED']
    sync_run_id:UUID|None=None
    targets:tuple[UUID,...]=()
    document_ids:tuple[UUID,...]=()
    errors:tuple[str,...]=()
    processed_jobs:int=0
    failed_jobs:int=0
    pending_jobs:int=0

class PipelineCycle(DTO):
    cycle_id:UUID
    execution_mode:Literal['LIVE','MOCK']
    status:Literal['SUCCESS','PARTIAL','FAILED','CANCELLED','BUSY']
    started_at:AwareDatetime
    finished_at:AwareDatetime
    sources:tuple[SourceReceipt,...]=()
    queued_jobs:int=0
    processed_jobs:int=0
    failed_jobs:int=0
    pending_jobs:int=0
    unresolved_jobs:int=0
    dependency_jobs:int=0
    failed_dependency_jobs:int=0
    backlog_runs:int=0
    resumed_sources:tuple[SourceReceipt,...]=()
    asset_jobs:int=0
    failed_asset_jobs:int=0
    deferred_targets:int=0
    warnings:tuple[str,...]=()

class EnrichmentProgress(DTO):
    kind:str
    job_id:UUID
    status:Literal['queued','running','success','partial','no_result','failed','conflict','cancelled']
    error_code:str|None=None
    retryable:bool=False
    finished_at:AwareDatetime|None=None

class IntelligenceRecord(DTO):
    id:UUID
    type:str
    title:str
    canonical_id:str|None=None
    sources:tuple[str,...]
    status:LifecycleState
    verification_status:Literal['CONFIRMED','PENDING','CONFLICT','INSUFFICIENT_EVIDENCE']
    execution_mode:ExecutionMode='UNSPECIFIED'
    enrichment_progress:tuple[EnrichmentProgress,...]=()
    query_available:bool
    verified_claims:int=0
    active_claims:int=0
    evidence_count:int=0
    knowledge_chunks:int=0
    stages:tuple[LifecycleState,...]
    observed_at:AwareDatetime
    published_at:AwareDatetime|None=None
    warnings:tuple[str,...]=()

class RecordPage(DTO):
    items:tuple[IntelligenceRecord,...]
    total:int
    offset:int
    limit:int
    availability_semantics:str='AVAILABLE is queryability, not a blanket verification or exploit verdict.'

class PipelineRun(DTO):
    sync_run_id:UUID
    cycle_id:UUID
    last_cycle_id:UUID
    source:str
    execution_mode:ExecutionMode
    status:Literal['RUNNING','SUCCESS','PARTIAL','FAILED','CANCELLED']
    collection_status:str
    processed_jobs:int
    failed_jobs:int
    pending_jobs:int=0
    targets:tuple[UUID,...]
    document_ids:tuple[UUID,...]
    started_at:AwareDatetime
    updated_at:AwareDatetime
    errors:tuple[str,...]=()

class PipelineRunPage(DTO):
    items:tuple[PipelineRun,...]
    total:int
    offset:int
    limit:int
    scheduler_semantics:str='Worker is operator opt-in; these GETs never trigger collection, models or risk computation.'
