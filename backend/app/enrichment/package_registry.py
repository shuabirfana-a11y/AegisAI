"""Registry identity context, never a vulnerability or installed-patch verdict."""
import re
from urllib.parse import urlsplit
from packaging.utils import canonicalize_name
from packaging.version import Version, InvalidVersion
from app.db import models as m
from app.enrichment.evidence import EvidenceService
from app.enrichment.enrichers.base import failure


def registry_snapshot(payload, expected_name):
    if not isinstance(payload, dict) or not isinstance(payload.get('info'), dict):
        raise ValueError('Registry project metadata required')
    info = payload['info']; name = info.get('name'); version = info.get('version')
    if (not isinstance(name, str) or not name or len(name) > 200 or
            canonicalize_name(name) != canonicalize_name(expected_name)):
        raise ValueError('Registry distribution identity mismatch')
    try:
        if not isinstance(version, str) or len(version) > 100: raise ValueError('Registry version required')
        Version(version)
    except InvalidVersion:
        raise ValueError('Invalid registry version') from None
    releases = payload.get('releases')
    if not isinstance(releases, dict): raise ValueError('Registry release index required')
    project_urls = info.get('project_urls') or {}
    if not isinstance(project_urls, dict): raise ValueError('Invalid project URLs')
    repository = None
    candidate = project_urls.get('Repository') or project_urls.get('Source')
    if isinstance(candidate, str):
        p = urlsplit(candidate)
        if (p.scheme == 'https' and p.netloc == 'github.com' and not p.query and not p.fragment
                and re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?', p.path)):
            repository = p.path.strip('/')
    versions = []
    for value, files in releases.items():
        if not isinstance(value, str) or len(value) > 100 or not isinstance(files, list):
            raise ValueError('Invalid release index')
        try: Version(value)
        except InvalidVersion: continue
        versions.append(value)
    versions.sort(key=Version)
    kept = versions[-512:]
    return {'ecosystem': 'PyPI', 'package': canonicalize_name(name), 'original_name': name,
        'registry_version': version, 'project_repository': repository,
        'project_url': 'https://pypi.org/project/' + canonicalize_name(name) + '/',
        'release_versions': kept, 'release_count': len(versions),
        'release_versions_omitted': len(versions) - len(kept),
        # PyPI JSON does not publish a project-metadata modification timestamp.
        'metadata_updated_at': None, 'scope': 'IDENTITY_AND_RELEASES_ONLY'}


def attach_registry_metadata(ctx, session, out, acq):
    """Attach neutral raw-backed context to already source-backed package Claims.

    Neutral stance is intentional: publishing a release or listing an upstream
    repository cannot support an AFFECTS_VERSION or FIXED_VERSION assertion.
    No package alias, impact Claim or verification decision is manufactured.
    """
    start = len(acq.checked)
    claims = [session.get(m.Claim, cid) for cid in dict.fromkeys(out.claims)]
    for package in [p for p in ctx.packages if p.get('ecosystem') == 'PyPI'][:3]:
        bound = [c for c in claims if c is not None and c.vulnerability_id == ctx.target_id
            and c.package_identifier_id == package['package_id']
            and c.claim_type in ('AFFECTS_PRODUCT', 'AFFECTS_VERSION', 'FIXED_VERSION')
            and c.value_json.get('package') == package['name']
            and c.value_json.get('ecosystem') == 'PyPI']
        if not bound: continue
        name = canonicalize_name(package['name'])
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', name):
            out.unresolved.append('Registry package name unsupported'); continue
        try:
            doc = acq.fetch('PYPI_METADATA', f'https://pypi.org/pypi/{name}/json',
                'PyPI:' + name, 'pypi:' + name)
            snapshot = registry_snapshot(doc.payload, package['name'])
        except Exception as exc:
            out.errors.append(failure(exc, 'PYPI_METADATA'))
            out.unresolved.append('Registry metadata unavailable or inconsistent; no identity inferred')
            continue
        obs = session.get(m.SourceObservation, doc.observation_id)
        evidence_ids = []
        for claim in bound:
            for locator, fields in [('/info', ('original_name', 'project_repository', 'project_url')),
                    ('/releases', ('registry_version', 'release_versions', 'release_count', 'release_versions_omitted'))]:
                value = {k: snapshot[k] for k in ('ecosystem', 'package', 'scope', *fields)}
                evidence = EvidenceService.add(session, claim, obs, value,
                    {'json_pointer': locator}, stance='neutral', explicit=False,
                    evidence_type='package_registry_metadata',
                    details={'registry_scope': snapshot['scope'], 'inference': False,
                        'release_publication_is_not_vulnerability_impact': True,
                        'metadata': snapshot, 'package_identifier_id': str(package['package_id'])})
                evidence_ids.append(str(evidence.id)); out.evidence.append(evidence.id)
        out.artifacts.setdefault('package_registry', []).append({**snapshot,
            'source_id': str(doc.source_id), 'raw_document_id': str(doc.raw_id),
            'observation_id': str(doc.observation_id), 'reference': doc.url,
            'collected_at': doc.retrieved_at.isoformat(), 'evidence_ids': evidence_ids,
            'claim_ids': [str(c.id) for c in bound], 'match_method': 'EXACT_DISTRIBUTION',
            'upstream_relation': 'DECLARED_REPOSITORY' if snapshot['project_repository'] else None,
            'impact_verification': 'NOT_ASSERTED_BY_REGISTRY'})
    out.checked.extend(acq.checked[start:])
    if out.errors: out.status = 'PARTIAL' if out.claims else 'FAILED'
