"""Describe existing legacy wire shapes without changing their serialization.

Legacy handlers still accept/return the exact same values. JSON extension columns
remain open objects; x-response-validation makes this compatibility limit explicit.
"""
from copy import deepcopy
from fastapi.openapi.utils import get_openapi
from sqlalchemy import inspect
from sqlalchemy import types as t
from app.db import models as m
from app.tooling.contracts import ToolEnvelope


def row(model, **extras):
    properties = {}
    for column in inspect(model).columns:
        if column.key in ('details', 'metadata', 'raw_payload', 'payload', 'request_hash'):
            continue
        kind = column.type
        if isinstance(kind, t.Uuid):
            shape = {'type': 'string', 'format': 'uuid'}
        elif isinstance(kind, t.DateTime):
            shape = {'type': 'string', 'format': 'date-time'}
        elif isinstance(kind, t.Date):
            shape = {'type': 'string', 'format': 'date'}
        elif isinstance(kind, t.Boolean):
            shape = {'type': 'boolean'}
        elif isinstance(kind, t.Integer):
            shape = {'type': 'integer'}
        elif isinstance(kind, (t.Numeric, t.Float)):
            shape = {'type': 'number'}
        elif isinstance(kind, t.JSON):
            shape = {}
        else:
            shape = {'type': 'string'}
        if column.nullable:
            shape = {'anyOf': [shape, {'type': 'null'}]}
        properties[column.key] = shape
    properties.update(extras)
    return obj(properties)


