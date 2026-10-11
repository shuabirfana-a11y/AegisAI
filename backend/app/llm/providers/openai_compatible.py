"""Minimal compatible HTTP protocol; no model SDK, retries or redirects."""
import json
import logging
import httpx
from pydantic import ValidationError
from app.llm.providers.base import ProviderFailure, ProviderResponse
from app.llm.schemas import HealthData, Usage, strict_json

MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class OpenAICompatibleProvider:
    name = 'openai_compatible'
    is_mock = False

    def __init__(self, config, *, capability='text', transport=None):
        self.config = config
        self.model = config.model if capability == 'text' else config.embedding_model
        headers = {'Accept': 'application/json'}
        if config.api_key and config.api_key.get_secret_value():
            headers['Authorization'] = 'Bearer ' + config.api_key.get_secret_value()
        # Library debug logging can include HTTP headers or URLs.
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        self.client = httpx.Client(headers=headers, follow_redirects=False, trust_env=False,
            timeout=httpx.Timeout(config.timeout_seconds, connect=min(5, config.timeout_seconds)),
            transport=transport)

    def _request(self, method, endpoint, body=None, *, health=False):
        try:
            with self.client.stream(method, self.config.api_base + endpoint, json=body) as response:
                status = response.status_code
                if health and status in (404, 405, 501):
                    raise ProviderFailure('HEALTH_UNSUPPORTED')
                if status in (401, 403):
                    raise ProviderFailure('AUTHENTICATION_FAILED')
                if status == 429:
                    raise ProviderFailure('RATE_LIMITED', retryable=True)
                if status >= 500:
                    raise ProviderFailure('PROVIDER_ERROR', retryable=True)
                if 300 <= status < 400:
                    raise ProviderFailure('INVALID_RESPONSE')
                if not 200 <= status < 300:
                    raise ProviderFailure('PROVIDER_REQUEST_REJECTED')
                chunks, size = [], 0
                for chunk in response.iter_bytes(chunk_size=8192):
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise ProviderFailure('INVALID_RESPONSE')
                    chunks.append(chunk)
                try:
                    result = strict_json(b''.join(chunks).decode('utf-8'))
                    if not isinstance(result, dict):
                        raise ValueError('Expected response object')
                    return result
                except (ValueError, TypeError, UnicodeError, RecursionError):
                    raise ProviderFailure('INVALID_RESPONSE') from None
        except httpx.TimeoutException:
            raise ProviderFailure('TIMEOUT', retryable=True) from None
        except httpx.DecodingError:
            raise ProviderFailure('INVALID_RESPONSE') from None
        except httpx.RequestError:
            raise ProviderFailure('NETWORK_ERROR', retryable=True) from None

    def _metadata(self, body, *, embedding=False):
        model = body.get('model')
        warnings = []
        if model is None:
            model = self.model
            warnings.append('Provider response did not include a model name.')
        raw = body.get('usage')
        if raw is None:
            usage = Usage()
        else:
            try:
                if not isinstance(raw, dict):
                    raise ValueError('Invalid usage')
                usage = Usage(input_tokens=raw.get('prompt_tokens', raw.get('input_tokens')),
                              output_tokens=0 if embedding else raw.get('completion_tokens', raw.get('output_tokens')),
                              total_tokens=raw.get('total_tokens'))
            except (ValueError, TypeError, ValidationError):
                raise ProviderFailure('INVALID_RESPONSE') from None
        return model, usage, warnings

    def _chat(self, request, schema=None):
        messages = [message.model_dump() for message in request.messages]
        body = {'model': self.model, 'messages': messages, 'stream': False, 'n': 1,
                self.config.token_parameter: request.max_output_tokens}
        if request.temperature is not None:
            body['temperature'] = request.temperature
        if schema is not None:
            messages.insert(0, {'role': 'system', 'content':
                'Return only a JSON object matching this output schema. No code fences or extra text.\n' +
                json.dumps(schema, ensure_ascii=True, allow_nan=False)})
            if self.config.structured_mode == 'json_object':
                body['response_format'] = {'type': 'json_object'}
            elif self.config.structured_mode == 'json_schema':
                body['response_format'] = {'type': 'json_schema', 'json_schema': {
                    'name': request.schema_name, 'schema': schema, 'strict': True}}
        result = self._request('POST', '/chat/completions', body)
        model, usage, warnings = self._metadata(result)
        try:
            choices = result['choices']
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError('Expected one choice')
            choice = choices[0]
            message = choice['message']
            if message.get('refusal') or choice.get('finish_reason') == 'content_filter':
                raise ProviderFailure('MODEL_REFUSED', usage=usage, model=model)
            finish = choice['finish_reason']
            if finish == 'length':
                raise ProviderFailure('OUTPUT_TRUNCATED', usage=usage, model=model)
            if finish != 'stop' or message.get('role') != 'assistant' or message.get('tool_calls'):
                raise ValueError('Unsupported choice')
            text = message['content']
            if not isinstance(text, str) or not text.strip():
                raise ValueError('Invalid content')
            return ProviderResponse(text, model, usage, finish, warnings)
        except ProviderFailure:
            raise
        except (KeyError, ValueError, TypeError, AttributeError):
            raise ProviderFailure('INVALID_RESPONSE', usage=usage, model=model) from None

    def generate_text(self, request):
        return self._chat(request)

    def generate_structured(self, request, schema):
        return self._chat(request, schema)

    def embed(self, request):
        result = self._request('POST', '/embeddings', {
            'model': self.model, 'input': request.texts, 'encoding_format': 'float'})
        model, usage, warnings = self._metadata(result, embedding=True)
        try:
            data = result['data']
            if not isinstance(data, list) or len(data) != len(request.texts):
                raise ValueError('Embedding count mismatch')
            indexed = {}
            for item in data:
                index = item['index']
                if type(index) is not int or not 0 <= index < len(data) or index in indexed:
                    raise ValueError('Invalid embedding index')
                indexed[index] = item['embedding']
            vectors = [indexed[index] for index in range(len(data))]
            return ProviderResponse(vectors, model, usage, warnings=warnings)
        except (KeyError, ValueError, TypeError):
            raise ProviderFailure('INVALID_EMBEDDING', usage=usage, model=model) from None

    def health_check(self, capability):
        result = self._request('GET', '/models', health=True)
        try:
            data = result['data']
            if not isinstance(data, list) or any(not isinstance(item, dict) or not isinstance(item.get('id'), str) for item in data):
                raise ValueError('Invalid models listing')
            if self.model not in {item['id'] for item in data}:
                raise ProviderFailure('MODEL_UNAVAILABLE')
            return ProviderResponse(HealthData(capability=capability, state='healthy',
                probe_kind='http_models', model_seen=True), self.model)
        except (KeyError, ValueError, TypeError):
            raise ProviderFailure('INVALID_RESPONSE') from None

    def close(self):
        self.client.close()
