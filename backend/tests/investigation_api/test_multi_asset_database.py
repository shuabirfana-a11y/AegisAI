"""Real PostgreSQL batch scope, idempotency and saved snapshot tests."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from app.assistant.storage import IdempotencyConflict
from app.investigation_api.multi_asset_schemas import BatchRequest
from app.investigation_api.multi_asset_repository import BatchRepository
from tests.orchestration.fixtures import scenario


def setup_batch(engine, mode='complete'):
    seed,_,gateway,_,_=scenario(engine,mode)
    with transaction(engine) as db:
        asset=m.Asset(name='SYNTHETIC second inventory',asset_type='service',owner_principal=seed.actor,is_demo=True)
        db.add(asset);db.flush()
        c=m.AssetComponent(asset_id=asset.id,package_identifier_id=seed.package_id,
            raw_package_name=seed.component['package_name'],version='0.7.0',ecosystem='PyPI',source='manual',identity_status='resolved')
        db.add(c);db.flush();seed.second_asset_id=asset.id;seed.second_component_id=c.id
    return seed,gateway


def test_scope_is_atomic_and_does_not_allocate_a_partial_batch(engine):
    seed,gw=setup_batch(engine)
    repo=BatchRepository(engine,max_assets=5)
    key='batch-test-'+uuid4().hex
    try:
        with pytest.raises(LookupError):
            repo.create(BatchRequest(vulnerability_id=seed.cve,asset_ids=[seed.asset_id,uuid4()]),key,seed.actor,'mock','test')
        assert repo.by_key(seed.actor,key) is None
    finally:gw.close()


def test_concurrent_retries_deduplicate_order_and_keep_original_snapshot(engine):
    seed,gw=setup_batch(engine);repo=BatchRepository(engine,max_assets=5);key='batch-test-'+uuid4().hex
    a=BatchRequest(vulnerability_id=seed.cve,asset_ids=[seed.asset_id,seed.second_asset_id,seed.asset_id])
    b=BatchRequest(vulnerability_id=seed.cve,asset_ids=[seed.second_asset_id,seed.asset_id])
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            records=list(pool.map(lambda req:repo.create(req,key,seed.actor,'mock','test'),[a,b]))
        assert len({x.response.batch_id for x,fresh in records})==1
        assert sum(fresh for x,fresh in records)==1
        saved=records[0][0]
        assert len(saved.response.items)==2
        alias,recreated=repo.create(b.model_copy(update={'vulnerability_id':str(seed.vulnerability_id)}),key,seed.actor,'mock','test')
        assert not recreated and alias.response.batch_id==saved.response.batch_id
        assert alias.request.vulnerability_id==seed.cve
        with transaction(engine) as db:
            c=db.get(m.AssetComponent,seed.component_id);c.version='9.0.0';c.inventory_revision+=1
        reread,_=repo.create(a,key,seed.actor,'mock','test')
        assert {c.version for x in reread.response.items for c in x.snapshot.components}=={'0.6.0','0.7.0'}
        with pytest.raises(IdempotencyConflict):
            repo.create(BatchRequest(vulnerability_id=seed.cve,asset_ids=[seed.asset_id]),key,seed.actor,'mock','test')
        with pytest.raises(LookupError):repo.read(saved.response.batch_id,'SYNTHETIC-other-owner')
    finally:
        repo.mutate(records[0][0].response.batch_id,seed.actor,lambda r:setattr(r.response,'execution_status','CANCELLED'))
        gw.close()


def test_count_limit_applies_after_deduplication(engine):
    seed,gw=setup_batch(engine);repo=BatchRepository(engine,max_assets=1)
    try:
        with pytest.raises(Exception) as error:
            repo.create(BatchRequest(vulnerability_id=seed.cve,asset_ids=[seed.asset_id,seed.second_asset_id]),'limit-'+uuid4().hex,seed.actor,'mock','test')
        assert getattr(error.value,'code',None)=='ASSET_LIMIT_EXCEEDED'
    finally:gw.close()