def obj(properties, required=()):
    return {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': True}


def array(shape):
    return {'type': 'array', 'items': shape}


def page(shape, **extras):
    return obj({'items': array(shape), 'total': {'type': 'integer', 'minimum': 0},
                'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1}, **extras},
               ('items', 'total', 'offset', 'limit'))


def legacy_shape(path, method):
    uuid = {'type': 'string', 'format': 'uuid'}
    date = {'type': 'string', 'format': 'date-time'}
    nullable = lambda shape: {'anyOf': [shape, {'type': 'null'}]}
    unknown = obj({})
    string = {'type': 'string'}
    if path == '/health':
        return obj({'application': {'const': 'up'}, 'database': {'enum': ['up', 'down']},
                    'sources': string, 'scope': {'const': 'local development'}}, ('application', 'database', 'sources', 'scope'))
    if path == '/api/v1/sources':
        return obj({'items': array(row(m.Source, last_sync=nullable(uuid), latest_error=nullable(string), records=unknown)),
                    'total': {'type': 'integer'}, 'status_semantics': string}, ('items', 'total', 'status_semantics'))
    if path == '/api/v1/sync-runs':
        return page(row(m.SyncRun))
    if path == '/api/v1/vulnerabilities':
        return page(row(m.Vulnerability), data_status=string, coverage=string)
    if path == '/api/v1/vulnerabilities/{id}':
        return row(m.Vulnerability, **{key: array(unknown) for key in (
            'source_variants', 'source_documents', 'external_identifiers', 'affected_versions', 'cvss_assessments',
            'products', 'cwe', 'references', 'ai_relevance', 'enrichment', 'claims', 'evidence', 'pocs',
            'patches', 'timeline', 'epss', 'known_exploitation', 'conflicts', 'verification_results', 'reviews')})
    if path.startswith('/api/v1/vulnerabilities/{id}/'):
        models = {'enrichment': m.EnrichmentJob, 'claims': m.Claim, 'evidence': m.Evidence,
                  'pocs': m.PocCandidate, 'patches': m.PatchCandidate, 'timeline': m.IntelligenceEvent}
        return page(row(models[path.rsplit('/', 1)[-1]]), content_trust_level={'const': 'UNTRUSTED_EXTERNAL_CONTENT'})
    if path == '/api/v1/evidence/{id}':
        return row(m.Evidence, claim_verification_status=string, source_key=string)
    if path == '/api/v1/reviews':
        return page(row(m.ReviewTask))
    if path == '/api/v1/reviews/{id}':
        return row(m.ReviewTask, claim=row(m.Claim), evidence=array(row(m.Evidence)), audit=array(row(m.AuditLog)))
    if path == '/api/v1/reviews/{id}/resolve':
        return row(m.AuditLog)
    if path == '/api/v1/assets/overview':
        names = ('assets', 'components', 'affected_components', 'critical_high', 'confirmed_poc', 'kev',
                 'patch_available', 'uncertain_matches', 'not_evaluated_components')
        return obj({**{name: {'type': 'integer'} for name in names}, 'is_demo_inventory_included': {'type': 'boolean'},
                    'counts_unit': string}, names)
    if path == '/api/v1/assets':
        return page(row(m.Asset)) if method == 'get' else row(m.Asset)
    if path.endswith('/components') or '/components/{component_id}' in path:
        return row(m.AssetComponent)
    if path.endswith('/sbom'):
        return obj({'format': {'enum': ['CycloneDX', 'SPDX']}, 'sha256': string,
                    **{key: {'type': 'integer'} for key in ('added', 'updated', 'removed', 'component_count')},
                    **{key: array(uuid) for key in ('added_ids', 'updated_ids', 'removed_ids')}})
    if path.endswith('/recompute'):
        return obj({'items': array(unknown)}, ('items',))
    if path.endswith('/risk-changes'):
        return page(row(m.AssetRiskChange))
    if path.endswith('/inventory-history'):
        return page(row(m.AssetInventoryEvent, changes={}, summary=unknown))
    if path.startswith('/api/v1/assets/'):
        if path.endswith('/risks'):
            return page(unknown, coverage=string)
        if path.endswith('/reviews'):
            return page(row(m.ReviewTask))
        if '/risks/' in path:
            return obj({'asset_id': uuid, 'snapshot_id': uuid, 'historical': {'const': True}})
        return row(m.Asset, components=array(row(m.AssetComponent)))
    if path == '/api/v1/assistant/runs/{id}/tasks':
        return obj({'items': array(unknown)}, ('items',))
    if path == '/api/v1/assistant/runs/{id}/trace':
        return obj({'run_id': uuid, 'trace_id': uuid, 'items': array(unknown), 'events': array(unknown), 'disclosure': string}, ('run_id', 'trace_id', 'items', 'events', 'disclosure'))
    if path.startswith('/api/v1/assistant/'):
        return obj({'run_id': uuid, 'trace_id': uuid, 'status': {'enum': ['PLANNING', 'RUNNING', 'WAITING_TOOL', 'VERIFYING', 'REPLANNING', 'WAITING_REVIEW', 'COMPLETED', 'FAILED']},
            'route': nullable(unknown), 'result': nullable(unknown), 'warnings': array(string),
            'started_at': date, 'finished_at': nullable(date), 'duration_ms': nullable({'type': 'number'})}, ('run_id', 'trace_id', 'status', 'warnings', 'started_at'))
    if path == '/api/v1/tools/contracts':
        return obj({'version': {'const': 'ToolContractV3'}, 'content_trust_level': {'const': 'UNTRUSTED_EXTERNAL_CONTENT'},
            'tools': array(obj({'name': string, 'input_schema': unknown, 'permission': string, 'category': string, 'description': string},
                               ('name', 'input_schema', 'permission', 'category', 'description')))}, ('version', 'content_trust_level', 'tools'))
    if path == '/api/v1/tools/{name}':
        return ToolEnvelope.model_json_schema()
    raise ValueError('Unmapped legacy HTTP operation')


def install_openapi(application):
    def openapi():
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(title=application.title, version=application.version, routes=application.routes)
        for path, item in schema['paths'].items():
            if path.startswith(('/api/investigations','/api/v1/intelligence')):
                continue
            for method, operation in item.items():
                if method not in ('get', 'post', 'patch', 'delete', 'put'):
                    continue
                shape = legacy_shape(path, method)
                for code, response in operation['responses'].items():
                    if code.startswith('2') or (path == '/health' and code == '503'):
                        response.setdefault('content', {}).setdefault('application/json', {})['schema'] = deepcopy(shape)
                operation['x-response-validation'] = 'LEGACY_DESCRIPTION_ONLY; wire behavior unchanged; extension fields open'
        application.openapi_schema = schema
        return schema
    application.openapi = openapi
