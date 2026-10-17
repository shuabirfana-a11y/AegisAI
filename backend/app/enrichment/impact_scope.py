"""Frozen package/version scope; normalization is not an evidence verdict."""
import json,re
from typing import Literal,Any
from uuid import UUID
from pydantic import Field
from packaging.version import Version,InvalidVersion
from app.runtime.contracts import FrozenModel
from app.enrichment.versions import intervals

VERSION='impact-scope-v1'

def valid_fixed_version(value):
    if not isinstance(value,str) or not value or len(value)>120:return False
    try:Version(value);return True
    except InvalidVersion:return False

class ImpactInterval(FrozenModel):
    lower: str|None=None
    lower_inclusive: bool=True
    upper: str|None=None
    upper_inclusive: bool=False

class ScopeEvidenceReference(FrozenModel):
    evidence_id: str=Field(min_length=1,max_length=200)
    source_claim_id: str=Field(min_length=1,max_length=200)
    source_id: UUID|None=None
    raw_document_id: UUID|None=None
    observation_id: UUID|None=None
    reference: dict[str,Any]=Field(default_factory=dict)

class ImpactScope(FrozenModel):
    normalization_version: Literal['impact-scope-v1']=VERSION
    vulnerability_id: str
    affected_product: str|None=None
    affected_component: str|None=None
    ecosystem: str|None=None
    affected_version_range: tuple[ImpactInterval,...]=Field(default=(),max_length=128)
    fixed_version: str|None=None
    condition: str|None=None
    platform: str|None=None
    architecture: str|None=None
    branch: str|None=None
    source_artifact_id: UUID|None=None
    asset_id: UUID|None=None
    source_claim_ids: tuple[str,...]=Field(default=(),max_length=32)
    evidence_refs: tuple[ScopeEvidenceReference,...]=Field(default=(),max_length=128)
    source_refs: tuple[str,...]=Field(default=(),max_length=128)
    normalization_state: Literal['NORMALIZED','UNSUPPORTED']='UNSUPPORTED'
    verification_state: Literal['CONFIRMED','PENDING','CONFLICT','INSUFFICIENT_EVIDENCE','REJECTED']|None=None
    confidence: float|None=Field(default=None,ge=0,le=1)

def scope_intervals(value):
    found=intervals(value)
    if found is not None and len(found)>128:return ()
    return tuple(ImpactInterval(lower=str(lo) if lo is not None else None,lower_inclusive=li,
        upper=str(hi) if hi is not None else None,upper_inclusive=ui) for lo,li,hi,ui in found) if found is not None else ()

def explicit_fixed_constraint(value,reference,content):
    """An inclusive *patched_versions* field, never an affected upper bound."""
    raw=value.get('raw_expression');locator=(reference or {}).get('locator') or {}
    path=locator.get('json_pointer','')
    if value.get('version') is not None or not re.fullmatch(r'/vulnerabilities/[0-9]+/patched_versions',path):return None
    if not isinstance(raw,str) or len(raw)>120:return None
    try:
        if json.loads(content)!=raw:return None
    except (ValueError,TypeError):return None
    matched=re.fullmatch(r'\s*>=\s*([^\s,]+)\s*',raw)
    if not matched:return None
    try:return str(Version(matched.group(1)))
    except InvalidVersion:return None
