"""Strict contracts separating runner inputs, draft labels and reviewed outcomes."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False,
                              hide_input_in_errors=True)


class EvidenceReference(Contract):
    source_id: str = Field(min_length=1, max_length=200)
    locator: str = Field(min_length=1, max_length=2000)
    excerpt: str = Field(min_length=1, max_length=20000)


FORBIDDEN_INPUT_KEYS = {
    "expected", "expected_answer", "ground_truth", "gold", "gold_answer",
    "evidence_refs", "review_status", "annotator", "reviewer",
    "annotation_note", "should_abstain", "required_hops",
}


def reject_labels(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.strip().lower() in FORBIDDEN_INPUT_KEYS:
                raise ValueError("Annotation fields are prohibited in runtime inputs")
            reject_labels(item)
    elif isinstance(value, list):
        for item in value:
            reject_labels(item)
    return value


class Question(Contract):
    id: str = Field(min_length=1, max_length=200)
    category: Literal["facts", "version", "poc_patch", "risk", "multihop"]
    question: str = Field(min_length=1, max_length=10000)
    input_context: dict[str, JsonValue]
    origin: Literal["REAL_SOURCE", "CONTROLLED_SCENARIO", "TEST_FIXTURE"]
    source_ids: list[str] = Field(min_length=1, max_length=100)

    @field_validator("input_context")
    @classmethod
    def no_annotations(cls, value):
        return reject_labels(value)


class Annotation(Contract):
    id: str = Field(min_length=1, max_length=200)
    expected_answer: dict[str, JsonValue]
    evidence_refs: list[EvidenceReference]
    confidence: Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    review_status: Literal["PENDING", "APPROVED", "REVIEWED", "REJECTED"]
    annotator_type: Literal["MACHINE", "HUMAN"]
    reviewer_type: Literal["MACHINE", "HUMAN"]
    annotator: str
    reviewer: str
    annotation_note: str
    should_abstain: bool
    origin: Literal["SOURCE_REFERENCE", "HUMAN_GOLD", "TEST_FIXTURE"]
    required_hops: list[str] = Field(default_factory=list)


class ClaimOutput(Contract):
    claim_id: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=20000)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)


class Prediction(Contract):
    question_id: str
    baseline: str
    status: Literal["SUCCEEDED", "FAILED", "NOT_EVALUATED"]
    answer: dict[str, JsonValue] = Field(default_factory=dict)
    claims: list[ClaimOutput] = Field(default_factory=list)
    abstained: bool | None = None
    completed_hops: list[str] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0, ge=0)
    error_code: str | None = None
    error: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class ReviewedClaim(Contract):
    claim_id: str
    verdict: Literal["SUPPORTED", "HALLUCINATED", "CONTRADICTED", "UNRESOLVED"]
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    review_note: str = Field(min_length=1)


class OutcomeAudit(Contract):
    question_id: str
    baseline: str
    reviewer: str = ""
    reviewer_type: Literal["HUMAN", "MACHINE"]
    review_status: Literal["PENDING", "APPROVED", "REVIEWED", "REJECTED"]
    prediction_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    claims: list[ReviewedClaim]

    @model_validator(mode="after")
    def named_human_review(self):
        if self.reviewer_type == "HUMAN" and self.review_status in {"APPROVED", "REVIEWED"} and not self.reviewer.strip():
            raise ValueError("Accepted human outcome audit requires a named reviewer")
        if self.reviewer_type == "HUMAN" and self.review_status in {"APPROVED", "REVIEWED"} and not self.prediction_sha256:
            raise ValueError("Accepted human outcome audit requires an output hash")
        return self
