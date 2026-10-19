import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from app.orchestration.contracts import TYPE
from tests.orchestration.fixtures import scenario


def test_process_quota_is_shared_across_service_instances_and_does_not_allocate_busy_root(engine,monkeypatch):
    from app.orchestration.service import InvestigationOrchestrator,InvestigationBusy
    from app.orchestration.adapters import AgentServices
    from app.orchestration.control import InvestigationAbort
    entered=[threading.Event(),threading.Event()];release=threading.Event();lock=threading.Lock();count=[0]
    def wait(self,*a,**k):
        with lock:index=count[0];count[0]+=1
        entered[index].set();assert release.wait(10);raise InvestigationAbort('SYNTHETIC_STOP')
    monkeypatch.setattr(AgentServices,'investigate',wait)
    contexts=[scenario(engine) for _ in range(3)]
    services=[InvestigationOrchestrator(engine,x[2]) for x in contexts]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(services[i].investigate,contexts[i][1],actor=contexts[i][0].actor) for i in range(2)]
            assert all(e.wait(10) for e in entered)
            with pytest.raises(InvestigationBusy):services[2].investigate(contexts[2][1],actor=contexts[2][0].actor)
            with transaction(engine) as db:assert db.scalar(select(func.count()).select_from(m.AgentRun).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==contexts[2][0].actor))==0
            release.set()
            assert all(f.result(timeout=10).status.overall_status=='FAILED' for f in futures)
    finally:
        release.set()
        for x in contexts:x[2].close()


def test_concurrent_same_key_during_planning_uses_one_chain_and_frozen_running_read(engine):
    from app.orchestration.service import InvestigationOrchestrator
    seed,request,gw,calls,_=scenario(engine);entered=threading.Event();release=threading.Event()
    original=gw.text_provider.generate_structured
    def wait(req,schema):entered.set();assert release.wait(10);return original(req,schema)
    gw.text_provider.generate_structured=wait
    svc=InvestigationOrchestrator(engine,gw)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(svc.investigate,request,actor=seed.actor)
            assert entered.wait(10)
            duplicate=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
            assert duplicate.status.overall_status=='RUNNING' and duplicate.answer is None
            release.set();result=future.result(timeout=30)
        assert result.context.logical_investigation_id==duplicate.context.logical_investigation_id and len(calls)==1
    finally:release.set();gw.close()


