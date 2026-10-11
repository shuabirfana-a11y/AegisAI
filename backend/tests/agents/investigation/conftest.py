from types import SimpleNamespace
from sqlalchemy import select
import pytest
from app.db import models as m
from app.db.session import transaction
from app.utils.time import utcnow
from tests.runtime.conftest import runtime_seed as original_seed

@pytest.fixture(scope='session')
def investigation_seed(engine):
    """New committed synthetic records, reusing existing relational fixture builder."""
    saved=original_seed.__wrapped__(engine)
    with transaction(engine) as db:
        vuln=db.scalar(select(m.Vulnerability).where(m.Vulnerability.canonical_id==saved.cve))
        observed=db.scalar(select(m.SourceObservation).where(m.SourceObservation.external_id==saved.cve))
        source=db.get(m.Source,observed.source_id);source.authority_level='official'
        source.authority_scope='SYNTHETIC TEST ONLY; NOT REAL OFFICIAL INTELLIGENCE'
        observed=m.SourceObservation(source_id=source.id,raw_document_id=observed.raw_document_id,
            external_id=saved.cve,record_type='vulnerability',retrieved_at=utcnow(),http_status=200,
            raw_locator={'text_span':[0,19]},lineage_key=observed.lineage_key,publisher='SYNTHETIC',
            parse_status='parsed',normalizer_version='SYNTHETIC_INVESTIGATION',
            normalized_payload={'title':'SYNTHETIC','description':'SYNTHETIC vLLM advisory','products':[],'record_status':'published'})
        db.add(observed);db.flush()
        db.add(m.AiRelevanceAssessment(vulnerability_id=vuln.id,observation_id=observed.id,
            method='rule',result='relevant',reason_summary='SYNTHETIC fixture',evaluated_at=utcnow()))
        pkg=db.get(m.PackageIdentifier,db.get(m.AssetComponent,saved.component_id).package_identifier_id)
        version_range=db.scalar(select(m.AffectedVersionRange).where(m.AffectedVersionRange.vulnerability_id==vuln.id))
        db.add(m.AffectedVersionRange(vulnerability_id=vuln.id,product_id=version_range.product_id,
            package_identifier_id=pkg.id,source_id=source.id,observation_id=observed.id,
            introduced='0.5.0',fixed='0.7.0',range_type='ECOSYSTEM',raw_expression='>=0.5.0,<0.7.0',
            scope_key=version_range.scope_key,parse_status='parsed',parser_version='SYNTHETIC_INVESTIGATION'))
        component={'name':'vllm','ecosystem':'PyPI','package_name':pkg.package_name,'version':'0.6.0'}
        ids={'vulnerability_id':vuln.id,'source_id':source.id,'observation_id':observed.id}
    return SimpleNamespace(**saved.__dict__,component=component,**ids)
