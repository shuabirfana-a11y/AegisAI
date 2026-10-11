from dataclasses import dataclass,field
from typing import Iterable
from uuid import UUID
from datetime import datetime
from app.utils.time import utcnow

@dataclass
class RawEnvelope:
    external_id: str
    source_url: str
    raw_payload: bytes
    retrieved_at: datetime=field(default_factory=utcnow)
    content_type: str='application/json'
    http_status: int=200
    raw_id: UUID | None=None
    record_id: str | None=None
    payload: dict | None=None
    locator: dict | None=None
    metadata: dict=field(default_factory=dict)

@dataclass
class CollectionBatch:
    records: Iterable[RawEnvelope]
    checkpoint: dict
    pending: list[str]
    coverage: dict

class BaseCollector:
    source_key: str
    def collect(self,checkpoint,limit,persist_raw): raise NotImplementedError
    def normalize(self,payload,raw_id,retrieved_at): raise NotImplementedError
    def finalize_checkpoint(self,before,candidate,pending,failed):
        return {**(before or {}),'pending':pending,'candidate_checkpoint':candidate} if pending or failed else candidate
