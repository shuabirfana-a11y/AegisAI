"""Local adapter contract and actual cached CPU embedding verification."""
import pytest
from app.llm import ModelConfig, ModelGateway
from app.llm.config import LOCAL_MODEL
from .test_contracts import MemorySink, module, request


class EmbeddingEngine:
    model = LOCAL_MODEL
    dimension = 384

    def __init__(self):
        self.calls = []

    def query(self, text):
        self.calls.append(('query', text))
        return [1.0] + [0.0] * 383

    def passages(self, texts):
        self.calls.append(('document', texts))
        return [[0.0, 1.0] + [0.0] * 382 for text in texts]


def local_config():
    return ModelConfig(embedding_provider='local_embedding')


def test_local_embedding_is_lazy_and_preserves_query_document_semantics():
    engine = EmbeddingEngine()
    loads = []
    def load():
        loads.append(True)
        return engine
    settings = local_config()
    adapter = module('providers.local_embedding').LocalEmbeddingAdapter(settings, loader=load)
    sink = MemorySink()
    with ModelGateway(settings, embedding_provider=adapter, record_sink=sink) as model:
        assert loads == []
        query = model.embed({'texts': ['query text'], 'purpose': 'query'})
        docs = model.embed({'texts': ['first', 'second'], 'purpose': 'document'})
    assert query.status == docs.status == 'success'
    assert not query.is_mock and query.model == LOCAL_MODEL
    assert query.data.vectors[0][0] == 1 and docs.data.vectors[0][1] == 1
    assert engine.calls == [('query', 'query text'), ('document', ['first', 'second'])]
    assert len(loads) == 1 and len(sink.records) == 2
    assert query.usage.total_tokens is None


def test_missing_local_model_does_not_download_or_fall_back_to_mock():
    def missing():
        raise FileNotFoundError('private-cache-directory')
    settings = local_config()
    adapter = module('providers.local_embedding').LocalEmbeddingAdapter(settings, loader=missing)
    with ModelGateway(settings, embedding_provider=adapter, record_sink=MemorySink()) as model:
        result = model.embed({'texts': ['query'], 'purpose': 'query'})
    assert result.error.code == 'MODEL_UNAVAILABLE' and not result.is_mock
    assert result.data is None and 'private-cache-directory' not in result.model_dump_json()


def test_local_health_reports_loaded_model_without_calling_inference():
    engine = EmbeddingEngine()
    settings = local_config()
    adapter = module('providers.local_embedding').LocalEmbeddingAdapter(settings, loader=lambda: engine)
    with ModelGateway(settings, embedding_provider=adapter, record_sink=MemorySink()) as model:
        result = model.health_check(capability='embedding')
    assert result.status == 'success' and result.data.probe_kind == 'local_model_load'
    assert engine.calls == []


def test_local_adapter_does_not_claim_text_generation_support():
    settings = local_config()
    adapter = module('providers.local_embedding').LocalEmbeddingAdapter(settings, loader=EmbeddingEngine)
    with pytest.raises(module('providers.base').ProviderFailure) as error:
        adapter.generate_text(request())
    assert error.value.error.code == 'CAPABILITY_UNSUPPORTED'


def test_local_model_identity_and_dimension_are_fixed():
    with pytest.raises(ValueError):
        ModelConfig(embedding_provider='local_embedding', embedding_model='another-model')
    with pytest.raises(ValueError):
        ModelConfig(embedding_provider='local_embedding', embedding_dimension=768)


def test_cached_real_local_embedding_through_gateway(monkeypatch):
    # This executes the existing cached model. It never counts an injected engine as real inference.
    monkeypatch.setenv('HF_HUB_OFFLINE', '1')
    monkeypatch.setenv('TRANSFORMERS_OFFLINE', '1')
    with ModelGateway(local_config(), record_sink=MemorySink()) as model:
        query = model.embed({'texts': ['AI model vulnerability evidence'], 'purpose': 'query'})
        docs = model.embed({'texts': ['A vendor advisory describes affected versions.',
                                     'A patch resolves the reported issue.']})
        health = model.health_check(capability='embedding')
    assert query.status == docs.status == health.status == 'success'
    assert query.model == docs.model == LOCAL_MODEL and not query.is_mock
    assert len(query.data.vectors) == 1 and len(docs.data.vectors) == 2
    assert query.data.dimension == docs.data.dimension == 384
    assert query.data.vectors[0] != docs.data.vectors[0]
