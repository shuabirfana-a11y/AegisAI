"""Owner-scoped inventory mutations with atomic imports and explicit version history."""
from hashlib import sha256
from uuid import UUID
from sqlalchemy import select
from packageurl import PackageURL
from app.db import models as m
from app.db.persistence import RevisionConflict,IdempotencyConflict
from app.enrichment.repository import lock,digest
from app.utils.time import utcnow
from app.assets.contracts import AssetInput,ComponentInput,CONTENT_TRUST
from app.assets.identity import resolve_component
from app.assets.versions import normalize_version
from app.assets.sbom import parse_sbom

def owned_asset(session,asset_id,actor):
    asset=session.get(m.Asset,asset_id)
    if asset is None or asset.deleted_at is not None or asset.owner_principal!=actor:raise LookupError('Asset not found')
    return asset

def request_check(key,actor):
    if not isinstance(key,str) or not key.strip() or len(key)>150:raise ValueError('request_key must be 1..150 characters')
    if not actor or len(actor)>150:raise ValueError('Authenticated actor required')

def _prior(session,asset,key,payload):
    row=session.scalar(select(m.AssetInventoryEvent).where(m.AssetInventoryEvent.asset_id==asset.id,m.AssetInventoryEvent.request_key==key))
    if row and row.request_hash!=digest(payload):raise IdempotencyConflict('request_key already used with another body')
    return row

def _event(session,asset,component,actor,key,kind,request,payload):
    row=m.AssetInventoryEvent(asset_id=asset.id,component_id=component.id if component else None,actor=actor,
        request_key=key,request_hash=digest(request),event_type=kind,occurred_at=utcnow(),payload=payload,
        details={'content_trust_level':CONTENT_TRUST})
    session.add(row);session.flush();return row

def _component(session,asset,data,source,key,extra=None):
    r=resolve_component(session,data);n=normalize_version(r['version'],r['ecosystem']);now=utcnow()
    c=m.AssetComponent(asset_id=asset.id,product_id=r['product_id'],package_identifier_id=r['package_identifier_id'],
        raw_package_name=data['name'],version=r['version'],normalized_version=n['normalized'],ecosystem=r['ecosystem'],namespace=r['namespace'],
        purl=r['purl'],source=source,inventory_key=key,identity_status=r['status'].lower(),resolution_method=r['method'],
        first_seen_at=now,last_seen_at=now,details={'resolution':{k:str(v) if isinstance(v,UUID) else v for k,v in r.items()},
            'normalization':n,'content_trust_level':CONTENT_TRUST,**(extra or {})})
    session.add(c);session.flush();return c

def _recompute(session,asset):
    from app.assets.risk import RiskService
    return RiskService.recompute(session,asset.id)

