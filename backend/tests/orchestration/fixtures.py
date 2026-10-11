"""Seed inputs only. No pre-generated Agent Runs or success artifacts for E2E."""
import hashlib
from uuid import uuid4
from app.db import models as m
from app.db.session import transaction
from app.utils.time import utcnow
from app.assistant.contracts import QueryRequest
from app.planner.schemas import PlannerInput
from app.orchestration.contracts import InvestigationRequest
from tests.agents.verification.conftest import verification_seed
from tests.agents.investigation.test_end_to_end import plan_for
from tests.planner.fixtures import gateway_with_responses,task


def scenario(engine,mode='complete'):
    seed=verification_seed.__wrapped__(engine);now=utcnow();mark={'is_test':True,'fixture':'PHASE11D_SYNTHETIC_NOT_BENCHMARK'}
    with transaction(engine) as db:
        extra=[('CVSS_SCORE',{'version':'3.1','score':8.1,'severity':'high'},'CVSS severity high 8.1'),
               ('FIXED_VERSION',{'ecosystem':'PyPI','package':seed.component['package_name'],'version':'0.7.0'},'fixed version 0.7.0')]
        if mode=='conflict':extra.append(('AFFECTS_VERSION',{'ecosystem':'PyPI','package':seed.component['package_name'],'raw_expression':'<=0.8.0'},'affected <=0.8.0'))
        src=m.Source(source_key='ORCH_SYNTHETIC_'+uuid4().hex,name='SYNTHETIC independent vendor',source_type='vendor_advisory',
            category='vulnerability',authority_level='official',authority_scope='vulnerability affected versions severity fixes',
            acquisition_method='fixture',base_url='https://example.invalid/ORCHESTRATION_SYNTHETIC',details=mark)
        db.add(src);db.flush();payload=('\n'.join(x[2] for x in extra)).encode()
        raw=m.RawDocument(source_id=src.id,external_id=seed.cve,source_url=src.base_url,published_at=now,retrieved_at=now,
            content_type='text/plain',raw_payload=payload,content_hash=hashlib.sha256(payload).hexdigest(),publisher=src.name,details=mark)
        db.add(raw);db.flush();obs=m.SourceObservation(source_id=src.id,raw_document_id=raw.id,external_id=seed.cve,
            record_type='vulnerability',retrieved_at=now,parse_status='parsed',publisher=raw.publisher,
            lineage_key='ORCH_SYNTHETIC:'+str(src.id),normalizer_version='TEST',normalized_payload={'canonical_id':seed.cve},details=mark)
        db.add(obs);db.flush()
        for index,(kind,value,text) in enumerate(extra,1):
            scope='PyPI:'+seed.component['package_name'] if kind in ('FIXED_VERSION','AFFECTS_VERSION') else seed.cve
            claim=m.Claim(claim_key='ORCH_SYNTHETIC_'+uuid4().hex,vulnerability_id=seed.vulnerability_id,
                package_identifier_id=seed.package_id if kind in ('FIXED_VERSION','AFFECTS_VERSION') else None,
                claim_type=kind,predicate=kind,scope_key=scope,value_json=value,details=mark)
            db.add(claim);db.flush();db.add(m.Evidence(claim_id=claim.id,source_id=src.id,raw_document_id=raw.id,observation_id=obs.id,
                scope_key=scope,evidence_type='official_vendor_advisory',stance='support',excerpt=text,
                excerpt_hash=hashlib.sha256(text.encode()).hexdigest(),source_url=raw.source_url,published_at=now,retrieved_at=now,
                locator={'line':index},locator_key=kind,observed_value=value,publisher=src.name,
                lineage_key=obs.lineage_key,details={**mark,'explicit':True}))
        package=db.get(m.PackageIdentifier,seed.package_id)
        asset=m.Asset(name='ORCH SYNTHETIC owned inventory',asset_type='service',owner_principal=seed.actor,
            is_demo=True,environment='production',exposure='internet',details=mark)
        db.add(asset);db.flush();component=m.AssetComponent(asset_id=asset.id,product_id=package.product_id,
            package_identifier_id=package.id,raw_package_name=package.package_name,version=None if mode=='unknown_version' else '0.6.0',
            ecosystem='PyPI',purl=package.purl,identity_status='resolved',inventory_revision=1,details=mark)
        db.add(component);db.flush();seed.asset_id=asset.id;seed.component_id=component.id
        if mode=='insufficient':
            db.get(m.Source,seed.source_id).authority_level='community';src.authority_level='community'
    question=(f'我的部署是否受到 {seed.cve} 影响，如何修复？' if mode=='unknown_version'
              else f'我的 vLLM 0.6.0 部署是否受到 {seed.cve} 影响，如何修复？')
    if mode=='required_partial':question+=' 请附证据。'
    plan=plan_for(seed,'lookup' if mode=='unknown_version' else 'version')
    plan['tasks'].append(task('asset_lookup','asset','get_asset',{'asset_id':str(seed.asset_id)}))
    if mode=='ambiguous':plan['tasks'].append(task('vulnerability_lookup','second_lookup','get_vulnerability',{'target':seed.cve}))
    if mode in ('optional_failure','required_partial','blocked'):
        node=task('evidence_search','extra_source','semantic_search',{'query':question})
        node['acceptance_criteria'].append('evidence_present');plan['tasks'].append(node)
        if mode=='blocked':
            child=task('evidence_search','blocked_child','get_evidence',{'target':seed.cve},['extra_source'])
            child['acceptance_criteria'].append('evidence_present');plan['tasks'].append(child)
    gateway,calls,sink=gateway_with_responses([plan])
    request=InvestigationRequest(planner_input=PlannerInput(query=QueryRequest(question=question,target=seed.cve,
        asset_id=seed.asset_id,request_key='ORCH-'+uuid4().hex),component_id=seed.component_id,
        component=None if mode=='unknown_version' else seed.component))
    return seed,request,gateway,calls,sink
