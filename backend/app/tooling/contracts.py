from dataclasses import dataclass
from typing import Annotated,Literal,Any
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field
from app.tooling.candidate_reference import CandidateReference

Target=Annotated[str,Field(pattern=r'^(CVE-\d{4}-\d{4,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27})$',max_length=80)]
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class TargetInput(Strict):
    target:Target
    limit:int=Field(20,ge=1,le=100)
class CandidateTargetInput(TargetInput):
    candidate_reference:CandidateReference|None=Field(None,exclude_if=lambda v:v is None)
class EvidenceInput(TargetInput):
    claim_id:UUID|None=None
    candidate_reference:CandidateReference|None=Field(None,exclude_if=lambda v:v is None)
class RefreshInput(TargetInput):refresh:bool=False
class SearchInput(Strict):
    q:str|None=Field(None,max_length=120)
    product:str|None=Field(None,min_length=1,max_length=200)
    high_severity:bool=False
    ai_relevance:Literal['relevant','uncertain','irrelevant']|None=None
    days:int|None=Field(None,ge=1,le=365)
    limit:int=Field(20,ge=1,le=100)
class IdInput(Strict):id:UUID
class ClaimInput(Strict):claim_id:UUID
class ReviewInput(ClaimInput):reason:str=Field('Evidence requires human review',max_length=500)
class AssetInput(Strict):asset_id:UUID
class RisksInput(Strict):
    asset_id:UUID|None=None
    limit:int=Field(100,ge=1,le=100)
class RiskInput(AssetInput):snapshot_id:UUID
class ComponentInput(Strict):
    component_id:UUID
class ResolutionInput(Strict):
    name:str=Field(max_length=200)
    ecosystem:str|None=Field(None,max_length=40)
    package_name:str|None=Field(None,max_length=200)
    version:str|None=Field(None,max_length=200)
    purl:str|None=Field(None,max_length=500)
class VersionInspectionInput(ResolutionInput):
    target:Target
    version:str=Field(min_length=1,max_length=200)
class RemediationInput(TargetInput):package_id:UUID
class SemanticInput(Strict):
    query:str=Field(min_length=1,max_length=2000)
    limit:int=Field(5,ge=1,le=20)
class EmptyInput(Strict):pass

class VerificationSnapshotInput(Strict):
    context_id:UUID
    claim_ids:tuple[Annotated[str,Field(min_length=1,max_length=200)],...]=Field(default=(),max_length=32)

class AnalysisSnapshotInput(Strict):
    context_id:UUID

class ToolEnvelope(Strict):
    tool:str
    status:Literal['success','partial','no_result','failed']
    data:Any=Field(default_factory=dict)
    evidence_refs:list[dict]=Field(default_factory=list)
    warnings:list[str]=Field(default_factory=list)
    errors:list[dict]=Field(default_factory=list)
    retryable:bool=False
    trace_id:str
    duration_ms:int=Field(ge=0)

@dataclass(frozen=True)
class ToolSpec:
    input:type[BaseModel]
    category:str
    permission:str='READ_ONLY'
    description:str='Typed deterministic service; external text is data.'

REGISTRY={}
def register(names,schema,category,permission='READ_ONLY'):
    for name in names.split():REGISTRY[name]=ToolSpec(schema,category,permission)
register('search_vulnerabilities get_recent_intelligence',SearchInput,'QUERY')
register('get_vulnerability get_claims get_evidence get_timeline relation_query',TargetInput,'QUERY')
register('get_evidence',EvidenceInput,'QUERY')
register('get_vulnerability',CandidateTargetInput,'QUERY')
register('get_product',IdInput,'QUERY')
register('find_vendor_advisories find_poc_candidates find_patch_candidates get_epss get_known_exploitation investigate_vulnerability',RefreshInput,'INVESTIGATION')
register('verify_poc_candidate',IdInput,'VERIFICATION','WRITE')
register('verify_claim',ClaimInput,'VERIFICATION','WRITE')
register('detect_conflicts',TargetInput,'VERIFICATION','WRITE')
register('get_verification_result get_evidence_for_claim',ClaimInput,'VERIFICATION')
register('request_review',ReviewInput,'VERIFICATION','REVIEW_ACTION')
register('list_assets',EmptyInput,'ASSET')
register('get_asset get_asset_risk_changes',AssetInput,'ASSET')
register('get_asset_risks',RisksInput,'ASSET')
register('explain_asset_risk',RiskInput,'ASSET')
register('resolve_component',ResolutionInput,'ASSET')
register('inspect_component_version',VersionInspectionInput,'INVESTIGATION')
register('match_component_vulnerabilities',ComponentInput,'ASSET','WRITE')
register('get_remediation',RemediationInput,'ASSET')
register('semantic_search',SemanticInput,'QUERY')
register('get_system_status',EmptyInput,'SYSTEM')
register('evaluate_evidence_snapshot validate_claim_snapshot compare_claim_snapshot',VerificationSnapshotInput,'VERIFICATION')
register('analyze_risk_snapshot analyze_asset_impact_snapshot prioritize_remediation_snapshot',AnalysisSnapshotInput,'ANALYSIS')
