from datetime import datetime
from typing import Literal
from pydantic import Field,model_validator
from app.tooling.contracts import Strict,Target
from uuid import UUID

class QueryRequest(Strict):
    question:str=Field(min_length=1,max_length=2000)
    asset_id:UUID|None=None
    target:Target|None=None
    mode:Literal['auto','fast','deep']='auto'
    request_key:str=Field(min_length=1,max_length=150)
    realtime:bool=False

class TaskContract(Strict):
    task_id:str=Field(min_length=1,max_length=100)
    goal:str=Field(max_length=500)
    task_type:Literal['Investigation','Verification','SecurityAnalysis']
    inputs:dict
    constraints:dict=Field(default_factory=lambda:{'external_content':'data_only','max_calls':8})
    dependencies:list[str]=Field(default_factory=list)
    allowed_tools:list[str]
    expected_output:dict=Field(default_factory=lambda:{'schema':'TaskArtifact-v1'})
    evidence_required:bool=False
    acceptance_criteria:list[str]=Field(default_factory=lambda:['typed output','matching task and trace','only accepted dependencies'])
    timeout:int=Field(30,ge=1,le=60)
    retry_policy:dict=Field(default_factory=lambda:{'max_retries':1,'retryable_only':True})
    failure_policy:Literal['abstain','replan','human_review']='abstain'

class TaskArtifact(Strict):
    task_id:str
    agent:Literal['Investigation','Verification','SecurityAnalysis']
    status:Literal['success','partial','failed','blocked']
    result:dict
    claims:list[dict]=Field(default_factory=list)
    evidence_refs:list[dict]=Field(default_factory=list)
    unresolved:list[str]=Field(default_factory=list)
    warnings:list[str]=Field(default_factory=list)
    errors:list[dict]=Field(default_factory=list)
    trace_id:str
    started_at:datetime
    finished_at:datetime
    @model_validator(mode='after')
    def timing(self):
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None or self.finished_at<self.started_at:raise ValueError('Ordered aware times required')
        return self
