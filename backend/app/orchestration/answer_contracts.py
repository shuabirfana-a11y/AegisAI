"""Bounded delivery views; the underlying business verdicts remain immutable."""
from typing import Literal,ClassVar,Any
from uuid import UUID
from pydantic import AwareDatetime,Field,StrictBool,model_validator
from app.integration.contracts import Sized,ArtifactRef,Status,Hash
from app.enrichment.contracts import ClaimType,VerificationStatus
from app.agents.analysis.schemas import RiskLevel,Priority

AnswerStatus=Literal['COMPLETE','COMPLETE_WITH_WARNINGS','INCOMPLETE','REVIEW_REQUIRED','FAILED','CANCELLED']


class VerifiedFact(Sized):
    claim_id: str
    claim_type: ClaimType
    verification_status: Literal['CONFIRMED']='CONFIRMED'
    value: dict[str,Any]
    evidence_ids: tuple[str,...]=Field(min_length=1,max_length=128)
    source_artifact: ArtifactRef


class Citation(Sized):
    evidence_id: str
    claim_id: str
    hash: Hash
    source_id: UUID
    raw_document_id: UUID
    observation_id: UUID
    reference: dict[str,Any]
    verification_artifact: ArtifactRef


class DisputedClaim(Sized):
    """A preserved assessment, never a confirmed answer fact."""
    claim_id: str
    claim_type: ClaimType
    verification_status: Literal['PENDING','CONFLICT','INSUFFICIENT_EVIDENCE','REJECTED']
    value: dict[str,Any]
    scope_key: str=Field(max_length=256)
    supporting_evidence_ids: tuple[str,...]=Field(default=(),max_length=128)
    conflicting_evidence_ids: tuple[str,...]=Field(default=(),max_length=128)
    verification_artifact: ArtifactRef
    conclusion_scope: Literal['OBSERVATION']='OBSERVATION'


class EvidenceObservation(Sized):
    """Audit pointers include rejected/conflicting evidence without endorsing it."""
    evidence_id: str
    claim_id: str
    verification_status: VerificationStatus
    scope_key: str=Field(max_length=256)
    hash: Hash|None=None
    source_id: UUID|None=None
    raw_document_id: UUID|None=None
    observation_id: UUID|None=None
    reference: dict[str,Any]
    stance: Literal['support','contradict','neutral']
    directness: Literal['direct','mention','unknown']
    integrity_status: Literal['VALID','MISSING','INVALID']
    is_current: StrictBool
    verification_artifact: ArtifactRef
    conclusion_scope: Literal['OBSERVATION']='OBSERVATION'


class RiskView(Sized):
    risk_level: RiskLevel
    priority: Priority
    affected: StrictBool|None
    verification_status: VerificationStatus
    source_artifact: ArtifactRef
    asset_match_status: Literal['MATCHED','NOT_MATCHED','UNKNOWN']
    version_match_status: Literal['AFFECTED','NOT_AFFECTED','UNKNOWN']
    exploitation_status: Literal['KNOWN_EXPLOITED','VERIFIED_POC_ASSOCIATION','POC_CANDIDATE','UNKNOWN']
    usability: Literal['NOT_EVALUATED']='NOT_EVALUATED'
    patch_status: Literal['CONFIRMED_PRESENT','UNCONFIRMED','UNKNOWN']
    patch_applied: Literal['UNKNOWN']='UNKNOWN'
    conclusion_scope: Literal['ACCEPTED','OBSERVATION']

    @model_validator(mode='after')
    def abstention(self):
        if self.risk_level=='UNKNOWN' and self.priority!='REVIEW_REQUIRED':raise ValueError('UNKNOWN_REQUIRES_REVIEW')
        if self.verification_status!='CONFIRMED' and (self.affected is not None or self.risk_level!='UNKNOWN' or self.priority!='REVIEW_REQUIRED'):
            raise ValueError('UNVERIFIED_RISK_CONCLUSION')
        if self.risk_level=='LOW' and (self.affected is not False or self.version_match_status!='NOT_AFFECTED'):
            raise ValueError('LOW_REQUIRES_CONFIRMED_NON_IMPACT')
        return self


class AssetView(Sized):
    asset_id: UUID|None
    component_id: UUID|None
    deployed_version: str|None
    provenance: Literal['USER_INVENTORY_NOT_SCANNED']='USER_INVENTORY_NOT_SCANNED'
    source_artifact: ArtifactRef
    claim_ids: tuple[str,...]=()


class ActionView(Sized):
    action_id: str
    action_type: str
    summary: str
    category: Literal['IMMEDIATE','FURTHER_INVESTIGATION','LONG_TERM_HARDENING']
    fixed_version: str|None=None
    patch_reference: str|None=None
    claim_ids: tuple[str,...]=()
    evidence_ids: tuple[str,...]=()
    action_provenance: Literal['VERIFIED_CLAIM','GENERAL_PRECAUTION']
    applicability: Literal['CONFIRMED','UNKNOWN','NOT_APPLICABLE']
    source_artifact: ArtifactRef
    conclusion_scope: Literal['ACCEPTED','OBSERVATION']