def test_old_api_and_business_source_hashes_are_unchanged():
    import json,hashlib
    from pathlib import Path
    root=Path(__file__).resolve().parents[3]
    baseline=json.loads((root/'work/orchestration/baseline_hashes.json').read_text(encoding='utf-8'))
    frontend_changes=json.loads((root/'docs/phase14c1/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(frontend_changes)=={'frontend/public/app.js','frontend/public/index.html','frontend/public/styles.css',
        'frontend/public/modules/components.js','frontend/public/modules/router.js','frontend/public/modules/services.js',
        'frontend/public/modules/pages/assets.js','frontend/public/modules/pages/assistant.js','frontend/public/modules/pages/dashboard.js',
        'frontend/public/modules/pages/reviews.js','frontend/public/modules/pages/system.js','frontend/public/modules/pages/vulnerabilities.js'}
    poc_changes=json.loads((root/'docs/phase14b1/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(poc_changes)=={'backend/app/enrichment/enrichers/poc.py','backend/app/enrichment/service.py'}
    monitoring_changes=json.loads((root/'docs/phase14a/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    batch_changes=json.loads((root/'docs/phase14b4/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    regression_changes=json.loads((root/'docs/phase14b4_1/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(regression_changes)=={'backend/tests/conftest.py','backend/app/tooling/adapters.py'}
    assert set(batch_changes)=={'backend/app/main.py'}
    assert set(monitoring_changes)=={'backend/app/main.py','backend/app/api/openapi_contracts.py','backend/app/repositories/ingestion.py',
        'backend/app/repositories/sources.py'}
    # Baseline stays immutable; separately authorize exact Phase12D source digests.
    changes=json.loads((root/'docs/phase12d/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(changes)=={'backend/app/planner/schemas.py','backend/app/llm/config.py','backend/tests/agents/verification/test_rules.py','backend/tests/runtime/test_scheduler.py',
                         'backend/app/llm/providers/openai_compatible.py'}
    planner_changes=json.loads((root/'docs/phase12d1/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(planner_changes)=={'backend/app/agents/investigation/planner.py','backend/app/agents/investigation/planning.py',
                                 'backend/app/agents/investigation/roles.py','backend/tests/agents/investigation/test_planning.py'}
    asset_changes=json.loads((root/'docs/phase12d3/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    f2_changes=json.loads((root/'docs/phase13f2/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    f3_changes=json.loads((root/'docs/phase13f3/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(f3_changes)=={'backend/app/agents/investigation/planner.py','backend/app/agents/investigation/planning.py',
        'backend/app/agents/investigation/roles.py','backend/tests/agents/investigation/test_planning.py'}
    assert set(f2_changes)=={'backend/app/agents/investigation/planner.py','backend/app/agents/investigation/planning.py',
        'backend/app/agents/investigation/roles.py','backend/tests/agents/investigation/test_planning.py',
        'backend/app/agents/verification/schemas.py','backend/app/agents/verification/snapshot.py',
        'backend/app/orchestration/handoff.py','backend/app/orchestration/service.py'}
    assert set(asset_changes)=={'backend/app/agents/analysis/schemas.py','backend/app/agents/analysis/snapshot.py',
        'backend/app/agents/verification/schemas.py','backend/app/agents/verification/snapshot.py',
        'backend/app/agents/verification/reader.py','backend/app/tooling/analysis.py','backend/app/tooling/verification.py'}
    allowed={'backend/app/runtime/service.py','backend/app/agents/investigation/service.py','backend/app/runtime/process.py',
             'backend/app/main.py'}
    supplement_changes=json.loads((root/'docs/phase14b5/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(supplement_changes)=={'backend/app/agents/analysis/snapshot.py','backend/app/agents/verification/schemas.py',
        'backend/app/agents/verification/snapshot.py','backend/app/integration/snapshot.py',
        'backend/app/tooling/adapters.py','backend/app/tooling/contracts.py','frontend/public/modules/pages/assistant.js'}
    impact_changes=json.loads((root/'docs/phase14b7/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    primary_changes=json.loads((root/'docs/phase14b8/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(primary_changes)=={'backend/app/enrichment/acquisition.py','backend/app/enrichment/parsing.py',
                                  'backend/app/enrichment/enrichers/vendor.py'}
    assert set(impact_changes)=={'backend/app/orchestration/composer.py','backend/app/agents/verification/schemas.py',
        'backend/app/agents/verification/snapshot.py','backend/app/investigation_api/projection.py'}
    fact_changes=json.loads((root/'docs/phase14b9_1/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(fact_changes)=={'backend/app/agents/verification/schemas.py', 'backend/app/enrichment/enrichers/vendor.py', 'backend/app/orchestration/composer.py', 'backend/app/agents/verification/snapshot.py', 'backend/app/enrichment/contracts.py', 'backend/app/enrichment/enrichers/version.py'}
    before_fact=json.loads((root/'docs/phase14b9_1/before-code.json').read_text(encoding='utf-8'))
    c2_changes=json.loads((root/'docs/phase14c2/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    before_c2=json.loads((root/'docs/phase14c2/before-code.json').read_text(encoding='utf-8'))
    assert set(c2_changes)=={'backend/app/enrichment/conflict.py','backend/app/enrichment/rules.py',
                            'backend/app/agents/verification/snapshot.py','backend/app/agents/verification/rules.py'}
    c5_changes=json.loads((root/'docs/phase14c5/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    before_c5=json.loads((root/'docs/phase14c5/before-code.json').read_text(encoding='utf-8'))
    guarded_c5={'backend/app/agents/investigation/normalize.py','backend/app/agents/investigation/planner.py',
        'backend/app/agents/investigation/planning.py','backend/app/agents/investigation/service.py',
        'backend/app/agents/investigation/validation.py','backend/app/planner/schemas.py',
        'backend/app/tooling/adapters.py','backend/app/tooling/contracts.py'}
    assert set(c5_changes)&set(baseline)==guarded_c5
    c10_record=json.loads((root/'docs/phase14c10/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c10_record['authorization']=='PHASE14C10_USER_AUTHORIZED_AUTHORITATIVE_SOURCE_AND_SCOPE_HANDOFF'
    assert c10_record['historical_gold_modified'] is False and c10_record['gate_and_verification_rules_modified'] is False
    c10_changes=c10_record['changes']
    assert set(c10_changes)=={'backend/app/enrichment/acquisition.py','backend/app/enrichment/parsing.py',
        'backend/app/tooling/investigation.py','backend/app/agents/investigation/normalize.py'}
    c11_record=json.loads((root/'docs/phase14c11/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c11_record['authorization']=='PHASE14C11_USER_AUTHORIZED_SCOPED_EVIDENCE_AND_SCHEMA_ADAPTER'
    assert c11_record['gold_scoring_gate_verification_unchanged'] is True
    c11_changes=c11_record['changes']
    assert set(c11_changes)=={'backend/app/enrichment/enrichers/vendor.py','backend/app/agents/investigation/planning.py'}
    c12_record=json.loads((root/'docs/phase14c12/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c12_record['authorization']=='PHASE14C12_USER_AUTHORIZED_IDENTITY_AND_BOUND_SCOPE_CONSUMPTION'
    assert c12_record['gold_scoring_gate_verification_unchanged'] is True
    c12_changes=c12_record['changes']
    assert set(c12_changes)=={'backend/app/enrichment/context.py','backend/app/enrichment/enrichers/vendor.py','backend/app/agents/analysis/rules.py','backend/app/agents/analysis/recommendations.py'}
    c13_record=json.loads((root/'docs/phase14c13/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c13_record['authorization']=='PHASE14C13_USER_AUTHORIZED_REQUIRED_OBSERVATION_FEEDBACK'
    assert c13_record['gold_scoring_gate_verification_unchanged'] is True
    c13_changes=c13_record['changes']
    assert set(c13_changes)=={'backend/app/agents/investigation/planner.py'}
    c20_record=json.loads((root/'docs/phase14c20/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c20_record['authorization']=='PHASE14C20_USER_AUTHORIZED_FIELD_ERROR_RETRY_HANDOFF'
    assert c20_record['gold_scoring_gate_verification_unchanged'] is True
    assert c20_record['historical_configuration_modified'] is False
    assert set(c20_record['changes'])=={'backend/app/agents/investigation/planner.py'}
    assert set(c20_record['new_files'])=={'backend/app/agents/investigation/schema_feedback.py'}
    for path,digest in c20_record['new_files'].items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
    c22_record=json.loads((root/'docs/phase14c22/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c22_record['authorization']=='PHASE14C22_USER_AUTHORIZED_BOUNDED_REJECTED_CONTEXT_HANDOFF'
    assert c22_record['gold_scoring_gate_verification_unchanged'] is True
    assert c22_record['historical_configuration_modified'] is False
    assert set(c22_record['changes'])=={'backend/app/agents/investigation/planner.py'}
    assert set(c22_record['new_files'])=={'backend/app/agents/investigation/retry_context.py'}
    for path,digest in c22_record['new_files'].items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
    c15_record=json.loads((root/'docs/phase14c15/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c15_record['authorization']=='PHASE14C15_USER_AUTHORIZED_REGISTRY_SOURCE_ADAPTER'
    assert c15_record['gold_scoring_gate_verification_unchanged'] is True
    assert c15_record['historical_configuration_modified'] is False
    c15_changes=c15_record['changes']
    assert set(c15_changes)=={'backend/app/enrichment/acquisition.py','backend/app/enrichment/enrichers/version.py',
        'backend/app/tooling/adapters.py'}
    assert set(c15_record['new_files'])=={'backend/app/enrichment/package_registry.py'}
    for path,expected in c15_record['new_files'].items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest()==expected,path
    c16_record=json.loads((root/'docs/phase14c16/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c16_record['authorization']=='PHASE14C16_USER_AUTHORIZED_ONE_INLINE_CNA_SCOPE_FIX'
    assert c16_record['gold_scoring_gate_verification_unchanged'] is True
    assert c16_record['historical_configuration_modified'] is False
    assert set(c16_record['changes'])=={'backend/app/normalizers/cve.py'}
    c18_record=json.loads((root/'docs/phase14c18/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c18_record['authorization']=='PHASE14C18_USER_AUTHORIZED_EXISTING_ACCEPTANCE_SCHEMA_ALIGNMENT'
    assert c18_record['gold_scoring_gate_verification_unchanged'] is True
    assert c18_record['historical_configuration_modified'] is False
    assert set(c18_record['changes'])=={'backend/app/agents/investigation/planning.py'}
    c23_record=json.loads((root/'docs/phase14c23/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c23_record['authorization']=='PHASE14C23_USER_AUTHORIZED_TASK_AND_ARTIFACT_HANDOFF'
    assert c23_record['gold_scoring_gate_verification_unchanged'] is True
    assert c23_record['historical_configuration_modified'] is False
    assert set(c23_record['changes'])=={'backend/app/agents/investigation/planner.py',
        'backend/app/agents/investigation/planning.py','backend/app/agents/investigation/normalize.py'}
    c24_record=json.loads((root/'docs/phase14c24/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c24_record['authorization']=='PHASE14C24_USER_AUTHORIZED_CATALOG_BOUND_TASK_COMPLETION'
    assert c24_record['gold_scoring_gate_verification_unchanged'] is True
    assert c24_record['historical_configuration_modified'] is False
    assert set(c24_record['changes'])=={'backend/app/agents/investigation/planner.py'}
    assert set(c24_record['new_files'])=={'backend/app/agents/investigation/task_invariants.py'}
    c25_record=json.loads((root/'docs/phase14c25/source_hash_exceptions.json').read_text(encoding='utf-8'))
    assert c25_record['authorization']=='PHASE14C25_USER_AUTHORIZED_ONE_GENERIC_HIGH_YIELD_FIX'
    assert c25_record['gold_scoring_gate_verification_unchanged'] is True
    assert c25_record['historical_configuration_modified'] is False
    assert set(c25_record['changes'])==set(c24_record['new_files'])
    for path,expected in c24_record['new_files'].items():
        entry=c25_record['changes'][path]
        assert entry['previous_sha256']==expected,path
        assert hashlib.sha256((root/path).read_bytes()).hexdigest()==entry['current_sha256'],path
    def current_digest(path):
        actual=hashlib.sha256((root/path).read_bytes()).hexdigest()
        if path in c24_record['changes']:
            entry=c24_record['changes'][path]
            assert entry['baseline_sha256']==baseline[path],path
            assert entry['previous_sha256']==c23_record['changes'][path]['current_sha256'],path
            assert actual==entry['current_sha256'],path
            actual=entry['previous_sha256']
        if path not in c23_record['changes']:return actual
        entry=c23_record['changes'][path]
        assert entry['baseline_sha256']==baseline[path],path
        assert actual==entry['current_sha256'],path
        # Existing complete authorization chains below still check this prior digest.
        return entry['previous_sha256']
    for path,digest in baseline.items():
        if path in c18_record['changes']:
            entry=c18_record['changes'][path];previous=c11_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (c10_changes,c5_changes,c2_changes,fact_changes,primary_changes,impact_changes,supplement_changes,
                 regression_changes,batch_changes,frontend_changes,poc_changes,monitoring_changes,f3_changes,
                 f2_changes,asset_changes,planner_changes,changes) if path in group),digest)
            assert previous['baseline_sha256']==digest and previous['previous_sha256']==prior,path
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==previous['current_sha256'],path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in c16_record['changes']:
            entry=c16_record['changes'][path]
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==digest,path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in c15_changes:
            entry=c15_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (c13_changes,c12_changes,c11_changes,c10_changes,c5_changes,c2_changes,fact_changes,primary_changes,
                 impact_changes,supplement_changes,regression_changes,batch_changes,frontend_changes,poc_changes,
                 monitoring_changes,f3_changes,f2_changes,asset_changes,planner_changes,changes) if path in group),digest)
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==prior,path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in c13_changes:
            entry=c13_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (c12_changes,c11_changes,c10_changes,c5_changes,c2_changes,fact_changes,primary_changes,impact_changes,supplement_changes,
                 regression_changes,batch_changes,frontend_changes,poc_changes,monitoring_changes,f3_changes,
                 f2_changes,asset_changes,planner_changes,changes) if path in group),digest)
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==prior,path
            if path in c20_record['changes']:
                current=c20_record['changes'][path]
                assert current['baseline_sha256']==digest and current['previous_sha256']==entry['current_sha256'],path
                entry=current
            if path in c22_record['changes']:
                current=c22_record['changes'][path]
                assert current['baseline_sha256']==digest and current['previous_sha256']==entry['current_sha256'],path
                entry=current
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in c12_changes:
            entry=c12_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (c11_changes,c10_changes,c5_changes,c2_changes,fact_changes,primary_changes,impact_changes,supplement_changes,
                 regression_changes,batch_changes,frontend_changes,poc_changes,monitoring_changes,f3_changes,
                 f2_changes,asset_changes,planner_changes,changes) if path in group),digest)
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==prior,path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in c11_changes:
            entry=c11_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (c10_changes,c5_changes,c2_changes,fact_changes,primary_changes,impact_changes,supplement_changes,
                 regression_changes,batch_changes,frontend_changes,poc_changes,monitoring_changes,f3_changes,
                 f2_changes,asset_changes,planner_changes,changes) if path in group),digest)
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==prior,path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in c10_changes:
            entry=c10_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (c5_changes,c2_changes,fact_changes,primary_changes,impact_changes,supplement_changes,regression_changes,
                 batch_changes,frontend_changes,poc_changes,monitoring_changes,f3_changes,f2_changes,
                 asset_changes,planner_changes,changes) if path in group),digest)
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==prior,path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in guarded_c5:
            entry=c5_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (c2_changes,fact_changes,primary_changes,impact_changes,supplement_changes,regression_changes,
                 batch_changes,frontend_changes,poc_changes,monitoring_changes,f3_changes,f2_changes,
                 asset_changes,planner_changes,changes) if path in group),digest)
            if path in allowed:
                prior=hashlib.sha256((root/'work/phase14c5/before'/path).read_bytes()).hexdigest()
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==before_c5[path]==prior,path
            assert entry['authorization']=='PHASE14C5_USER_AUTHORIZED_CONFIRMED_DEFECT_ADAPTER_REPAIRS',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in c2_changes:
            entry=c2_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (fact_changes,primary_changes,impact_changes,supplement_changes,regression_changes,
                 batch_changes,frontend_changes,poc_changes,monitoring_changes,f3_changes,f2_changes,
                 asset_changes,planner_changes,changes) if path in group),digest)
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==before_c2[path]==prior,path
            assert entry['authorization']=='PHASE14C2_USER_AUTHORIZED_SOURCE_SCOPE_COMPARABILITY_ONLY',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in fact_changes:
            entry=fact_changes[path]
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==before_fact[path],path
            assert entry['authorization']=='PHASE14B9_1_USER_AUTHORIZED_FACT_VERIFICATION_CONTRACT_ONLY',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in primary_changes:
            entry=primary_changes[path]
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==digest,path
            assert entry['authorization']=='PHASE14B8_USER_AUTHORIZED_TOP1_PRIMARY_EVIDENCE_ADAPTER',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in impact_changes:
            entry=impact_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (supplement_changes,regression_changes,frontend_changes,f3_changes,f2_changes,asset_changes,planner_changes,changes) if path in group),digest)
            assert entry['baseline_sha256']==digest and entry['previous_sha256']==prior,path
            assert entry['authorization']=='PHASE14B7_USER_AUTHORIZED_IMPACT_SCOPE_CLAIM_AND_ANSWER_CLOSURE',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in supplement_changes:
            entry=supplement_changes[path]
            prior=next((group[path]['current_sha256'] for group in
                (regression_changes,frontend_changes,f3_changes,f2_changes,asset_changes,planner_changes,changes) if path in group),digest)
            assert entry['baseline_sha256']==digest,path
            assert entry['previous_sha256']==prior,path
            assert entry['authorization']=='PHASE14B5_USER_AUTHORIZED_BOUNDED_EVIDENCE_ADAPTERS',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in regression_changes:
            entry=regression_changes[path]
            assert entry['baseline_sha256']==entry['previous_sha256']==digest,path
            expected_authorization=('PHASE14B4_1_USER_AUTHORIZED_TEST_DATABASE_ISOLATION'
                if path=='backend/tests/conftest.py' else 'PHASE14B4_1_USER_AUTHORIZED_EMPTY_CORPUS_FIX')
            assert entry['authorization']==expected_authorization,path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in batch_changes:
            entry=batch_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['previous_sha256']==monitoring_changes[path]['current_sha256'],path
            assert entry['authorization']=='PHASE14B4_USER_AUTHORIZED_BATCH_ADAPTER',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in frontend_changes:
            entry=frontend_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['authorization']=='PHASE14C1_USER_AUTHORIZED_FRONTEND_INTEGRATION_FIXES',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in poc_changes:
            entry=poc_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['authorization']=='PHASE14B1_USER_AUTHORIZED_POC_ARTIFACT_ADAPTER',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in monitoring_changes:
            entry=monitoring_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['authorization']=='PHASE14A_USER_AUTHORIZED_MONITORING_ADAPTERS',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in f3_changes:
            entry=f3_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['previous_sha256']==f2_changes[path]['current_sha256'],path
            assert entry['authorization']=='PHASE13F3_USER_AUTHORIZED_NORMALIZATION_AND_TASK_TEMPLATES',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in f2_changes:
            entry=f2_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['authorization']=='PHASE13F2_USER_AUTHORIZED_INPUT_PLANNER_AND_CONFLICT_HANDOFF',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in asset_changes:
            entry=asset_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['authorization']=='PHASE12D3_USER_AUTHORIZED_ASSET_HANDOFF_ADAPTERS',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in planner_changes:
            entry=planner_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['authorization']=='PHASE12D1_USER_AUTHORIZED_PLANNER_STABILITY',path
            assert current_digest(path)==entry['current_sha256'],path
            continue
        if path in changes:
            assert changes[path]['baseline_sha256']==digest,path
            assert changes[path]['authorization'] in {'USER_APPROVED_SCHEMA_METADATA_ONLY','PHASE12D_MODEL_PROVIDER_CONFIGURATION','PHASE12D_TEST_CLOCK_ISOLATION','PHASE12D_TEST_MONOTONIC_CONCURRENCY'}
            assert current_digest(path)==changes[path]['current_sha256'],path
            continue
        if path not in allowed:assert current_digest(path)==digest,path
    from fastapi.routing import APIRoute
    from app.main import create_app
    from app.api import routes,enrichment,assets,assistant,tools
    expected={(route.path,method):route.endpoint for module in (routes,enrichment,assets,assistant,tools)
              for route in module.router.routes if isinstance(route,APIRoute) for method in route.methods}
    def flat(routes):
        for route in routes:
            if hasattr(route,'original_router'):
                yield from flat(route.original_router.routes)
            else:yield route
    actual={(route.path,method):route.endpoint for route in flat(create_app().routes) if isinstance(route,APIRoute)
            and not route.path.startswith(('/api/investigations','/api/v1/intelligence')) for method in route.methods}
    assert len(expected)==34
    assert actual==expected
