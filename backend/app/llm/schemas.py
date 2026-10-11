"""Provider-independent, bounded public contracts."""
from datetime import datetime
import json
from typing import Annotated, Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict, Field, model_validator

SafeName = Annotated[str, Field(min_length=1, max_length=200, pattern=r'^[^\x00-\x20\x7f]+$')]
TraceId = Annotated[str, Field(min_length=1, max_length=150, pattern=r'^[^\x00-\x1f\x7f]+$')]
Capability = Literal['text', 'embedding']
Function = Literal['generate_text', 'generate_structured', 'embed', 'health_check']
T = TypeVar('T')
MAX_INPUT_BYTES = 65536


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, hide_input_in_errors=True)


class Message(Strict):
    role: Literal['system', 'user', 'assistant']
    content: str = Field(min_length=1)


class TextRequest(Strict):
    messages: list[Message] = Field(min_length=1, max_length=32)
    max_output_tokens: int | None = Field(None, ge=1, le=4096)
    temperature: float | None = Field(None, ge=0, le=2, allow_inf_nan=False)
    trace_id: TraceId | None = None

    @model_validator(mode='after')
    def bounded_text(self):
        if any(not m.content.strip() for m in self.messages):
            raise ValueError('Empty message')
        if sum(len(m.content.encode('utf-8')) for m in self.messages) > MAX_INPUT_BYTES:
            raise ValueError('Input exceeds byte limit')
        return self


class StructuredRequest(TextRequest):
    json_schema: dict | None = None
    schema_name: str = Field('result', pattern=r'^[A-Za-z0-9_-]{1,64}$')


class EmbeddingRequest(Strict):
    texts: list[str] = Field(min_length=1, max_length=32)
    purpose: Literal['query', 'document'] = 'document'
    trace_id: TraceId | None = None

    @model_validator(mode='after')
    def bounded_batch(self):
        if any(not text.strip() for text in self.texts):
            raise ValueError('Empty embedding input')
        if sum(len(text.encode('utf-8')) for text in self.texts) > MAX_INPUT_BYTES:
            raise ValueError('Input exceeds byte limit')
        if self.purpose == 'query' and len(self.texts) != 1:
            raise ValueError('Query requires one input')
        return self


class Usage(Strict):
    input_tokens: int | None = Field(None, ge=0)
    output_tokens: int | None = Field(None, ge=0)
    total_tokens: int | None = Field(None, ge=0)

    @model_validator(mode='after')
    def consistent(self):
        if None not in (self.input_tokens, self.output_tokens, self.total_tokens):
            if self.total_tokens < self.input_tokens + self.output_tokens:
                raise ValueError('Invalid usage total')
        return self


ERROR_MESSAGES = {
    'INVALID_INPUT': 'Model input is invalid or exceeds limits.',
    'INVALID_SCHEMA': 'Output schema is invalid or unsupported.',
    'CAPABILITY_UNSUPPORTED': 'Provider does not support this capability.',
    'AUTHENTICATION_FAILED': 'Model service authentication failed.',
    'RATE_LIMITED': 'Model service rate limit exceeded.',
    'TIMEOUT': 'Model service operation timed out.',
    'NETWORK_ERROR': 'Model service connection failed.',
    'PROVIDER_ERROR': 'Model service failed.',
    'PROVIDER_REQUEST_REJECTED': 'Model service rejected the request.',
    'INVALID_RESPONSE': 'Model service response is invalid.',
    'INVALID_JSON': 'Model output is not strict JSON.',
    'SCHEMA_VALIDATION_FAILED': 'Model output does not match the schema.',
    'INVALID_EMBEDDING': 'Embedding output is invalid.',
    'MODEL_REFUSED': 'Model refused the request.',
    'OUTPUT_TRUNCATED': 'Model output was truncated.',
    'MODEL_UNAVAILABLE': 'Configured model is unavailable.',
    'HEALTH_UNSUPPORTED': 'Provider does not support the health probe.',
    'AUDIT_WRITE_FAILED': 'Model call record could not be persisted.',
    'GATEWAY_CLOSED': 'Model gateway is closed.',
    'INTERNAL_ERROR': 'Model operation failed internally.',
}


class ModelError(Strict):
    code: str
    message: str
    retryable: bool = False

    @model_validator(mode='after')
    def safe_message(self):
        if self.code not in ERROR_MESSAGES or self.message != ERROR_MESSAGES[self.code]:
            raise ValueError('Unapproved error description')
        return self

    @classmethod
    def make(cls, code, retryable=False):
        return cls(code=code, message=ERROR_MESSAGES[code], retryable=retryable)


class TextData(Strict):
    text: str = Field(min_length=1)
    finish_reason: str


class StructuredData(Strict):
    data: dict
    schema_name: str
    schema_hash: str


class EmbeddingData(Strict):
    vectors: list[list[Annotated[float, Field(allow_inf_nan=False)]]]
    dimension: int = Field(ge=1, le=16384)
    purpose: Literal['query', 'document']

    @model_validator(mode='after')
    def valid_space(self):
        if not self.vectors or any(len(v) != self.dimension or not any(v) for v in self.vectors):
            raise ValueError('Invalid vector space')
        return self


class HealthData(Strict):
    capability: Capability
    state: Literal['healthy']
    probe_kind: Literal['mock', 'http_models', 'local_model_load']
    model_seen: bool


class ModelResult(Strict, Generic[T]):
    request_id: str
    trace_id: TraceId | None
    provider: SafeName
    requested_model: SafeName
    model: SafeName
    function: Function
    is_mock: bool
    status: Literal['success', 'failed']
    started_at: datetime
    finished_at: datetime
    duration_ms: float = Field(ge=0, allow_inf_nan=False)
    attempt_count: int = Field(ge=0, le=1)
    usage: Usage
    data: T | None
    error: ModelError | None
    original_error: ModelError | None = None
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def valid_envelope(self):
        if (self.status == 'success') != (self.data is not None and self.error is None):
            raise ValueError('Invalid result state')
        if self.status == 'failed' and (self.data is not None or self.error is None):
            raise ValueError('Invalid failure state')
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None or self.finished_at < self.started_at:
            raise ValueError('Invalid call times')
        return self


class CallRecord(Strict):
    request_id: str
    trace_id: TraceId | None
    provider: SafeName
    requested_model: SafeName
    model: SafeName
    function: Function
    is_mock: bool
    attempt_count: int
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    usage: Usage
    status: Literal['success', 'failed']
    error: ModelError | None
    original_error: ModelError | None = None


def strict_json(text):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('Invalid JSON constant')

    result = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
    # Reject numeric overflow and lone surrogate escapes before a success can be serialized.
    json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8')
    return result
