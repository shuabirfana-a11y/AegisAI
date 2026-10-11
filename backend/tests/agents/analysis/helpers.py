"""Hand-checked synthetic inputs for pure-rule tests; never production provenance."""
import importlib
from uuid import uuid4
import pytest
from app.utils.time import utcnow
from app.agents.contracts import fingerprint
from app.agents.verification.schemas import VerificationClaim,ClaimVerification,VerificationArtifact
from tests.agents.verification.helpers import evidence
from app.agents.investigation.schemas import InvestigationArtifact


def module(name):
    try:return importlib.import_module('app.agents.analysis.'+name)
    except ModuleNotFoundError:pytest.fail('Analysis '+name+' is missing')


def request(source,**changes):
    data=dict(investigation_run_id=source.investigation.run_id,investigation_task_id=source.investigation.task_id,
        investigation_artifact_id=source.investigation.artifact_id,verification_run_id=source.verification.run_id,
        verification_task_id=source.verification.task_id,verification_artifact_id=source.verification.artifact_id,
        asset_id=source.asset_id,component_id=source.component_id,request_key='SYNTHETIC-'+uuid4().hex)
    data.update(changes)
    return module('schemas').AnalysisRequest(**data)


def verified(kind='AFFECTS_VERSION',identifier='impact',value=None,status='CONFIRMED',package='pkg-vllm',branch=None):
    raw=VerificationClaim(claim_id=identifier,statement='SYNTHETIC '+kind,claim_type=kind,source_task_id='lookup',
        value=value or {'ecosystem':'PyPI','package':'vllm','raw_expression':'>=0.5.0,<0.7.0'},
        scope_key='PyPI:vllm' if package else 'CVE-2099-9999113',vulnerability_id='CVE-2099-9999113',
        package_identifier_id=package,branch=branch,evidence_ids=('E-'+identifier,),claim_revision=1,status=status)
    return ClaimVerification(claim=raw,status=status,confidence=0.9 if status=='CONFIRMED' else 0.1,
        supporting_evidence_ids=('E-'+identifier,) if status=='CONFIRMED' else (),
        reason_code='SYNTHETIC',reason_summary='SYNTHETIC independent decision')


def context(claims=None,**changes):
    s=module('schemas');now=utcnow();run_id=uuid4();artifact_id=uuid4();asset_id=uuid4();component_id=uuid4()
    cs=tuple(claims if claims is not None else [verified()])
    original=InvestigationArtifact(artifact_id=artifact_id,run_id=run_id,task_id='lookup',status='COMPLETE',
        runtime_status='SUCCESS',vulnerability_id='CVE-2099-9999113',component={'name':'vllm'},
        poc_candidates=changes.get('candidates',[]),patch_information=changes.get('patch_candidates',[]))
    support=tuple(evidence(identifier='E-'+c.claim.claim_id,claim_id=c.claim.claim_id,observed_value=c.claim.value,
        scope_key=c.claim.scope_key,vulnerability_id=c.claim.vulnerability_id,
        source_key='CISA_KEV' if c.claim.claim_type=='KNOWN_EXPLOITED' else 'SYNTHETIC_vendor',
        evidence_type='kev_record' if c.claim.claim_type=='KNOWN_EXPLOITED' else 'official_vendor_advisory')
        for c in cs if c.status=='CONFIRMED')
    verification=VerificationArtifact(artifact_id=uuid4(),run_id=uuid4(),task_id='verify',source_run_id=run_id,
        source_artifact_id=artifact_id,source_snapshot_hash='a'*64,evaluation_time=now,claims=cs,
        verification_status=changes.get('verification_status','CONFIRMED'),confidence=0.9,supporting_evidence=support,
        execution_status=changes.get('execution_status','SUCCESS'),partial_result=changes.get('partial',False))
    asset=s.AssetContextSnapshot(asset_id=asset_id,component_id=component_id,component='vllm',
        package_identifier_id=changes.get('package','pkg-vllm'),package_name='vllm',ecosystem='PyPI',purl='pkg:pypi/vllm',
        deployed_version=changes.get('version','0.6.0'),inventory_revision=1,captured_at=now,
        exposure=changes.get('exposure','internet'),environment='production',context_status=changes.get('asset_status','RESOLVED'))
    req=s.AnalysisRequest(investigation_run_id=run_id,investigation_task_id='lookup',investigation_artifact_id=artifact_id,
        verification_run_id=verification.run_id,verification_task_id='verify',verification_artifact_id=verification.artifact_id,
        asset_id=asset_id,component_id=component_id,request_key='SYNTHETIC-'+uuid4().hex,
        model_assistance=changes.get('model_assistance',False))
    inputs=s.AnalysisInputs(investigation=original,verification=verification,asset=asset,
        source_claims=tuple(changes.get('source_claims',[x.claim for x in cs])),source_snapshot_hash='a'*64,
        source_verification_task=changes.get('verification_task','evidence_verification'),
        coverage_complete=changes.get('coverage',True),epss=tuple(changes.get('epss',[])))
    return s.AnalysisContext(context_id=uuid4(),owner='SYNTHETIC-owner',request=req,
        request_hash=fingerprint(req.model_dump(mode='json')),input_snapshot_hash=fingerprint(inputs.model_dump(mode='json')),
        evaluation_time=now,inputs=inputs)
