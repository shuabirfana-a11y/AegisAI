"""Exact package identity is authoritative; display labels are never fuzzy identifiers."""
from uuid import UUID
from sqlalchemy import select,func
from packageurl import PackageURL
from packaging.utils import canonicalize_name
from packaging.version import Version,InvalidVersion
from app.db import models as m
from app.services.products import registry
from app.assets.contracts import ComponentInput

ECO_TYPES={'pypi':'PyPI','npm':'npm','maven':'Maven','nuget':'NuGet','gem':'RubyGems','golang':'Go'}

def _name(name,eco):return canonicalize_name(name) if eco=='PyPI' else name

def _same_version(a,b,eco):
    if eco=='PyPI':
        try:return Version(a)==Version(b)
        except InvalidVersion:return a==b
    return a==b

def resolve_component(session,value):
    data=ComponentInput.model_validate(value).model_dump()
    eco=data['ecosystem'];name=data['package_name'];namespace=data['namespace'];purl=data['purl']
    normalized_purl=None;version=data['version'];method=None;candidates=[]
    if purl:
        try:parsed=PackageURL.from_string(purl)
        except ValueError as exc:raise ValueError('PURL invalid') from exc
        pe=ECO_TYPES.get(parsed.type,parsed.type)
        if eco is not None and eco!=pe:raise ValueError('PURL ecosystem mismatch')
        if name is not None and _name(name,pe)!=_name(parsed.name,pe):raise ValueError('PURL package mismatch')
        if namespace and namespace!=(parsed.namespace or ''):raise ValueError('PURL namespace mismatch')
        if parsed.version and version and not _same_version(parsed.version,version,pe):raise ValueError('PURL version mismatch')
        eco=pe;name=_name(parsed.name,eco);namespace=parsed.namespace or '';version=version or parsed.version
        normalized_purl=str(PackageURL(type=parsed.type,namespace=parsed.namespace,name=name,version=parsed.version,qualifiers=parsed.qualifiers,subpath=parsed.subpath))
        # A qualifier/subpath-specific identity is not silently equated to another distribution.
        base=str(PackageURL(type=parsed.type,namespace=parsed.namespace,name=name))
        if parsed.qualifiers or parsed.subpath:
            candidates=list(session.scalars(select(m.PackageIdentifier).where(m.PackageIdentifier.purl==normalized_purl)))
        else:candidates=list(session.scalars(select(m.PackageIdentifier).where(m.PackageIdentifier.purl==base)))
        method='PURL_EXACT'
    if data['package_identifier_id']:
        pkg=session.get(m.PackageIdentifier,data['package_identifier_id'])
        if pkg is None:raise ValueError('Package Identifier not found')
        if eco and eco!=pkg.ecosystem or name and _name(name,pkg.ecosystem)!=pkg.package_name or namespace and namespace!=pkg.namespace:
            raise ValueError('Package Identifier mismatch')
        if purl and (not candidates or pkg.id not in [p.id for p in candidates]):raise ValueError('PURL Identifier mismatch')
        candidates=[pkg];method=method or 'PACKAGE_IDENTIFIER';eco=pkg.ecosystem;name=pkg.package_name;namespace=pkg.namespace
    if not purl and not candidates and eco:
        name=_name(name or data['name'],eco)
        candidates=list(session.scalars(select(m.PackageIdentifier).where(m.PackageIdentifier.ecosystem==eco,m.PackageIdentifier.package_name==name,m.PackageIdentifier.namespace==namespace)))
        method='ECOSYSTEM_PACKAGE'
    if not purl and not candidates and not eco and not name:
        alias=data['name'].strip().casefold()
        ids=set(session.scalars(select(m.ProductAlias.product_id).where(m.ProductAlias.normalized_alias==alias,m.ProductAlias.verification_status=='confirmed')))
        # Reviewed explicit registry names; unqualified Ray/Ollama/Triton remain unresolved.
        known=[x for x in registry()['products'] if alias in x['aliases']]
        for entry in known:
            ids.update(session.scalars(select(m.Product.id).where(m.Product.canonical_key=='ai:'+entry['key'])))
            ids.update(session.scalars(select(m.Product.id).where(func.lower(m.Product.canonical_name)==entry['name'].casefold())))
        if ids:candidates=list(session.scalars(select(m.PackageIdentifier).where(m.PackageIdentifier.product_id.in_(ids))))
        method='PRODUCT_ALIAS'
    candidates=[p for p in candidates if session.get(m.Product,p.product_id).deleted_at is None]
    if len(candidates)==1:
        pkg=candidates[0];product=session.get(m.Product,pkg.product_id)
        return {'status':'RESOLVED','method':method,'product_id':product.id,'package_identifier_id':pkg.id,
            'matched_product':product.canonical_name,'matched_identifier':pkg.purl,'ecosystem':pkg.ecosystem,
            'package_name':pkg.package_name,'namespace':pkg.namespace,'purl':normalized_purl or pkg.purl,'version':version,
            'reason_summary':'Exactly one explicit distribution identity matched'}
    return {'status':'AMBIGUOUS' if candidates else 'UNRESOLVED','method':method or 'NONE','product_id':None,'package_identifier_id':None,
        'matched_product':None,'matched_identifier':None,'ecosystem':eco or 'unknown','package_name':name or data['name'],
        'namespace':namespace,'purl':normalized_purl,'version':version,'reason_summary':'Multiple explicit identities require selection' if candidates else 'No exact supported identity found',
        'candidates':[str(p.id) for p in candidates]}
