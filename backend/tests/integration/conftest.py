"""Real service/Runtime/process/database chain over marked synthetic intelligence."""
import hashlib
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from app.utils.time import utcnow
from tests.runtime.conftest import engine
from tests.agents.verification.conftest import verification_seed

def build_chain(engine,mode='complete'):
    from app.agents.investigation.service import IntelligenceInvestigationService
    from app.agents.verification.service import EvidenceVerificationService
    from app.agents.verification.schemas import VerificationRequest
    from app.agents.analysis.service import SecurityAnalysisService
    from app.agents.analysis.schemas import AnalysisRequest
    from app.planner.schemas import PlannerInput
    from tests.planner.fixtures import gateway_with_responses,cve_input,task
    from tests.agents.investigation.test_end_to_end import plan_for
    seed=verification_seed.__wrapped__(engine);now=utcnow()
    with transaction(engine) as db:
        extra=[('CVSS_SCORE',{'version':'3.1','score':8.1,'severity':'high'},'CVSS severity high 8.1'),
               ('FIXED_VERSION',{'ecosystem':'PyPI','package':seed.component['package_name'],'version':'0.7.0'},'fixed version 0.7.0')]
        if mode in ('unknown','overview'):extra=extra[1:]
        if mode=='conflict':extra.append(('AFFECTS_VERSION',{'ecosystem':'PyPI','package':seed.component['package_name'],'raw_expression':'<=0.8.0'},'affected <=0.8.0'))
        source=m.Source(source_key='GATE_SYNTHETIC_'+uuid4().hex,name='SYNTHETIC additional vendor',
            source_type='vendor_advisory',category='vulnerability',authority_level='official',
            authority_scope='vulnerability affected versions severity fixes',acquisition_method='fixture',
            base_url='https://example.invalid/GATE_SYNTHETIC',details={'is_test':True})
        db.add(source);db.flush();payload=('\n'.join(e[2] for e in extra)).encode()
        raw=m.RawDocument(source_id=source.id,external_id=seed.cve,source_url=source.base_url,published_at=now,
            retrieved_at=now,content_type='text/plain',raw_payload=payload,content_hash=hashlib.sha256(payload).hexdigest(),
            publisher='SYNTHETIC additional vendor',details={'is_test':True})
        db.add(raw);db.flush()
        obs=m.SourceObservation(source_id=source.id,raw_document_id=raw.id,external_id=seed.cve,
            record_type='vulnerability',retrieved_at=now,parse_status='parsed',publisher=raw.publisher,
            lineage_key='GATE_SYNTHETIC:'+str(source.id),normalizer_version='TEST',
            normalized_payload={'canonical_id':seed.cve},details={'is_test':True})
        db.add(obs);db.flush()
        for index,(kind,value,text) in enumerate(extra,1):
            scope='PyPI:'+seed.component['package_name'] if kind in ('FIXED_VERSION','AFFECTS_VERSION') else seed.cve
            claim=m.Claim(claim_key='GATE_SYNTHETIC_'+uuid4().hex,vulnerability_id=seed.vulnerability_id,
                package_identifier_id=seed.package_id if kind in ('FIXED_VERSION','AFFECTS_VERSION') else None,
                claim_type=kind,predicate=kind,scope_key=scope,value_json=value,details={'is_test':True})
            db.add(claim);db.flush()
            db.add(m.Evidence(claim_id=claim.id,source_id=source.id,raw_document_id=raw.id,observation_id=obs.id,
                scope_key=scope,evidence_type='official_vendor_advisory',stance='support',excerpt=text,
                excerpt_hash=hashlib.sha256(text.encode()).hexdigest(),source_url=raw.source_url,published_at=now,retrieved_at=now,
                locator={'line':index},locator_key=kind,observed_value=value,publisher=raw.publisher,
                lineage_key=obs.lineage_key,details={'explicit':True,'is_test':True}))
        package=db.get(m.PackageIdentifier,seed.package_id)
        asset=m.Asset(name='GATE SYNTHETIC owned inventory',asset_type='service',owner_principal=seed.actor,
            is_demo=True,environment='production',exposure='internet',details={'is_test':True})
        db.add(asset);db.flush()
        component=m.AssetComponent(asset_id=asset.id,product_id=package.product_id,package_identifier_id=package.id,
            raw_package_name=package.package_name,version='0.6.0',ecosystem='PyPI',purl=package.purl,
            identity_status='resolved',inventory_revision=1,details={'is_test':True})
        db.add(component);db.flush();seed.asset_id=asset.id;component_id=component.id
    question=f'{seed.cve}已有情报概览' if mode=='overview' else f'我的 vLLM 0.6.0 部署是否受到 {seed.cve} 影响，如何修复？'
    plan=plan_for(seed,'version');plan['tasks'].append(task('asset_lookup','asset','get_asset',{'asset_id':str(seed.asset_id)}))
    if mode in ('optional_failure','required_partial','blocked'):
        node=task('evidence_search','extra_source','semantic_search',{'query':question})
        node['acceptance_criteria'].append('evidence_present');plan['tasks'].append(node)
        if mode=='blocked':
            next_task=task('evidence_search','blocked_child','get_evidence',{'target':seed.cve},['extra_source'])
            next_task['acceptance_criteria'].append('evidence_present');plan['tasks'].append(next_task)
    gw,calls,_=gateway_with_responses([plan]);investigator=IntelligenceInvestigationService(engine,gw)
    raw=cve_input(target=seed.cve,question=question)
    input=PlannerInput(query=raw.query.model_copy(update={'asset_id':seed.asset_id}),component=seed.component,component_id=component_id)
    try:
        saved=investigator.plan_and_run(input,seed.actor)
        assert saved.runtime_run_id is not None,investigator.read_planner_trace(saved.planner_run_id,seed.actor).error
    finally:gw.close()
    inv=investigator.read_results(saved.runtime_run_id,seed.actor).artifacts[0]
    verifier=EvidenceVerificationService(engine)
    vr=verifier.run(VerificationRequest(source_run_id=inv.run_id,source_task_id=inv.task_id,source_artifact_id=inv.artifact_id,
        request_key='GATE-VERIFY-'+uuid4().hex),actor=seed.actor)
    ver=verifier.read_results(vr.run_id,actor=seed.actor).artifacts[0]
    analyzer=SecurityAnalysisService(engine)
    ar=analyzer.run(AnalysisRequest(investigation_run_id=inv.run_id,investigation_task_id=inv.task_id,
        investigation_artifact_id=inv.artifact_id,verification_run_id=ver.run_id,verification_task_id=ver.task_id,
        verification_artifact_id=ver.artifact_id,asset_id=seed.asset_id,component_id=component_id,
        request_key='GATE-ANALYSIS-'+uuid4().hex),actor=seed.actor)
    risk=analyzer.read_results(ar.run_id,actor=seed.actor).artifacts[0]
    return SimpleNamespace(seed=seed,investigation=inv,verification=ver,analysis=risk,planner=saved,
        asset_id=seed.asset_id,component_id=component_id,input=input,model_calls=calls)

@pytest.fixture(scope='session')
def gate_chain(engine):return build_chain(engine)