class AnswerEnvelope(Sized):
    size_limit: ClassVar[int]=512*1024
    schema_version: Literal['answer-envelope-v1']='answer-envelope-v1'
    answer_id: UUID
    logical_investigation_id: UUID
    original_question: str=Field(min_length=1,max_length=2000)
    answer_status: AnswerStatus
    integration_status: Status|None=None
    summary: str=Field(max_length=2400)
    key_findings: tuple[str,...]=Field(default=(),max_length=32)
    affected_assets: tuple[AssetView,...]=Field(default=(),max_length=1)
    risk_assessment: RiskView|None=None
    recommended_actions: tuple[ActionView,...]=Field(default=(),max_length=32)
    verified_claims: tuple[VerifiedFact,...]=Field(default=(),max_length=32)
    disputed_claims: tuple[DisputedClaim,...]=Field(default=(),max_length=32)
    citations: tuple[Citation,...]=Field(default=(),max_length=128)
    evidence_observations: tuple[EvidenceObservation,...]=Field(default=(),max_length=128)
    evidence_references: tuple[str,...]=Field(default=(),max_length=128)
    warnings: tuple[str,...]=Field(default=(),max_length=128)
    unresolved_items: tuple[str,...]=Field(default=(),max_length=128)
    integration_result_id: UUID|None=None
    agent_run_references: tuple[UUID,...]=Field(default=(),max_length=3)
    accepted_source_run_references: tuple[UUID,...]=Field(default=(),max_length=3)
    trace_reference: UUID
    generated_at: AwareDatetime
    historical_snapshot: Literal[True]=True
    fact_origin: Literal['FROZEN_GATE_CONTEXT']='FROZEN_GATE_CONTEXT'
    explanation_provider: Literal['DETERMINISTIC_TEMPLATE']='DETERMINISTIC_TEMPLATE'

    @model_validator(mode='after')
    def references(self):
        expected={'PASS':'COMPLETE','PASS_WITH_WARNINGS':'COMPLETE_WITH_WARNINGS','REPLAN_REQUIRED':'INCOMPLETE',
                  'HUMAN_REVIEW_REQUIRED':'REVIEW_REQUIRED','FAILED':'FAILED'}
        if self.integration_status is not None:
            if not self.integration_result_id or expected[self.integration_status]!=self.answer_status:
                raise ValueError('ANSWER_GATE_STATUS_MISMATCH')
        elif self.answer_status not in ('FAILED','CANCELLED'):raise ValueError('COMPLETE_REQUIRES_GATE')
        facts={c.claim_id:c for c in self.verified_claims}
        citations={c.evidence_id:c for c in self.citations}
        disputed={c.claim_id:c for c in self.disputed_claims}
        observations={e.evidence_id:e for e in self.evidence_observations}
        if len(facts)!=len(self.verified_claims) or len(citations)!=len(self.citations):raise ValueError('DUPLICATE_ANSWER_REFERENCE')
        if len(disputed)!=len(self.disputed_claims) or len(observations)!=len(self.evidence_observations) or set(facts)&set(disputed):
            raise ValueError('DUPLICATE_ANSWER_OBSERVATION')
        if len(set(self.evidence_references))!=len(self.evidence_references) or set(self.evidence_references)!=set(observations):
            raise ValueError('EVIDENCE_REFERENCE_MISMATCH')
        if len(set(self.agent_run_references))!=len(self.agent_run_references) or not set(self.accepted_source_run_references)<=set(self.agent_run_references):
            raise ValueError('ANSWER_RUN_REFERENCE_MISMATCH')
        for c in self.citations:
            if c.claim_id not in facts or c.evidence_id not in facts[c.claim_id].evidence_ids:
                raise ValueError('DANGLING_ANSWER_CITATION')
            e=observations.get(c.evidence_id)
            if e is None or (e.claim_id,e.hash,e.source_id,e.raw_document_id,e.observation_id,e.reference,e.verification_artifact)!=(
                    c.claim_id,c.hash,c.source_id,c.raw_document_id,c.observation_id,c.reference,c.verification_artifact):
                raise ValueError('CITATION_OBSERVATION_MISMATCH')
        for f in self.verified_claims:
            if any(id not in citations or citations[id].claim_id!=f.claim_id for id in f.evidence_ids):raise ValueError('DANGLING_FACT_EVIDENCE')
        if self.answer_status in ('FAILED','CANCELLED') and (self.verified_claims or self.risk_assessment or self.recommended_actions or self.affected_assets):
            raise ValueError('FAILED_ANSWER_CANNOT_DELIVER_FACTS')
        accepted=self.integration_status in ('PASS','PASS_WITH_WARNINGS')
        if self.risk_assessment and self.risk_assessment.conclusion_scope!=('ACCEPTED' if accepted else 'OBSERVATION'):
            raise ValueError('ANSWER_CONCLUSION_SCOPE_MISMATCH')
        for a in self.recommended_actions:
            if a.conclusion_scope!=('ACCEPTED' if accepted else 'OBSERVATION'):raise ValueError('ACTION_SCOPE_MISMATCH')
            if a.fixed_version or a.patch_reference:
                if a.action_provenance!='VERIFIED_CLAIM' or not a.claim_ids or not a.evidence_ids:raise ValueError('UNGROUNDED_PRECISE_ACTION')
                if any(id not in facts for id in a.claim_ids) or any(id not in citations for id in a.evidence_ids):raise ValueError('DANGLING_ACTION_REFERENCE')
        return self
