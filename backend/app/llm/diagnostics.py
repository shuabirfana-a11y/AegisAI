"""Explicit private diagnostic channel; never part of ModelResult or CallRecord."""
import hashlib
from typing import Protocol
from pydantic import Field
from app.runtime.contracts import FrozenModel

class StructuredOutputDiagnostic(FrozenModel):
    request_id: str
    trace_id: str | None
    raw_output: str
    original_bytes: int = Field(ge=0)
    sha256: str
    redacted: bool
    truncated: bool

class OutputObserver(Protocol):
    def __call__(self, diagnostic: StructuredOutputDiagnostic) -> None:...

def capture_output(text, request_id, trace_id, secret=''):
    raw=text.encode('utf-8',errors='surrogatepass')
    safe=text.replace(secret,'[REDACTED]') if secret else text
    encoded=safe.encode('utf-8',errors='replace')
    return StructuredOutputDiagnostic(request_id=request_id,trace_id=trace_id,
        raw_output=encoded[:65536].decode('utf-8',errors='ignore'),original_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),redacted=bool(secret and secret in text),
        truncated=len(encoded)>65536)
