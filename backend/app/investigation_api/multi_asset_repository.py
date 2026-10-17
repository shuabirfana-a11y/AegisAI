"""Owner-scoped durable batch adapter using the existing audit store and locks."""
from datetime import timedelta
from uuid import UUID, uuid4
from sqlalchemy import select, or_, cast, literal
from sqlalchemy.dialects.postgresql import JSONPATH
from app.db import models as m
from app.db.session import transaction
from app.assets.inventory import owned_asset
from app.enrichment.repository import lock
from app.agents.contracts import fingerprint
from app.assistant.storage import IdempotencyConflict
from app.investigation_api.errors import ApiFailure
from app.investigation_api.multi_asset_schemas import (
    BatchRequest, BatchRecord, BatchResponse, BatchSnapshot, InventoryComponent, BatchItem, CandidateRelations,
)
from app.investigation_api.multi_asset_projection import summarize
from app.knowledge.security_graph import build_security_graph
from app.utils.time import utcnow

TYPE='multi-asset-investigation-v1'
NS='multi_asset_v1'
TERMINAL=frozenset({'COMPLETED','CANCELLED','TIMED_OUT','FAILED'})


def normalized_request(request):
    request=BatchRequest.model_validate_json(request.model_dump_json())
    data=request.model_dump(mode='json',exclude={'idempotency_key'})
    data['asset_ids']=sorted(set(data['asset_ids']))
    return data


def snapshot(db,asset_id,actor,*,selected=None):
    asset=owned_asset(db,asset_id,actor)
    rows=list(db.scalars(select(m.AssetComponent).where(m.AssetComponent.asset_id==asset_id,
        m.AssetComponent.deleted_at.is_(None)).order_by(m.AssetComponent.id).limit(101)))
    if len(rows)>100:raise ApiFailure('INVENTORY_LIMIT','资产组件超过本轮处理上限。',status=422)
    components=[]
    for c in rows:
        pkg=db.get(m.PackageIdentifier,c.package_identifier_id) if c.package_identifier_id else None
        components.append(InventoryComponent(component_id=c.id,product_id=c.product_id,
            package_identifier_id=c.package_identifier_id,name=c.raw_package_name,
            package_name=pkg.package_name if pkg else None,ecosystem=pkg.ecosystem if pkg else c.ecosystem or 'unknown',
            namespace=pkg.namespace if pkg else c.namespace or '',purl=c.purl,
            version=c.version,inventory_revision=c.inventory_revision,source=c.source,identity_status=c.identity_status))
    raw=dict(asset_id=asset.id,asset_name=asset.name,environment=asset.environment,exposure=asset.exposure,
             is_demo=asset.is_demo,components=tuple(components))
    return BatchSnapshot(**raw,captured_at=utcnow(),selected_component_id=selected,
        inventory_hash=fingerprint({**raw,'asset_id':str(asset.id),'components':[c.model_dump(mode='json') for c in components]}))


