"""Dedicated database inputs; all analysis examples are SYNTHETIC, not benchmark labels."""
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from tests.runtime.conftest import engine
from tests.agents.verification.conftest import verification_seed


@pytest.fixture(scope='session')
def analysis_source(engine):
    from tests.agents.investigation.test_end_to_end import run
    from app.agents.verification.service import EvidenceVerificationService
    from tests.agents.verification.test_snapshot import request
    seed=verification_seed.__wrapped__(engine)
    original,saved,_,_=run(engine,seed,'version')
    artifact=original.read_results(saved.runtime_run_id,seed.actor).artifacts[0]
    source=SimpleNamespace(artifact=artifact,seed=seed)
    verifier=EvidenceVerificationService(engine)
    verified_run=verifier.run(request(source),actor=seed.actor)
    verified=verifier.read_results(verified_run.run_id,actor=seed.actor).artifacts[0]
    with transaction(engine) as db:
        package=db.get(m.PackageIdentifier,seed.package_id)
        asset=m.Asset(name='SYNTHETIC analysis asset',asset_type='service',owner_principal=seed.actor,
                      is_demo=True,exposure='internet',environment='production',details={'is_test':True})
        db.add(asset);db.flush()
        component=m.AssetComponent(asset_id=asset.id,product_id=package.product_id,package_identifier_id=package.id,
            raw_package_name=package.package_name,version='0.6.0',ecosystem='PyPI',purl=package.purl,
            identity_status='resolved',inventory_revision=1,details={'is_test':True})
        db.add(component);db.flush()
        asset_id=asset.id;component_id=component.id
    return SimpleNamespace(seed=seed,original=original,investigation=artifact,verifier=verifier,
        verification=verified,asset_id=asset_id,component_id=component_id)