class AssetService:
    @staticmethod
    def create(session,value,actor,request_key):
        request_check(request_key,actor);data=AssetInput.model_validate(value).model_dump()
        lock(session,'asset-create:'+actor+':'+request_key)
        old=session.scalar(select(m.Asset).where(m.Asset.owner_principal==actor,m.Asset.request_key==request_key))
        if old:
            if old.details.get('request_hash')!=digest(data):raise IdempotencyConflict('request_key already used with another body')
            return old
        asset=m.Asset(**data,owner_principal=actor,request_key=request_key,details={'request_hash':digest(data)})
        session.add(asset);session.flush();return asset

    @staticmethod
    def add_component(session,asset_id,value,actor,request_key):
        request_check(request_key,actor);data=ComponentInput.model_validate(value).model_dump(mode='json')
        lock(session,'asset:'+str(asset_id));asset=owned_asset(session,asset_id,actor)
        previous=_prior(session,asset,request_key,data)
        if previous:return session.get(m.AssetComponent,previous.component_id)
        # Manual registrations represent explicit inventory items; retries share their request key.
        c=_component(session,asset,data,'manual','manual:'+digest(request_key))
        _event(session,asset,c,actor,request_key,'COMPONENT_ADDED',data,{'after':{'version':c.version,'revision':1}})
        _recompute(session,asset);return c

    @staticmethod
    def update_component(session,asset_id,component_id,version,expected_revision,actor,request_key):
        request_check(request_key,actor)
        if version is not None and (not isinstance(version,str) or len(version)>200):raise ValueError('Invalid version input')
        lock(session,'asset:'+str(asset_id));asset=owned_asset(session,asset_id,actor)
        request={'component_id':str(component_id),'version':version,'expected_revision':expected_revision}
        prior=_prior(session,asset,request_key,request)
        if prior:return session.get(m.AssetComponent,component_id)
        c=session.get(m.AssetComponent,component_id)
        if c is None or c.asset_id!=asset.id or c.deleted_at is not None:raise LookupError('Component not found')
        if c.inventory_revision!=expected_revision:raise RevisionConflict('Component inventory revision changed')
        before={'version':c.version,'revision':c.inventory_revision}
        if c.version!=version:
            c.version=version;c.inventory_revision+=1;c.normalized_version=normalize_version(version,c.ecosystem)['normalized']
            if c.purl:
                p=PackageURL.from_string(c.purl);c.purl=str(PackageURL(type=p.type,namespace=p.namespace,name=p.name,version=version,qualifiers=p.qualifiers,subpath=p.subpath))
        c.last_seen_at=utcnow();c.details={**c.details,'normalization':normalize_version(version,c.ecosystem)}
        session.flush()
        _event(session,asset,c,actor,request_key,'ASSET_VERSION_CHANGED',request,{'before':before,'after':{'version':c.version,'revision':c.inventory_revision}})
        _recompute(session,asset);return c

    @staticmethod
    def import_sbom(session,asset_id,payload,actor,request_key):
        request_check(request_key,actor);parsed=parse_sbom(payload)
        lock(session,'asset:'+str(asset_id));asset=owned_asset(session,asset_id,actor)
        request={'sbom_sha256':parsed['sha256']};prior=_prior(session,asset,request_key,request)
        if prior:return prior.payload['result']
        # Validate every identity before the first inventory mutation.
        entries=[]
        for entry in parsed['components']:
            data={k:v for k,v in entry.items() if k!='locator'};r=resolve_component(session,data)
            key='sbom:'+digest(entry['source_ref'] or [r['ecosystem'],r['package_name'],r['namespace'],r['purl'].split('@')[0] if r['purl'] else None])
            entries.append((key,data,r,entry['locator']))
        keys=[e[0] for e in entries]
        if len(set(keys))!=len(keys):raise ValueError('Duplicate normalized SBOM inventory identity')
        existing={c.inventory_key:c for c in session.scalars(select(m.AssetComponent).where(m.AssetComponent.asset_id==asset.id,m.AssetComponent.source=='sbom',m.AssetComponent.deleted_at.is_(None)))}
        added=[];updated=[];removed=[];changes=[]
        for key,data,r,locator in entries:
            old=existing.get(key);extra={'sbom_sha256':parsed['sha256'],'sbom_format':parsed['format'],'source_ref':data['source_ref'],'source_locator':locator}
            same_unresolved=old is not None and old.package_identifier_id is None and r['package_identifier_id'] is None and (
                old.raw_package_name==data['name'] and old.ecosystem==r['ecosystem'] and old.namespace==r['namespace'] and
                (old.details.get('resolution',{}).get('package_name') or old.raw_package_name)==r['package_name'])
            if old and (old.package_identifier_id!=r['package_identifier_id'] or old.package_identifier_id is None and not same_unresolved):
                old.deleted_at=utcnow();old.inventory_revision+=1;removed.append(str(old.id));changes.append({'id':str(old.id),'action':'removed','version':old.version,'revision':old.inventory_revision});session.flush();old=None
            if old is None:
                c=_component(session,asset,data,'sbom',key,extra);added.append(str(c.id));changes.append({'id':str(c.id),'action':'added','version':c.version,'revision':1})
            else:
                before={'version':old.version,'revision':old.inventory_revision}
                if old.version!=r['version']:
                    old.version=r['version'];old.inventory_revision+=1;updated.append(str(old.id))
                    changes.append({'id':str(old.id),'action':'updated','before':before,'after':{'version':old.version,'revision':old.inventory_revision}})
                old.purl=r['purl'];old.normalized_version=normalize_version(old.version,old.ecosystem)['normalized'];old.last_seen_at=utcnow()
                old.details={**old.details,**extra,'normalization':normalize_version(old.version,old.ecosystem)}
        for key,old in existing.items():
            if key not in keys:
                old.deleted_at=utcnow();old.inventory_revision+=1;removed.append(str(old.id));changes.append({'id':str(old.id),'action':'removed','version':old.version,'revision':old.inventory_revision})
        result={'format':parsed['format'],'sha256':parsed['sha256'],'added':len(added),'updated':len(updated),'removed':len(removed),
            'added_ids':added,'updated_ids':updated,'removed_ids':removed,'component_count':len(entries),'content_trust_level':CONTENT_TRUST}
        session.flush();_event(session,asset,None,actor,request_key,'SBOM_IMPORTED',request,{'result':result,'changes':changes,'document':parsed['document']})
        _recompute(session,asset);return result
