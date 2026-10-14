"""Deterministic Phase12-B HTTP exports; imports schemas, never starts services."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
METHODS = {'get', 'post', 'patch', 'put', 'delete'}
FOLDERS = [ROOT / 'docs/frontend-contracts', ROOT / 'AegisAI_FRONTEND_HANDOFF_PACKAGE/api/reference']


def identifier(name):
    return re.sub(r'\W', '_', name)


def typescript(schema):
    if '$ref' in schema:
        return identifier(schema['$ref'].rsplit('/', 1)[-1])
    if 'const' in schema:
        return json.dumps(schema['const'], ensure_ascii=False)
    if 'enum' in schema:
        return ' | '.join(json.dumps(value, ensure_ascii=False) for value in schema['enum'])
    for keyword, joiner in (('anyOf', ' | '), ('oneOf', ' | '), ('allOf', ' & ')):
        if keyword in schema:
            return '(' + joiner.join(typescript(item) for item in schema[keyword]) + ')'
    kind = schema.get('type')
    if kind == 'null':
        return 'null'
    if kind == 'string':
        return 'string'
    if kind in ('integer', 'number'):
        return 'number'
    if kind == 'boolean':
        return 'boolean'
    if kind == 'array':
        if 'prefixItems' in schema:
            return '[' + ', '.join(typescript(item) for item in schema['prefixItems']) + ']'
        return 'Array<' + typescript(schema.get('items', {})) + '>'
    if kind == 'object' or 'properties' in schema:
        properties = schema.get('properties', {})
        required = set(schema.get('required', []))
        fields = [json.dumps(key) + ('' if key in required else '?') + ': ' + typescript(item) + ';'
                  for key, item in properties.items()]
        extra = schema.get('additionalProperties', True)
        if not fields:
            return 'Record<string, ' + (typescript(extra) if isinstance(extra, dict) else 'unknown') + '>'
        if extra is not False:
            fields.append('[key: string]: ' + (typescript(extra) if isinstance(extra, dict) else 'unknown') + ';')
        return '{\n  ' + '\n  '.join(fields) + '\n}'
    return 'unknown'


def exports():
    from app.main import create_app
    schema = create_app().openapi()
    components = schema['components']['schemas']
    selected = {path: item for path, item in schema['paths'].items() if path.startswith('/api/investigations')}
    names = set()
    def visit(value):
        if isinstance(value, dict):
            ref = value.get('$ref', '')
            if ref.startswith('#/components/schemas/'):
                name = ref.rsplit('/', 1)[-1]
                if name not in names:
                    names.add(name)
                    visit(components[name])
            for key, child in value.items():
                if key != '$ref':
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(selected)
    assert len({identifier(name) for name in names}) == len(names)
    security_names = {name for path_item in selected.values() for method, operation in path_item.items()
                      if method in METHODS for requirement in operation.get('security', []) for name in requirement}
    contract = {'openapi': schema['openapi'], 'info': schema['info'],
                'x-contract-origin': 'ACTUAL_HTTP_REQUEST_AND_RESPONSE_MODELS', 'paths': selected,
                'components': {'schemas': {name: components[name] for name in sorted(names)},
                               'securitySchemes': {name: schema['components']['securitySchemes'][name]
                                                   for name in sorted(security_names)}}}
    declaration = '/** Generated from live FastAPI OpenAPI. UUID/date-time are strings; not internal service DTOs. */\n'
    for name in sorted(names):
        declaration += '\nexport type ' + identifier(name) + ' = ' + typescript(components[name]) + ';\n'
    declaration += '\nexport type Overall = InvestigationStatusResponse["overall_status"];\n'
    declaration += 'export type Stage = InvestigationStatusResponse["current_stage"];\n'
    client = (ROOT / 'frontend/contracts/investigations.ts').read_text(encoding='utf-8').replace(
        '../../docs/frontend-contracts/investigation-http.js', './investigation-http.js')
    result = {}
    for folder in FOLDERS:
        result[folder / 'openapi.json'] = schema
        result[folder / 'investigation-http.openapi.json'] = contract
        result[folder / 'investigation-http.d.ts'] = declaration
        result[folder / 'investigation-client.ts'] = client
        inventory = json.loads((folder / 'http-apis.json').read_text(encoding='utf-8'))
        by_operation = {(item['url'], item['method'].lower()): item for item in inventory['operations']}
        operations = []
        for path, item in schema['paths'].items():
            for method, operation in item.items():
                if method not in METHODS:
                    continue
                previous = by_operation.get((path, method), {})
                success_code = next(code for code in operation['responses'] if code.startswith('2'))
                success_schema = operation['responses'][success_code]['content']['application/json']['schema']
                updated = {**previous, 'api_status': 'AVAILABLE',
                    'browser_access': 'AVAILABLE' if path.startswith(('/api/investigations','/api/v1/intelligence')) else previous.get('browser_access', 'UNKNOWN'),
                    'method': method.upper(), 'url': path,
                    'request': {**previous.get('request', {}), 'parameters': operation.get('parameters', []),
                                'body_schema': operation.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema')},
                    'response': {**previous.get('response', {}), 'success_http_status': int(success_code),
                                 'openapi_success_schema': success_schema},
                    'response_validation': 'STRICT_PYDANTIC' if path.startswith(('/api/investigations','/api/v1/intelligence')) else 'LEGACY_DESCRIPTION_ONLY'}
                if path.startswith('/api/v1/intelligence'):
                    updated.update(permissions='Bearer / actor-owned assets and investigations' if path.endswith(('/assets','/graph','/graph/query')) else 'Public intelligence only; no private inventory',
                        source='backend/app/api/intelligence.py')
                if path.startswith('/api/investigations'):
                    updated.update(permissions='Bearer / server-side owner', source='backend/app/api/investigations.py',
                                   errors={code: 'ApiError' for code in operation['responses'] if not code.startswith('2')})
                operations.append(updated)
        result[folder / 'http-apis.json'] = {**inventory, 'operations': operations}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = exports()
    for path, value in result.items():
        content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != content:
                raise SystemExit('STALE_HTTP_CONTRACT: ' + str(path.relative_to(ROOT)))
        else:
            path.write_text(content, encoding='utf-8', newline='\n')
    print(json.dumps({'status': 'PASS', 'mode': 'check' if args.check else 'export',
                      'files': len(result), 'database_connected': False}))


if __name__ == '__main__':
    main()
