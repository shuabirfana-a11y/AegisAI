"""Read-only, bounded entity/relationship contracts; not a graph database."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.runtime.contracts import json_bytes

NodeType = Literal['VULNERABILITY','COMPONENT','VERSION','ASSET','EVIDENCE','RISK']
EdgeType = Literal['AFFECTS_COMPONENT','HAS_AFFECTED_RANGE','HAS_VERSION','DEPLOYED_ON','HAS_EVIDENCE','HAS_RISK','SUPPORTED_BY']
RelationStatus = Literal['SOURCE_ASSERTED','CANDIDATE','CONFIRMED','CONFLICT','PENDING','REJECTED','INSUFFICIENT_EVIDENCE','UNKNOWN','USER_INVENTORY']


class ReadOnly(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)


class KnowledgeNode(ReadOnly):
    id:str=Field(min_length=1,max_length=200)
    type:NodeType
    label:str=Field(max_length=400)
    data:dict[str,Any]=Field(default_factory=dict)


class KnowledgeEdge(ReadOnly):
    id:str
    type:EdgeType
    source:str
    target:str
    status:RelationStatus
    source_records:tuple[str,...]=Field(min_length=1,max_length=32)
    claim_ids:tuple[str,...]=Field(default=(),max_length=32)
    evidence_ids:tuple[str,...]=Field(default=(),max_length=32)
    historical_snapshot:bool=False


class KnowledgeGraph(ReadOnly):
    schema_version:Literal['security-knowledge-graph-v1']='security-knowledge-graph-v1'
    vulnerability_id:str
    canonical_id:str|None=None
    nodes:tuple[KnowledgeNode,...]=Field(default=(),max_length=160)
    edges:tuple[KnowledgeEdge,...]=Field(default=(),max_length=320)
    truncated:bool=False
    warnings:tuple[str,...]=()
    limitations:tuple[str,...]=('RELATIONS_DO_NOT_IMPLY_VERIFIED_IMPACT','NO_RISK_DECISION_SELECTED')
    investigation_id:str|None=None
    agent_references:tuple[dict[str,str],...]=()
    gate_status:str|None=None
    answer_id:str|None=None
    content_trust_level:Literal['UNTRUSTED_EXTERNAL_CONTENT']='UNTRUSTED_EXTERNAL_CONTENT'

    @model_validator(mode='after')
    def binding_and_budget(self):
        ids={n.id for n in self.nodes}
        if len(ids)!=len(self.nodes) or len({e.id for e in self.edges})!=len(self.edges):raise ValueError('Duplicate graph identity')
        if any(e.source not in ids or e.target not in ids for e in self.edges):raise ValueError('Dangling graph relationship')
        json_bytes(self.model_dump(mode='json'),128*1024)
        return self


class KnowledgeGraphPage(ReadOnly):
    items:tuple[KnowledgeGraph,...]=Field(default=(),max_length=10)
    total:int=Field(ge=0)
    offset:int=Field(ge=0)
    limit:int=Field(ge=1,le=10)
    limitations:tuple[str,...]=('LOCAL_COLLECTED_RELATIONS_ONLY','SOURCE_SEVERITY_IS_NOT_ASSET_RISK')
