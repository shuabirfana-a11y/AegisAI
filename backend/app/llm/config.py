"""Independent model configuration; never reads a dotenv file automatically."""
import os
from typing import Literal, Mapping
from urllib.parse import urlsplit
from pydantic import ConfigDict, Field, SecretStr, ValidationError, model_validator
from app.llm.providers import REGISTRY
from app.llm.schemas import SafeName, Strict

LOCAL_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'


class ConfigError(ValueError):
    pass


class ModelConfig(Strict):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True, hide_input_in_errors=True)
    provider: SafeName = 'mock'
    model: SafeName | None = None
    api_base: str | None = Field(None, repr=False, exclude=True)
    api_key: SecretStr | None = Field(None, repr=False, exclude=True)
    allow_keyless_local: bool = False
    embedding_provider: SafeName | None = None
    embedding_model: SafeName | None = None
    embedding_dimension: int | None = Field(None, ge=1, le=16384)
    timeout_seconds: float = Field(30, ge=1, le=60, allow_inf_nan=False)
    max_output_tokens: int = Field(1024, ge=1, le=4096)
    structured_mode: Literal['prompt_json', 'json_object', 'json_schema'] = 'prompt_json'
    token_parameter: Literal['max_tokens', 'max_completion_tokens'] = 'max_tokens'
    reasoning_effort: Literal['none', 'low', 'medium', 'high'] | None = None

    @model_validator(mode='after')
    def complete_and_validate(self):
        embedding_provider = self.embedding_provider or self.provider
        for name, capability in ((self.provider, 'text'), (embedding_provider, 'embedding')):
            if name not in REGISTRY or capability not in REGISTRY[name].capabilities:
                raise ValueError('Unknown or unsupported provider')
        object.__setattr__(self, 'embedding_provider', embedding_provider)
        if self.model is None:
            if self.provider != 'mock':
                raise ValueError('Explicit model required')
            object.__setattr__(self, 'model', 'mock-text-v1')
        if self.embedding_model is None:
            defaults = {'mock': 'mock-embedding-v1', 'local_embedding': LOCAL_MODEL}
            if embedding_provider not in defaults:
                raise ValueError('Explicit embedding model required')
            object.__setattr__(self, 'embedding_model', defaults[embedding_provider])
        if self.embedding_dimension is None:
            if embedding_provider not in ('mock', 'local_embedding'):
                raise ValueError('Explicit embedding dimension required')
            object.__setattr__(self, 'embedding_dimension', 384)
        if embedding_provider == 'local_embedding' and (self.embedding_model != LOCAL_MODEL or self.embedding_dimension != 384):
            raise ValueError('Local embedding model is fixed')
        if 'openai_compatible' in (self.provider, embedding_provider):
            self._validate_remote()
        secret = self.api_key.get_secret_value() if self.api_key else ''
        for name in (self.model, self.embedding_model):
            name.encode('utf-8')
            if '://' in name or (secret and secret in name):
                raise ValueError('Unsafe model metadata')
        return self

    def _validate_remote(self):
        if not self.api_base or any(ord(c) <= 32 or ord(c) == 127 for c in self.api_base):
            raise ValueError('Explicit model address required')
        parsed = urlsplit(self.api_base)
        local = parsed.hostname in ('localhost', '127.0.0.1', '::1')
        # Accessing port also rejects malformed port syntax.
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError('Invalid port')
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Invalid model address')
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and local):
            raise ValueError('Model address requires HTTPS or explicit loopback HTTP')
        key = self.api_key.get_secret_value() if self.api_key else ''
        if not key and not (self.allow_keyless_local and local):
            raise ValueError('Model authentication required')
        if key and (not key.strip() or any(ord(c) <= 32 or ord(c) >= 127 for c in key)):
            raise ValueError('Invalid authentication value')
        object.__setattr__(self, 'api_base', self.api_base.rstrip('/'))

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None):
        env = os.environ if environ is None else environ
        names = {'MODEL_PROVIDER': 'provider', 'MODEL_NAME': 'model', 'MODEL_API_BASE': 'api_base',
                 'MODEL_API_KEY': 'api_key', 'MODEL_EMBEDDING_PROVIDER': 'embedding_provider',
                 'MODEL_EMBEDDING_NAME': 'embedding_model', 'MODEL_STRUCTURED_MODE': 'structured_mode',
                 'MODEL_TOKEN_PARAMETER': 'token_parameter', 'MODEL_REASONING_EFFORT': 'reasoning_effort'}
        values = {field: env[key] for key, field in names.items() if key in env}
        if values.get('reasoning_effort') == '':
            values.pop('reasoning_effort')
        try:
            if 'api_key' in values:
                values['api_key'] = SecretStr(values['api_key'])
            for key, field, parse in (
                ('MODEL_TIMEOUT_SECONDS', 'timeout_seconds', float),
                ('MODEL_MAX_OUTPUT_TOKENS', 'max_output_tokens', int),
                ('MODEL_EMBEDDING_DIMENSION', 'embedding_dimension', int),
            ):
                if key in env:
                    values[field] = parse(env[key])
            if 'MODEL_ALLOW_KEYLESS_LOCAL' in env:
                flag = env['MODEL_ALLOW_KEYLESS_LOCAL'].lower()
                if flag not in ('true', 'false', '1', '0'):
                    raise ValueError('Invalid boolean')
                values['allow_keyless_local'] = flag in ('true', '1')
            return cls(**values)
        except (ValueError, TypeError, ValidationError):
            raise ConfigError('Invalid model configuration; check provider, model, endpoint and limits.') from None
