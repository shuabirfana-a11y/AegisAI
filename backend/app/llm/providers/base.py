"""Only adapters understand model service response objects."""
from dataclasses import dataclass, field
from typing import Generic, Protocol, TypeVar
from app.llm.schemas import Capability, EmbeddingRequest, HealthData, ModelError, StructuredRequest, TextRequest, Usage

T = TypeVar('T')


@dataclass
class ProviderResponse(Generic[T]):
    value: T
    model: str
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = 'stop'
    warnings: list[str] = field(default_factory=list)


class ProviderFailure(Exception):
    def __init__(self, code, *, retryable=False, usage=None, model=None):
        self.error = ModelError.make(code, retryable)
        self.usage = usage or Usage()
        self.model = model
        super().__init__(self.error.message)


class Provider(Protocol):
    name: str
    model: str
    is_mock: bool

    def generate_text(self, request: TextRequest) -> ProviderResponse[str]: ...
    def generate_structured(self, request: StructuredRequest, schema: dict) -> ProviderResponse[str]: ...
    def embed(self, request: EmbeddingRequest) -> ProviderResponse[list[list[float]]]: ...
    def health_check(self, capability: Capability) -> ProviderResponse[HealthData]: ...
    def close(self) -> None: ...
