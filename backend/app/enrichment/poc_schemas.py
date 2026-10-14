"""Read-only PoC snapshots. Association is not proof of exploit usability."""
from typing import Annotated, Literal
from uuid import UUID
from ipaddress import ip_address
from urllib.parse import parse_qsl
from datetime import timedelta
from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

POCStatus = Literal['NO_EVIDENCE','POC_CANDIDATE','VERIFIED_EXPLOIT']


def public_reference(value: HttpUrl) -> HttpUrl:
    host=(value.host or '').lower().rstrip('.')
    if value.username or value.password or '.' not in host or host.endswith(('.local','.localhost','.internal')):
        raise ValueError('Public credential-free HTTP reference required')
    try: address=ip_address(host.strip('[]'))
    except ValueError: address=None
    if address is not None and not address.is_global:
        raise ValueError('Private reference is forbidden')
    if any(k.lower() in {'token','access_token','api_key','apikey','key','password','authorization','signature','sig','awsaccesskeyid'}
           or k.lower().startswith(('x-amz-','x-goog-'))
           or any(part in k.lower() for part in ('credential','secret','password','token','api_key'))
           for k,_ in (*parse_qsl(value.query or ''),*parse_qsl(value.fragment or ''))):
        raise ValueError('Credential query parameter is forbidden')
    return value


PublicReference = Annotated[HttpUrl, AfterValidator(public_reference)]


class Snapshot(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)


class POCEvidence(Snapshot):
    id: UUID
    type: Literal['POC_EVIDENCE']='POC_EVIDENCE'
    claim_id: UUID
    source: str = Field(min_length=1,max_length=100)
    reference: PublicReference
    content: str = Field(max_length=2400)
    raw_document_id: UUID
    observation_id: UUID
    hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    retrieved_time: AwareDatetime
    is_current: bool
    stance: Literal['support','contradict','neutral']
    supports_exploit_validation: bool = False


class POCVerification(Snapshot):
    id: UUID
    claim_id: UUID
    claim_type: str
    status: Literal['CONFIRMED','PENDING','INSUFFICIENT_EVIDENCE','CONFLICT','REJECTED']
    current_revision: bool
    verified_time: AwareDatetime
    method: str
    verified_by_type: Literal['human','system']
    evidence_ref: tuple[UUID,...]
    exploit_validation: bool = False


class POCArtifact(Snapshot):
    schema_version: Literal['poc-artifact-v1']='poc-artifact-v1'
    id: UUID
    vulnerability_id: UUID
    source: str = Field(min_length=1,max_length=100)
    reference: PublicReference
    title: str = Field(min_length=1,max_length=300)
    description: str | None = Field(None,max_length=2400)
    language: str | None = Field(None,max_length=80)
    status: POCStatus
    created_time: AwareDatetime
    verified_time: AwareDatetime | None = None
    evidence_ref: tuple[UUID,...] = Field(min_length=1,max_length=128)
    evidence: tuple[POCEvidence,...] = Field(default=(),max_length=128)
    verification: tuple[POCVerification,...] = Field(default=(),max_length=128)
    association_status: str
    usability_status: str
    omitted_evidence_count: int = Field(default=0,ge=0)
    excluded_evidence_count: int = Field(default=0,ge=0)
    omitted_verification_count: int = Field(default=0,ge=0)
    exploit_executed: Literal[False]=False
    content_trust_level: Literal['UNTRUSTED_EXTERNAL_CONTENT']='UNTRUSTED_EXTERNAL_CONTENT'

    @model_validator(mode='after')
    def verification_basis(self):
        if set(self.evidence_ref)!={e.id for e in self.evidence}:
            raise ValueError('PoC evidence references must resolve inside the snapshot')
        if self.status=='VERIFIED_EXPLOIT':
            current={e.id:e for e in self.evidence if e.is_current and e.stance=='support' and e.supports_exploit_validation}
            valid=[v for v in self.verification if v.exploit_validation and v.current_revision
                and v.status=='CONFIRMED' and v.verified_by_type=='human' and self.created_time<=v.verified_time
                and any(current[eid].retrieved_time<=v.verified_time+timedelta(minutes=5)
                        for eid in v.evidence_ref if eid in current)]
            if not valid or self.verified_time not in {v.verified_time for v in valid}:
                raise ValueError('Verified exploit requires current linked human validation')
        elif self.verified_time is not None:
            raise ValueError('Candidate has no exploit verification time')
        return self


class POCPage(Snapshot):
    vulnerability_id: UUID
    canonical_id: str
    status: POCStatus
    search_status: Literal['NOT_RUN','COMPLETED','PARTIAL','FAILED']
    items: tuple[POCArtifact,...]
    total: int = Field(ge=0)
    stored_count: int = Field(ge=0)
    omitted_count: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1,le=100)
    as_of: AwareDatetime
    warnings: tuple[str,...] = ()
    limitations: tuple[str,...] = (
        'Static discovery only; this module never executes PoC code or scans a target.',
        'NO_EVIDENCE is bounded absence in stored records, not proof no exploit exists.',
        'Association confirmation alone cannot establish exploit usability.',
        'Missing title details/language/verification time remain unknown; links are not fetched by this GET.',
    )
