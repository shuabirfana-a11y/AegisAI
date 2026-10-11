from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,Field,field_validator

class NormalizedIntelligenceRecord(BaseModel):
    schema_version: str='aegis-normalized-1'
    record_type: str='vulnerability'
    source: str
    external_id: str
    external_ids: list[dict]
    raw_document_id: UUID
    retrieved_at: datetime
    published_at: datetime | None=None
    modified_at: datetime | None=None
    title: str | None=None
    description: str | None=None
    language: str | None=None
    record_status: Literal['published','withdrawn','rejected','unknown']='unknown'
    products: list[dict] | None=None
    packages: list[dict] | None=None
    affected_versions: list[dict] | None=None
    fixed_versions: list[dict] | None=None
    cvss: list[dict] | None=None
    cwe: list[str] | None=None
    references: list[dict] | None=None
    exploitation: dict | None=None
    upstream_lineage: list[str]=Field(default_factory=list)
    field_provenance: dict=Field(default_factory=dict)
    extensions: dict=Field(default_factory=dict)

    @field_validator('retrieved_at','published_at','modified_at')
    @classmethod
    def aware(cls,value):
        if value is not None and value.tzinfo is None: raise ValueError('Timezone-aware timestamps required')
        return value
