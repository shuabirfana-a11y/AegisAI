"""Public copies only; hashes and private evidence snapshots are never changed."""
import os
import re
from app.integration.redaction import credential_key, public_reference, public_lineage
from app.orchestration.composer import safe_text, safe_value, safe_reference, safe_impact_value
from app.investigation_api.schemas import PRIVATE_ARTIFACT_FIELDS

PRIVATE_KEYS = PRIVATE_ARTIFACT_FIELDS | frozenset({
    'details', 'metadata', 'configuration', 'config', 'headers', 'prompt', 'raw_output',
    'database_url', 'api_base', 'worker_token', 'worker_lease', 'owner', 'actor_principal',
    'file_path', 'path', 'internal_path', 'traceback', 'input_summary', 'output_summary',
})
PRIVATE_NORMALIZED = frozenset(re.sub(r'[^a-z0-9]', '', key.casefold()) for key in PRIVATE_KEYS)
# Paths may contain spaces. Be conservative within one quoted/line-delimited
# segment; the lookbehind prevents matching a public HTTP URL's path.
PATH = re.compile(r'''(?ix)
    (?<![a-z0-9]) [a-z]:[\\/] [^\r\n"'<>]+
    | (?<![a-z0-9:/]) /(?:home|users|etc|var|tmp|opt|root|mnt|run|srv|usr|workspace|workspaces|proc|sys|dev|media)/ [^\r\n"'<>]+
    | \\\\ [a-z0-9_.-]+ \\ [^\r\n"'<>]+
''')
AUTH = re.compile(r'(?i)\b(?:Bearer|Basic)\s+[^\s"<>]+|\bsk-[a-zA-Z0-9_-]{8,}')


def public_text(value):
    text = safe_text(value)
    text = PATH.sub('[REDACTED_PATH]', text)
    text = AUTH.sub('[REDACTED]', text)
    for name in ('MODEL_API_KEY', 'AEGIS_ASSET_TOKEN', 'NVD_API_KEY', 'GITHUB_TOKEN'):
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, '[REDACTED]')
    return text


def public_copy(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = re.sub(r'[^a-z0-9]', '', str(key).casefold())
            if credential_key(key) or normalized in PRIVATE_NORMALIZED:
                continue
            if key in ('value', 'observed_value') and isinstance(item, dict):
                result[key] = public_copy(safe_impact_value(item))
            elif key == 'reference' and isinstance(item, dict):
                result[key] = public_copy(safe_reference(item))
            elif key == 'lineage_key':
                result[key] = public_lineage(item) if isinstance(item, str) else None
            else:
                result[key] = public_copy(item)
        return result
    if isinstance(value, (tuple, list)):
        return [public_copy(item) for item in value]
    if isinstance(value, str):
        return public_text(public_reference(value))
    return value


def public_artifact(artifact, model):
    data = artifact.model_dump(mode='json', include=set(model.model_fields))
    return model.model_validate(public_copy(data))
