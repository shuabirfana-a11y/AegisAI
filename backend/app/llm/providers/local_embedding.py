"""Reuse the existing offline embedding model without moving its call sites."""
from threading import Lock
from app.llm.config import LOCAL_MODEL
from app.llm.providers.base import ProviderFailure, ProviderResponse
from app.llm.schemas import HealthData


class LocalEmbeddingAdapter:
    name = 'local_embedding'
    is_mock = False
    _load_lock = Lock()
    _inference_lock = Lock()

    def __init__(self, config, *, capability='embedding', loader=None):
        self.model = LOCAL_MODEL
        self._loader = loader
        self._engine = None

    def _load(self):
        try:
            with self._load_lock:
                if self._engine is None:
                    if self._loader is None:
                        from app.knowledge.embedding import local_embedding
                        engine = local_embedding()
                    else:
                        engine = self._loader()
                    if engine.model != self.model or engine.dimension != 384:
                        raise ValueError('Local model identity mismatch')
                    self._engine = engine
                return self._engine
        except Exception:
            raise ProviderFailure('MODEL_UNAVAILABLE') from None

    def generate_text(self, request):
        raise ProviderFailure('CAPABILITY_UNSUPPORTED')

    def generate_structured(self, request, schema):
        raise ProviderFailure('CAPABILITY_UNSUPPORTED')

    def embed(self, request):
        engine = self._load()
        try:
            with self._inference_lock:
                vectors = [engine.query(request.texts[0])] if request.purpose == 'query' else engine.passages(request.texts)
            return ProviderResponse(vectors, self.model)
        except Exception:
            raise ProviderFailure('MODEL_UNAVAILABLE') from None

    def health_check(self, capability):
        if capability != 'embedding':
            raise ProviderFailure('CAPABILITY_UNSUPPORTED')
        self._load()
        return ProviderResponse(HealthData(capability='embedding', state='healthy',
            probe_kind='local_model_load', model_seen=True), self.model)

    def close(self):
        # The existing shared lru_cache owns the model; do not unload it.
        pass
