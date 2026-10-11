"""Explicitly synthetic outputs for offline demos and protocol tests."""
from copy import deepcopy
import hashlib
import json
from app.llm.providers.base import ProviderFailure, ProviderResponse
from app.llm.schemas import HealthData, Usage


class MockProvider:
    name = 'mock'
    is_mock = True

    def __init__(self, config, *, capability='text', structured_fixtures=None):
        self.model = config.model if capability == 'text' else config.embedding_model
        self.dimension = config.embedding_dimension
        self.fixtures = deepcopy(structured_fixtures if structured_fixtures is not None else {
            'VulnerabilityAnalysis': {'cve': 'CVE-2099-9999001', 'risk': 'high', 'evidence': []},
        })

    def _response(self, value):
        return ProviderResponse(value, self.model, Usage(input_tokens=0, output_tokens=0, total_tokens=0))

    def generate_text(self, request):
        return self._response('MOCK: synthetic model output; no real vulnerability assessment was performed.')

    def generate_structured(self, request, schema):
        if request.schema_name not in self.fixtures:
            raise ProviderFailure('CAPABILITY_UNSUPPORTED')
        value = self.fixtures[request.schema_name]
        return self._response(value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, allow_nan=False))

    def embed(self, request):
        vectors = []
        for text in request.texts:
            # Versioned model name identifies this synthetic byte-hash space.
            raw = hashlib.shake_256(('mock-embedding-v1\0' + request.purpose + '\0' + text).encode()).digest(self.dimension)
            vectors.append([(byte - 127.5) / 127.5 for byte in raw])
        return self._response(vectors)

    def health_check(self, capability):
        return self._response(HealthData(capability=capability, state='healthy', probe_kind='mock', model_seen=True))

    def close(self):
        pass
