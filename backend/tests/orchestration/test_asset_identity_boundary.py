"""Compatibility of sealed inventory, using explicitly synthetic source fixtures."""
import pytest
from app.db import models as m
from app.db.session import transaction
from app.orchestration.service import InvestigationOrchestrator
from app.orchestration.answer_sources import AnswerSourcesLoader
from tests.orchestration.fixtures import scenario


def test_legacy_inventory_null_identity_fields_use_exact_registered_package(engine):
    seed,request,gw,_,_=scenario(engine)
    try:
        with transaction(engine) as db:
            component=db.get(m.AssetComponent,seed.component_id)
            # Legal inventory left by the additive 0003 migration, not a new alias.
            component.ecosystem=None;component.purl=None;component.namespace=None
            component.details={}
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        assert result.status.error_code is None
        sources,gate,_=AnswerSourcesLoader(engine).load(result.context,actor=seed.actor)
        assert sources.verification.version_observations[0].ecosystem=='unknown'
        assert sources.verification.version_observations[0].version=='0.6.0'
        assert sources.analysis.asset_match_status=='MATCHED'
        assert sources.analysis.affected is True and sources.analysis.risk_level=='HIGH'
        assert gate.status=='PASS'
    finally:gw.close()


@pytest.mark.parametrize('suffix',['?arch=x86_64','#lib'])
@pytest.mark.parametrize('registered',[False,True])
def test_qualified_inventory_preserves_explicit_applicability_boundary(engine,suffix,registered):
    seed,request,gw,_,_=scenario(engine)
    try:
        with transaction(engine) as db:
            package=db.get(m.PackageIdentifier,seed.package_id)
            qualified=package.purl+'@0.6.0'+suffix
            if registered:
                # One exact row, preserving the unique distribution constraint.
                # This boundary input is not an assertion about normal imports.
                package.purl=qualified
            db.get(m.AssetComponent,seed.component_id).purl=qualified
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        assert result.status.error_code=='GATE_FAILED'
        sources,gate,_=AnswerSourcesLoader(engine).load(result.context,actor=seed.actor)
        assert sources.verification.verification_status=='CONFIRMED'
        assert sources.analysis.affected is None
        assert sources.analysis.risk_level=='UNKNOWN'
        assert sources.analysis.priority=='REVIEW_REQUIRED'
        assert gate.status=='FAILED'
        assert any(check.code=='OBJECTIVE_PACKAGE_MISMATCH' and check.blocking=='FATAL'
                   for check in gate.checks)
    finally:gw.close()