class BatchRepository:
    def __init__(self,engine,*,max_assets=5):
        self.engine=engine;self.max_assets=max_assets

    def _decode(self,row,actor):
        if row is None or row.agent_type!=TYPE or row.actor_principal!=actor:raise LookupError('Batch unavailable')
        ns=(row.details or {}).get(NS,{})
        if ns.get('hash')!=fingerprint(ns.get('payload')):raise ValueError('BATCH_INTEGRITY_INVALID')
        result=BatchRecord.model_validate(ns['payload'])
        if result.owner!=actor or result.response.batch_id!=row.id or result.request_hash!=fingerprint(normalized_request(result.request)):
            raise ValueError('BATCH_BINDING_INVALID')
        if (result.response.vulnerability_id!=result.request.vulnerability_id or
            result.response.deadline_at!=result.response.created_at+timedelta(seconds=result.request.timeout_seconds)):
            raise ValueError('BATCH_REQUEST_BINDING_INVALID')
        ids=tuple(x.snapshot.asset_id for x in result.response.items)
        if tuple(sorted(ids,key=str))!=tuple(sorted(set(result.request.asset_ids),key=str)):
            raise ValueError('BATCH_SCOPE_INVALID')
        for item in result.response.items:
            if item.execution_status!='COMPLETED' and (item.impact!='UNKNOWN' or item.risk_level!='UNKNOWN' or
                item.priority!='REVIEW_REQUIRED' or item.recommended_actions):
                raise ValueError('BATCH_NONFINAL_DECISION_INVALID')
            if item.investigation_id is None and (
                item.execution_status=='COMPLETED' or item.impact!='UNKNOWN' or item.risk_level!='UNKNOWN' or
                item.priority!='REVIEW_REQUIRED' or item.gate_status is not None or item.artifact_references or
                item.integration_result_id or item.answer_id or item.planner_run_id or item.evidence_ids or
                item.claim_ids or item.citations or item.recommended_actions):
                raise ValueError('BATCH_UNBOUND_DECISION_INVALID')
            raw=item.snapshot.model_dump(mode='json',exclude={'captured_at','inventory_hash','selected_component_id','criticality','provenance'})
            if fingerprint(raw)!=item.snapshot.inventory_hash:raise ValueError('BATCH_SNAPSHOT_INVALID')
            if item.child_request_key!=f'batch:{row.id}:asset:{item.snapshot.asset_id}':
                raise ValueError('BATCH_CHILD_KEY_INVALID')
        if result.response.summary!=summarize(result.response.items):raise ValueError('BATCH_SUMMARY_INVALID')
        return result

    def _save(self,row,record):
        if record.response.execution_status in TERMINAL and record.response.finished_at is None:
            record.response.finished_at=utcnow()
        record=BatchRecord.model_validate_json(record.model_dump_json())
        payload=record.model_dump(mode='json')
        from app.runtime.contracts import json_bytes
        json_bytes(payload,4*1024*1024)
        row.details={NS:{'payload':payload,'hash':fingerprint(payload)}}
        r=record.response
        row.status=({'COMPLETED':'partial' if r.summary.unresolved_asset_ids else 'succeeded',
                     'CANCELLED':'cancelled','TIMED_OUT':'timeout','FAILED':'failed'}.get(r.execution_status,'running'))
        row.finished_at=r.finished_at
        return record

    def by_key(self,actor,key):
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==actor,
                m.AgentRun.details[NS]['payload']['request_key'].astext==key))
            return self._decode(row,actor) if row else None

    def read(self,id,actor):
        with transaction(self.engine) as db:
            record=self._decode(db.get(m.AgentRun,id),actor)
            # Server owner scope is rechecked without replacing the saved inventory.
            for item in record.response.items:owned_asset(db,item.snapshot.asset_id,actor)
            return record

    def mutate(self,id,actor,fn):
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==id).with_for_update())
            record=self._decode(row,actor)
            fn(record)
            record.response.summary=summarize(record.response.items)
            if record.response.cancel_requested_at and record.response.execution_status in TERMINAL:
                record.response.cancellation_observed=not any(i.execution_status=='RUNNING' for i in record.response.items)
            record.response.updated_at=utcnow();record.response.revision+=1
            return self._save(row,record)

    def create(self,request,key,actor,provider,model):
        data=normalized_request(request);digest=fingerprint(data)
        if len(data['asset_ids'])>self.max_assets:
            raise ApiFailure('ASSET_LIMIT_EXCEEDED','所选资产超过本轮上限，请缩小明确范围。',status=422)
        with transaction(self.engine) as db:
            lock(db,'multi-asset-create')
            target=db.get(m.Vulnerability,UUID(request.vulnerability_id)) if not request.vulnerability_id.startswith('CVE-') else db.scalar(
                select(m.Vulnerability).where(m.Vulnerability.canonical_id==request.vulnerability_id))
            if target is None:raise LookupError('Vulnerability unavailable')
            if not target.canonical_id.startswith('CVE-'):
                raise ApiFailure('TARGET_SCOPE_UNSUPPORTED','本轮需要已入库的明确 CVE 漏洞。',status=422)
            request=request.model_copy(update={'vulnerability_id':target.canonical_id})
            data=normalized_request(request);digest=fingerprint(data)
            old=db.scalar(select(m.AgentRun).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==actor,
                m.AgentRun.details[NS]['payload']['request_key'].astext==key))
            if old:
                record=self._decode(old,actor)
                if record.request_hash!=digest:raise IdempotencyConflict('Different batch scope')
                for i in record.response.items:owned_asset(db,i.snapshot.asset_id,actor)
                return record,False
            # Validate the complete scope before any child work or batch allocation.
            snapshots=[snapshot(db,UUID(id),actor) for id in data['asset_ids']]
            pending_child=m.AgentRun.details.op('@?')(cast(literal(
                '$.multi_asset_v1.payload.response.items[*] ? (@.execution_status == "RUNNING")'),JSONPATH))
            active=db.scalar(select(m.AgentRun.id).where(m.AgentRun.agent_type==TYPE,
                or_(m.AgentRun.finished_at.is_(None),pending_child)).limit(1))
            if active:raise ApiFailure('BATCH_BUSY','已有批次执行中，请稍后重试。',status=429,retryable=True)
            package_ids=set(db.scalars(select(m.AffectedVersionRange.package_identifier_id).where(
                m.AffectedVersionRange.vulnerability_id==target.id,m.AffectedVersionRange.package_identifier_id.is_not(None))))
            package_ids.update(db.scalars(select(m.Claim.package_identifier_id).where(
                m.Claim.vulnerability_id==target.id,m.Claim.package_identifier_id.is_not(None))))
            id=uuid4();items=[]
            for snap in snapshots:
                matching=[c for c in snap.components if c.package_identifier_id in package_ids]
                candidates=matching if matching else list(snap.components)
                selected=candidates[0] if len(candidates)==1 else None
                snap.selected_component_id=selected.component_id if selected else None
                graph=build_security_graph(db,str(target.id),actor,include_assets=True,asset_id=snap.asset_id)
                relations=CandidateRelations(node_ids=tuple(n.id for n in graph.nodes),edge_ids=tuple(e.id for e in graph.edges),
                    truncated=graph.truncated,warnings=graph.warnings)
                missing=[]
                if selected is None:missing.append('component')
                elif not selected.version or selected.version.strip().casefold() in ('unknown','未知'):missing.append('version')
                elif not selected.package_name or not selected.name:missing.append('component_identity')
                items.append(BatchItem(snapshot=snap,relations=relations,
                    child_request_key=f'batch:{id}:asset:{snap.asset_id}',
                    execution_status='NEED_CONTEXT' if missing else 'NOT_STARTED',missing_fields=tuple(missing)))
            now=utcnow()
            response=BatchResponse(batch_id=id,vulnerability_id=target.canonical_id,execution_status='QUEUED',
                items=tuple(items),summary=summarize(items),created_at=now,updated_at=now,
                deadline_at=now+timedelta(seconds=request.timeout_seconds),max_assets=self.max_assets,
                duplicate_asset_count=len(request.asset_ids)-len(items),
                warnings=('DUPLICATE_ASSETS_REMOVED',) if len(items)!=len(request.asset_ids) else (),
                model_provider=provider,model_name=model,execution_mode='MOCK' if provider=='mock' else 'REAL')
            record=BatchRecord(owner=actor,request_key=key,request_hash=digest,request=request,response=response)
            row=m.AgentRun(id=id,actor_principal=actor,user_request='Batch investigation '+target.canonical_id,
                agent_type=TYPE,started_at=now,status='running')
            db.add(row);self._save(row,record);db.flush()
            return record,True
