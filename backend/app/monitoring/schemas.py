from datetime import datetime
from typing import Any,Literal
from pydantic import BaseModel,ConfigDict,Field

class Schema(BaseModel):model_config=ConfigDict(extra='forbid')

class SourceReference(Schema):
    source:str
    raw_document_id:str
    hash:str
    reference:str
    locator:dict[str,Any]=Field(default_factory=dict)
    retrieved_at:datetime
    published_at:datetime|None=None

class SecurityIntelligenceObject(Schema):
    schema_version:Literal['security-intelligence-v1']='security-intelligence-v1'
    id:str
    source:list[str]
    title:str
    type:Literal['vulnerability','paper','blog','advisory','analysis','knowledge']
    cve_id:str|None=None
    affected_product:list[str]=Field(default_factory=list)
    affected_version:list[dict[str,Any]]=Field(default_factory=list)
    fixed_versions:list[dict[str,Any]]=Field(default_factory=list)
    cvss:list[dict[str,Any]]=Field(default_factory=list)
    cwe:list[str]=Field(default_factory=list)
    published_time:datetime|None=None
    modified_time:datetime|None=None
    edition:str|None=None
    is_current:bool|None=None
    canonical_publication_id:str|None=None
    references:list[SourceReference]=Field(default_factory=list)
    status:Literal['SOURCE_ASSERTED','CANDIDATE','CONFLICT']='SOURCE_ASSERTED'
    publication_status:str='unknown'
    poc_status:Literal['POC_CANDIDATE','VERIFIED_EXPLOIT','NO_EVIDENCE']='NO_EVIDENCE'
    poc_search_status:Literal['NOT_RUN','COMPLETED','PARTIAL','FAILED']='NOT_RUN'
    pocs:list[dict[str,Any]]=Field(default_factory=list)
    patches:list[dict[str,Any]]=Field(default_factory=list)
    related_documents:list[dict[str,Any]]=Field(default_factory=list)
    evidence:list[dict[str,Any]]=Field(default_factory=list)
    asset_risk_access:Literal['AUTHENTICATED_ONLY']='AUTHENTICATED_ONLY'
    content_trust_level:Literal['UNTRUSTED_EXTERNAL_CONTENT']='UNTRUSTED_EXTERNAL_CONTENT'
    limitations:list[str]=Field(default_factory=list)

class IntelligencePage(Schema):
    items:list[SecurityIntelligenceObject]
    total:int
    offset:int
    limit:int

class SourceStatusPage(Schema):
    items:list[dict[str,Any]]
    total:int
    source_category_count:int
    collected_source_category_count:int=0
    coverage:str='Declared bounded sources; not global completeness or grade attainment'

class AssetRiskPage(Schema):
    items:list[dict[str,Any]]
    total:int
    offset:int
    limit:int
    scope:str='Authenticated actor-owned inventory only; no public internet scan'
