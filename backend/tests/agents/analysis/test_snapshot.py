"""Breaks caught: mismatched source artifacts, forged receipts and foreign inventory."""
from uuid import uuid4
from datetime import timedelta
import copy
import pytest
from app.utils.time import utcnow
from app.db import models as m
from app.db.session import transaction
from tests.agents.analysis.helpers import module,request


def read(engine,source,**changes):
    return module('snapshot').AnalysisSnapshotReader(engine).read(request(source,**changes),
        actor=source.seed.actor,evaluation_time=utcnow())


def test_verification_source_task_and_hash_must_match(engine,analysis_source):
    src=analysis_source;before=src.investigation.model_dump(mode='json')
    got=read(engine,src)
    assert got.verification.verification_status=='CONFIRMED'
    assert got.asset.deployed_version=='0.6.0' and got.asset.criticality=='unknown'
    assert got.source_claims[0].claim_id==str(src.seed.claim_id) and got.receipt_references
    assert src.original.read_results(src.investigation.run_id,src.seed.actor).artifacts[0].model_dump(mode='json')==before
    with pytest.raises(ValueError,match='INVALID_INPUT_ARTIFACT'):read(engine,src,investigation_task_id='other')


def test_cross_owner_or_artifact_handoff_rejected(engine,analysis_source):
    cls=module('snapshot').AnalysisSnapshotReader(engine)
    with pytest.raises(ValueError,match='INVALID_INPUT_ARTIFACT'):
        cls.read(request(analysis_source),actor='foreign',evaluation_time=utcnow())
    with pytest.raises(ValueError,match='INVALID_INPUT_ARTIFACT'):
        read(engine,analysis_source,verification_artifact_id=uuid4())


def test_missing_asset_is_unknown_not_foreign_asset(engine,analysis_source):
    value=read(engine,analysis_source,asset_id=None,component_id=None)
    assert value.asset.context_status=='MISSING' and value.asset.asset_id is None
    with pytest.raises(LookupError,match='Asset not found'):read(engine,analysis_source,asset_id=uuid4(),component_id=None)


def test_tampered_formal_receipt_rejected(engine,analysis_source):
    src=analysis_source
    with transaction(engine) as db:
        row=db.get(m.AgentRun,src.verification.run_id);before=copy.deepcopy(row.details)
        edited=copy.deepcopy(before);edited['runtime_v1']['artifacts']['verify']['tool_calls'][0]['sequence_no']+=111
        row.details=edited
    try:
        with pytest.raises(ValueError,match='INVALID_INPUT_ARTIFACT'):read(engine,src)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,src.verification.run_id).details=before


def test_multiple_components_are_not_arbitrarily_selected(engine,analysis_source):
    src=analysis_source
    with transaction(engine) as db:
        c=db.get(m.AssetComponent,src.component_id)
        duplicate=m.AssetComponent(asset_id=c.asset_id,product_id=c.product_id,package_identifier_id=c.package_identifier_id,
            raw_package_name=c.raw_package_name,version='0.5.0',ecosystem=c.ecosystem,purl=c.purl,details={'is_test':True})
        db.add(duplicate);db.flush();added=duplicate.id
    try:
        got=read(engine,src,component_id=None)
        assert got.asset.context_status=='AMBIGUOUS' and got.asset.component_id is None
    finally:
        with transaction(engine) as db:db.get(m.AssetComponent,added).deleted_at=utcnow()
