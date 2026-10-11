"""A bounded model facade; it does not run tools or update business records."""
from datetime import datetime, timezone
import hashlib
import json
import re
import time
from uuid import uuid4
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, TypeAdapter, ValidationError
from referencing import Registry
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT202012
from app.llm.config import ConfigError, ModelConfig
from app.llm.providers import create_provider
from app.llm.providers.base import ProviderFailure
from app.llm.records import DefaultRecordSink, logger
from app.llm.diagnostics import OutputObserver, capture_output
from app.llm.schemas import (
    CallRecord, Capability, EmbeddingData, EmbeddingRequest, HealthData, ModelError,
    ModelResult, SafeName, Strict, StructuredData, StructuredRequest, TextData,
    TextRequest, TraceId, Usage, strict_json,
)


class HealthRequest(Strict):
    capability: Capability = 'text'
    trace_id: TraceId | None = None


def deny_retrieval(uri):
    raise NoSuchResource(ref=uri)


def prepare_schema(request, output_model):
    if (request.json_schema is None) == (output_model is None):
        raise ProviderFailure('INVALID_SCHEMA')
    try:
        if output_model is not None:
            if not isinstance(output_model, type) or not issubclass(output_model, BaseModel):
                raise ValueError('Invalid output model')
            schema = output_model.model_json_schema()
            name = output_model.__name__
        else:
            schema, name = request.json_schema, request.schema_name
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name):
            raise ValueError('Invalid schema name')
        encoded = json.dumps(schema, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')
        if len(encoded) > 65536:
            raise ValueError('Oversize schema')
        nodes = 0
        local_refs = set()

        def visit(value, depth=0):
            nonlocal nodes
            nodes += 1
            if depth > 32 or nodes > 10000:
                raise ValueError('Schema complexity limit')
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in ('$ref', '$dynamicRef', '$id') and (not isinstance(child, str) or not child.startswith('#')):
                        raise ValueError('External schema reference')
                    if key in ('$ref', '$dynamicRef'):
                        local_refs.add(child)
                    visit(child, depth + 1)
            elif isinstance(value, list):
                for child in value:
                    visit(child, depth + 1)
        visit(schema)
        if '$schema' in schema and schema['$schema'] not in (
            'https://json-schema.org/draft/2020-12/schema',
            'http://json-schema.org/draft/2020-12/schema',
        ):
            raise ValueError('Unsupported schema dialect')
        Draft202012Validator.check_schema(schema)
        base_uri = 'urn:aegis:output-schema'
        registry = Registry(retrieve=deny_retrieval).with_resource(base_uri, DRAFT202012.create_resource(schema))
        resolver = registry.resolver(base_uri)
        for ref in local_refs:
            target = resolver.lookup(ref).contents
            if not isinstance(target, (dict, bool)):
                raise ValueError('Reference target is not a schema')
            Draft202012Validator.check_schema(target)
        validator = Draft202012Validator(schema, format_checker=FormatChecker(),
                                         registry=registry)
        return schema, name, hashlib.sha256(encoded).hexdigest(), validator
    except ProviderFailure:
        raise
    except Exception:
        raise ProviderFailure('INVALID_SCHEMA') from None


class ModelGateway:
    def __init__(self, config=None, *, text_provider=None, embedding_provider=None, record_sink=None):
        self.config = config or ModelConfig.from_env()
        if not isinstance(self.config, ModelConfig):
            raise ConfigError('ModelConfig required.')
        self._closed = False
        self.record_sink = record_sink if record_sink is not None else DefaultRecordSink()
        self.text_provider = text_provider or create_provider(self.config.provider, self.config, 'text')
        try:
            self.embedding_provider = embedding_provider or create_provider(self.config.embedding_provider, self.config, 'embedding')
            for provider, name, model in (
                (self.text_provider, self.config.provider, self.config.model),
                (self.embedding_provider, self.config.embedding_provider, self.config.embedding_model),
            ):
                if provider.name != name or provider.model != model or provider.is_mock != (name == 'mock'):
                    raise ConfigError('Adapter identity does not match model configuration.')
        except Exception:
            created = [self.text_provider, getattr(self, 'embedding_provider', None)]
            closed = set()
            for provider in created:
                if provider is not None and id(provider) not in closed:
                    closed.add(id(provider))
                    try:
                        provider.close()
                    except Exception:
                        pass  # Preserve the original construction failure; never expose close errors.
            raise

    def generate_text(self, request: TextRequest) -> ModelResult[TextData]:
        return self._invoke('generate_text', request, TextRequest, 'text')

    def generate_structured(self, request: StructuredRequest, *, output_model: type[BaseModel] | None = None,
                            output_observer: OutputObserver | None = None) -> ModelResult[StructuredData]:
        return self._invoke('generate_structured', request, StructuredRequest, 'text', output_model, output_observer)

    def embed(self, request: EmbeddingRequest) -> ModelResult[EmbeddingData]:
        return self._invoke('embed', request, EmbeddingRequest, 'embedding')

    def health_check(self, *, capability: Capability = 'text', trace_id: str | None = None) -> ModelResult[HealthData]:
        return self._invoke('health_check', {'capability': capability, 'trace_id': trace_id},
                            HealthRequest, 'embedding' if capability == 'embedding' else 'text')

    def _safe_name(self, value):
        name = TypeAdapter(SafeName).validate_python(value)
        secret = self.config.api_key.get_secret_value() if self.config.api_key else ''
        if '://' in name or (secret and secret in name):
            raise ValueError('Unsafe metadata')
        return name

    def _invoke(self, function, raw, request_type, capability, output_model=None, output_observer=None):
        started = datetime.now(timezone.utc)
        clock = time.perf_counter()
        provider = self.embedding_provider if capability == 'embedding' else self.text_provider
        requested_model = self.config.embedding_model if capability == 'embedding' else self.config.model
        provider_name = self.config.embedding_provider if capability == 'embedding' else self.config.provider
        values = dict(request_id=str(uuid4()), trace_id=None, provider=provider_name,
                      requested_model=requested_model, model=requested_model, function=function,
                      is_mock=provider_name == 'mock', started_at=started, usage=Usage(),
                      attempt_count=0, warnings=[])
        data = None
        error = None
        try:
            if self._closed:
                raise ProviderFailure('GATEWAY_CLOSED')
            try:
                # Revalidate instances too: callers may have mutated a previous request.
                request = request_type.model_validate(raw.model_dump() if isinstance(raw, BaseModel) else raw)
                secret = self.config.api_key.get_secret_value() if self.config.api_key else ''
                if request.trace_id:
                    request.trace_id.encode('utf-8')
                    if '://' in request.trace_id or request.trace_id.startswith('//') or (secret and secret in request.trace_id):
                        raise ValueError('Unsafe trace')
                values['trace_id'] = request.trace_id
                if function in ('generate_text', 'generate_structured'):
                    if request.max_output_tokens and request.max_output_tokens > self.config.max_output_tokens:
                        raise ValueError('Output budget exceeded')
                    request = request.model_copy(update={
                        'max_output_tokens': request.max_output_tokens or self.config.max_output_tokens})
            except (ValueError, TypeError, UnicodeError):
                raise ProviderFailure('INVALID_INPUT') from None
            schema_parts = None
            if function == 'generate_structured':
                schema_parts = prepare_schema(request, output_model)
                request = request.model_copy(update={'schema_name': schema_parts[1]})
            values['attempt_count'] = 1
            if function == 'generate_text':
                response = provider.generate_text(request)
            elif function == 'generate_structured':
                response = provider.generate_structured(request, schema_parts[0])
            elif function == 'embed':
                response = provider.embed(request)
            else:
                response = provider.health_check(request.capability)
            if function == 'generate_structured' and output_observer is not None and isinstance(response.value, str):
                try:
                    output_observer(capture_output(response.value, values['request_id'],
                                                   values['trace_id'], secret))
                except Exception:
                    raise ProviderFailure('AUDIT_WRITE_FAILED') from None
            try:
                values['usage'] = Usage.model_validate(response.usage.model_dump())
                values['model'] = self._safe_name(response.model)
                values['warnings'] = [w for w in response.warnings if w == 'Provider response did not include a model name.']
            except (ValueError, TypeError, AttributeError):
                raise ProviderFailure('INVALID_RESPONSE') from None
            if function in ('generate_text', 'generate_structured'):
                if response.finish_reason == 'length':
                    raise ProviderFailure('OUTPUT_TRUNCATED')
                if not isinstance(response.value, str) or not response.value.strip():
                    raise ProviderFailure('INVALID_RESPONSE')
            if function == 'generate_text':
                data = TextData(text=response.value, finish_reason=response.finish_reason)
            elif function == 'generate_structured':
                try:
                    decoded = strict_json(response.value)
                except (ValueError, TypeError, RecursionError):
                    raise ProviderFailure('INVALID_JSON') from None
                try:
                    schema_parts[3].validate(decoded)
                    if output_model is not None:
                        decoded = output_model.model_validate_json(response.value, strict=True).model_dump(mode='json')
                    data = StructuredData(data=decoded, schema_name=schema_parts[1], schema_hash=schema_parts[2])
                except Exception:
                    raise ProviderFailure('SCHEMA_VALIDATION_FAILED') from None
            elif function == 'embed':
                try:
                    if len(response.value) != len(request.texts):
                        raise ValueError('Embedding count mismatch')
                    data = EmbeddingData(vectors=response.value, dimension=self.config.embedding_dimension, purpose=request.purpose)
                except (ValueError, TypeError):
                    raise ProviderFailure('INVALID_EMBEDDING') from None
            else:
                data = HealthData.model_validate(response.value.model_dump())
                if data.capability != request.capability:
                    raise ProviderFailure('INVALID_RESPONSE')
        except ProviderFailure as exc:
            error = exc.error
            if any(value is not None for value in (exc.usage.input_tokens, exc.usage.output_tokens, exc.usage.total_tokens)):
                values['usage'] = exc.usage
            if exc.model is not None:
                try:
                    values['model'] = self._safe_name(exc.model)
                except (ValueError, TypeError):
                    pass
        except Exception:
            error = ModelError.make('INTERNAL_ERROR')
        values.update(finished_at=max(started, datetime.now(timezone.utc)),
                      duration_ms=max(0, (time.perf_counter() - clock) * 1000),
                      status='failed' if error else 'success', data=None if error else data, error=error)
        result = ModelResult(**values)
        record_fields = set(CallRecord.model_fields)
        record = CallRecord(**{key: value for key, value in result.__dict__.items() if key in record_fields})
        try:
            self.record_sink.write(record)
        except Exception:
            try:
                logger.error('Model call audit failed; request_id=%s', result.request_id)
            except Exception:
                pass  # The returned audit error remains visible even if all logging is unavailable.
            values.update(status='failed', data=None, original_error=error,
                          error=ModelError.make('AUDIT_WRITE_FAILED'))
            result = ModelResult(**values)
        return result

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                self.text_provider.close()
            finally:
                if self.embedding_provider is not self.text_provider:
                    self.embedding_provider.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
