"""Register adapters here; imports and clients are lazy."""
from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class ProviderSpec:
    module: str
    adapter: str
    capabilities: frozenset[str]


REGISTRY = {
    'mock': ProviderSpec('mock', 'MockProvider', frozenset({'text', 'embedding'})),
    'openai_compatible': ProviderSpec('openai_compatible', 'OpenAICompatibleProvider', frozenset({'text', 'embedding'})),
    'local_embedding': ProviderSpec('local_embedding', 'LocalEmbeddingAdapter', frozenset({'embedding'})),
}


def create_provider(name, config, capability):
    spec = REGISTRY[name]
    adapter = getattr(import_module('app.llm.providers.' + spec.module), spec.adapter)
    return adapter(config, capability=capability)
