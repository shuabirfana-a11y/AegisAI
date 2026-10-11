from hashlib import sha256
import pytest
from sqlalchemy import select,func,update,delete
from sqlalchemy.exc import DBAPIError, IntegrityError
from app.db import models as m
from app.db.persistence import ensure_vulnerability,store_raw,record_review,RevisionConflict,IdempotencyConflict
from conftest import NOW

def count(db,model): return db.scalar(select(func.count()).select_from(model))
def raw_values(s,payload=b'SYNTHETIC revised content'):
    return dict(source_id=s.sources[0].id,external_id=s.raws[0].external_id,source_url=s.raws[0].source_url,retrieved_at=NOW,content_type='text/plain',raw_payload=payload,publisher='TEST_CVE',completeness='complete')
def review_values(s,**overrides):
    value=dict(task_id=s.review.id,actor='test-analyst',expected_revision=1,expected_claim_revision=1,request_key='TEST-REQUEST-1',status='confirmed',value={'raw_expression':'<0.8.4'},reason='Test analyst checked synthetic scoped source',evidence_ids=[s.evidence[0].id])
    value.update(overrides); return value

def test_01_three_sources_one_vulnerability(db,seed):
    ids=[ensure_vulnerability(db,seed.vuln.canonical_id,'SYNTHETIC') for _ in seed.sources]
    assert all(v is not None for v in ids)
    assert {v.id for v in ids}=={seed.vuln.id}
    assert count(db,m.Vulnerability)==1 and count(db,m.RawDocument)==3 and count(db,m.Evidence)==3

def test_02_one_vulnerability_two_products(db,seed):
    assert set(db.scalars(select(m.AffectedVersionRange.product_id).where(m.AffectedVersionRange.vulnerability_id==seed.vuln.id)))=={p.id for p in seed.products}

def test_03_product_multiple_ranges(db,seed):
    r=m.AffectedVersionRange(vulnerability_id=seed.vuln.id,product_id=seed.products[0].id,package_identifier_id=seed.packages[0].id,source_id=seed.sources[0].id,observation_id=seed.observations[0].id,introduced='0.9.0',fixed='0.9.2',raw_expression='>=0.9.0,<0.9.2',range_type='ECOSYSTEM',scope_key='test-vllm-0.9',parse_status='parsed',parser_version='TEST-1')
    db.add(r);db.flush()
    assert len(list(db.scalars(select(m.AffectedVersionRange).where(m.AffectedVersionRange.product_id==seed.products[0].id))))==2

def test_04_scoped_conflict_retains_both_evidence(db,seed):
    result=m.VerificationResult(claim_id=seed.claim.id,claim_revision=1,status='conflict',verification_method='test_manual_scope_check',reason_summary='Synthetic support and contradiction share scope',verified_at=NOW,verified_by_type='system',verified_by_id='TEST-VERIFIER',decision_key='TEST-CONFLICT')
    db.add(result);db.flush()
    for e in [seed.evidence[0],seed.evidence[2]]: db.add(m.VerificationEvidence(claim_id=seed.claim.id,verification_result_id=result.id,evidence_id=e.id))
    db.flush()
    assert result.status=='conflict' and count(db,m.VerificationEvidence)==2
    assert {seed.evidence[0].stance,seed.evidence[2].stance}=={'support','contradict'}

def test_05_poc_url_does_not_confirm(db,seed):
    db.refresh(seed.poc)
    assert seed.poc.status=='candidate' and seed.poc.usability_status=='not_evaluated'

def test_06_unsupported_preserves_raw_expression(db,seed):
    r=m.AffectedVersionRange(vulnerability_id=seed.vuln.id,product_id=seed.products[0].id,package_identifier_id=seed.packages[0].id,source_id=seed.sources[0].id,observation_id=seed.observations[0].id,raw_expression='before next compatible train',range_type='TEXT',scope_key='test-unsupported',parse_status='unsupported',parse_reason='No deterministic boundary',parser_version='TEST-1')
    db.add(r);db.flush();db.refresh(r)
    assert r.raw_expression=='before next compatible train' and r.fixed is None

def test_07_repeated_raw_write_is_idempotent(db,seed):
    values=raw_values(seed,seed.raws[0].raw_payload)
    first=store_raw(db,**values);second=store_raw(db,**values)
    assert first is not None and second is not None
    assert first.id==second.id==seed.raws[0].id and count(db,m.RawDocument)==3

def test_08_asset_match_pins_range_and_version(db,seed):
    match=m.AssetVulnerabilityMatch(asset_component_id=seed.component.id,vulnerability_id=seed.vuln.id,package_identifier_id=seed.packages[0].id,matched_range_id=seed.ranges[0].id,claim_id=seed.claim.id,match_status='affected',version_at_evaluation='0.8.2',component_revision=1,claim_revision=1,matcher_version='TEST-1',reason_summary='Fixture match only; not an implemented comparator',detected_at=NOW,last_evaluated_at=NOW)
    db.add(match);db.flush();db.refresh(match)
    assert match.matched_range_id==seed.ranges[0].id and match.version_at_evaluation=='0.8.2'

def test_09_review_produces_audit(db,seed):
    audit=record_review(db,**review_values(seed))
    assert audit is not None
    assert audit.before_state['value']!=audit.after_state['value'] and audit.actor=='test-analyst'
    assert count(db,m.AuditLog)==1 and count(db,m.VerificationResult)==1
    assert seed.claim.revision==2 and seed.review.status=='resolved'

def test_10_soft_delete_and_title_update_preserve_evidence(db,seed):
    seed.vuln.title='Updated canonical display';seed.vuln.deleted_at=NOW;db.flush()
    assert count(db,m.Evidence)==3
    assert db.get(m.RawDocument,seed.raws[0].id).raw_payload==seed.raws[0].raw_payload
    with pytest.raises(DBAPIError),db.begin_nested():
        db.execute(delete(m.Vulnerability).where(m.Vulnerability.id==seed.vuln.id));db.flush()
    assert count(db,m.Evidence)==3

@pytest.mark.parametrize('model',['RawDocument','Evidence','VerificationResult','AuditLog','IntelligenceEvent'])
def test_history_guards_installed(engine,model):
    table=getattr(m,model).__table__
    from sqlalchemy import text
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=:schema AND c.relname=:table AND t.tgname=\'immutable_history\''),{'schema':table.schema,'table':table.name})==1

@pytest.mark.parametrize('action',['update','delete'])
def test_raw_history_rejects_mutation(db,seed,action):
    with pytest.raises(DBAPIError),db.begin_nested():
        command=update(m.RawDocument).where(m.RawDocument.id==seed.raws[0].id).values(raw_payload=b'changed') if action=='update' else delete(m.RawDocument).where(m.RawDocument.id==seed.raws[0].id)
        db.execute(command);db.flush()
    assert db.get(m.RawDocument,seed.raws[0].id).raw_payload==seed.raws[0].raw_payload

def test_changed_raw_content_creates_revision(db,seed):
    new=store_raw(db,**raw_values(seed))
    assert new is not None and new.id!=seed.raws[0].id and count(db,m.RawDocument)==4
    assert db.get(m.Evidence,seed.evidence[0].id).raw_document_id==seed.raws[0].id

def test_same_bytes_different_sources_keep_sources(db,seed):
    values=raw_values(seed,seed.raws[0].raw_payload);values['source_id']=seed.sources[2].id
    new=store_raw(db,**values)
    assert new is not None and new.id!=seed.raws[0].id

def test_review_retry_is_idempotent(db,seed):
    a=record_review(db,**review_values(seed));b=record_review(db,**review_values(seed))
    assert a is not None and b is not None and a.id==b.id and count(db,m.AuditLog)==1

def test_review_same_request_different_payload_rejected(db,seed):
    record_review(db,**review_values(seed))
    with pytest.raises(IdempotencyConflict): record_review(db,**review_values(seed,value={'raw_expression':'<=0.8.5'}))

def test_review_stale_revision_rejected(db,seed):
    record_review(db,**review_values(seed))
    with pytest.raises(RevisionConflict): record_review(db,**review_values(seed,request_key='SECOND'))

def test_defer_retains_conflict_and_value(db,seed):
    seed.claim.verification_status='conflict';db.flush()
    old=seed.claim.value_json.copy()
    audit=record_review(db,**review_values(seed,status='deferred',value=None,evidence_ids=[]))
    assert audit is not None and seed.review.status=='deferred'
    assert seed.claim.value_json==old and seed.claim.verification_status=='conflict'

def test_confirm_without_evidence_is_rejected(db,seed):
    with pytest.raises(ValueError): record_review(db,**review_values(seed,evidence_ids=[]))
    assert count(db,m.AuditLog)==0

def test_cross_scope_evidence_is_rejected(db,seed):
    e=seed.evidence[0]
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.Evidence(claim_id=seed.claim.id,scope_key='different-cvss-version',source_id=e.source_id,raw_document_id=e.raw_document_id,observation_id=e.observation_id,evidence_type='test',stance='contradict',excerpt='wrong scope',excerpt_hash=sha256(b'wrong scope').hexdigest(),source_url=e.source_url,retrieved_at=NOW,locator={},locator_key='different',publisher=e.publisher,lineage_key=e.lineage_key));db.flush()

def test_wrong_product_package_is_rejected(db,seed):
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.AssetComponent(asset_id=seed.asset.id,product_id=seed.products[1].id,package_identifier_id=seed.packages[0].id,version='0.8.2'));db.flush()

def test_match_wrong_package_range_is_rejected(db,seed):
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.AssetVulnerabilityMatch(asset_component_id=seed.component.id,vulnerability_id=seed.vuln.id,package_identifier_id=seed.packages[0].id,matched_range_id=seed.ranges[1].id,match_status='affected',component_revision=1,claim_revision=1,matcher_version='TEST-1',reason_summary='invalid',detected_at=NOW,last_evaluated_at=NOW));db.flush()

def test_advisory_can_link_two_distinct_vulnerabilities(db,seed):
    other=m.Vulnerability(canonical_id='CVE-2099-9999002',title='Another SYNTHETIC issue')
    db.add(other);db.flush()
    identifier=m.ExternalIdentifier(identifier_type='ADVISORY',identifier_value='TEST-ADVISORY',normalized_value='TEST-ADVISORY',source_id=seed.sources[0].id)
    db.add(identifier);db.flush()
    for v in [seed.vuln,other]: db.add(m.VulnerabilityIdentifier(vulnerability_id=v.id,identifier_id=identifier.id,identifier_type='ADVISORY'))
    db.flush()
    assert count(db,m.Vulnerability)==2 and count(db,m.VulnerabilityIdentifier)==2

def test_one_cve_identifier_cannot_own_two_vulnerabilities(db,seed):
    other=m.Vulnerability(canonical_id='CVE-2099-9999002',title='Another SYNTHETIC issue');db.add(other);db.flush()
    identifier=m.ExternalIdentifier(identifier_type='CVE',identifier_value=seed.vuln.canonical_id,normalized_value=seed.vuln.canonical_id,source_id=seed.sources[0].id);db.add(identifier);db.flush()
    db.add(m.VulnerabilityIdentifier(vulnerability_id=seed.vuln.id,identifier_id=identifier.id,identifier_type='CVE'));db.flush()
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.VulnerabilityIdentifier(vulnerability_id=other.id,identifier_id=identifier.id,identifier_type='CVE'));db.flush()

def test_kev_absence_not_false_exploitation(db,seed):
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.KnownExploitation(vulnerability_id=seed.vuln.id,source_id=seed.sources[0].id,raw_document_id=seed.raws[0].id,known_exploited=False,catalog_status='not_listed_as_of',catalog_complete=True,catalog_version='TEST-1',observed_at=NOW));db.flush()

def test_epss_out_of_bounds_rejected(db,seed):
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.EpssSnapshot(vulnerability_id=seed.vuln.id,source_id=seed.sources[0].id,raw_document_id=seed.raws[0].id,score=1.1,score_date=NOW.date(),observed_at=NOW,model_version='TEST-1'));db.flush()

def test_cvss_versions_coexist_without_conflict(db,seed):
    for version,score in [('3.1',9.8),('4.0',9.3)]: db.add(m.CvssAssessment(vulnerability_id=seed.vuln.id,source_id=seed.sources[0].id,observation_id=seed.observations[0].id,version=version,base_score=score,severity='critical',provider='TEST_VENDOR',scope_key=version))
    db.flush()
    assert count(db,m.CvssAssessment)==2 and seed.claim.verification_status=='pending'

def test_patch_short_sha_rejected(db,seed):
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.PatchCandidate(vulnerability_id=seed.vuln.id,product_id=seed.products[0].id,source_id=seed.sources[0].id,observation_id=seed.observations[0].id,patch_type='commit',identity_key='abcdef',commit_sha='abcdef',first_seen_at=NOW));db.flush()

def test_benchmark_draft_is_not_gold_and_isolated(db):
    dataset=m.EvaluationDataset(dataset_key='SYNTHETIC-SCHEMA-TEST',revision_hash='0'*64,task_type='qa',split='development',as_of=NOW,rubric_version='TEST-1',description='Not benchmark performance')
    db.add(dataset);db.flush()
    case=m.EvaluationCase(dataset_id=dataset.id,case_key='TEST-QA-01',input_json={'question':'synthetic'},ground_truth=None,evidence_snapshot={},lineage_group='test-only')
    db.add(case);db.flush()
    run=m.EvaluationRun(dataset_id=dataset.id,started_at=NOW,finished_at=NOW,status='timeout',code_revision='TEST-1',configuration={},environment={'fixture':True});db.add(run);db.flush()
    result=m.EvaluationResult(dataset_id=dataset.id,run_id=run.id,case_id=case.id,prediction=None,correct=None,status='timeout',latency_ms=1000);db.add(result);db.flush()
    assert case.ground_truth_status=='draft' and result.correct is None and count(db,m.Vulnerability)==0

def test_timestamps_are_timezone_aware(db,seed):
    db.refresh(seed.raws[0]);assert seed.raws[0].retrieved_at.utcoffset().total_seconds()==0

def test_source_last_success_not_fabricated(db,seed):
    assert all(s.last_success_at is None and not s.enabled and s.status=='planned' for s in seed.sources)

def test_review_transaction_rolls_back_all_changes(db,seed):
    with pytest.raises(RuntimeError):
        with db.begin_nested():
            record_review(db,**review_values(seed))
            raise RuntimeError('Synthetic interruption before commit')
    db.refresh(seed.claim);db.refresh(seed.review)
    assert seed.claim.revision==1 and seed.review.status=='open'
    assert count(db,m.AuditLog)==0 and count(db,m.VerificationResult)==0

def test_wrong_raw_hash_is_rejected(db,seed):
    with pytest.raises(ValueError): store_raw(db,**raw_values(seed),content_hash='0'*64)
    assert count(db,m.RawDocument)==3

def test_unknown_component_can_persist_without_fake_range(db,seed):
    match=m.AssetVulnerabilityMatch(asset_component_id=seed.component.id,vulnerability_id=seed.vuln.id,package_identifier_id=seed.packages[0].id,match_status='unknown',version_at_evaluation='2.x',component_revision=1,claim_revision=1,matcher_version='TEST-1',reason_summary='Ambiguous version remains unknown',detected_at=NOW,last_evaluated_at=NOW)
    db.add(match);db.flush()
    assert match.matched_range_id is None and match.match_status=='unknown'

def test_agent_citation_pins_actual_claim_revision(db,seed):
    result=m.VerificationResult(claim_id=seed.claim.id,claim_revision=1,status='pending',verification_method='fixture_only',reason_summary='Unverified synthetic example',verified_at=NOW,verified_by_type='system',verified_by_id='TEST',decision_key='TEST-QA-REVISION')
    db.add(result);db.flush()
    run=m.AgentRun(actor_principal='test-analyst',user_request='Synthetic query',agent_type='TEST-ONLY',started_at=NOW,status='partial',result_summary='No actual Agent execution')
    db.add(run);db.flush()
    citation=m.AgentCitation(agent_run_id=run.id,evidence_id=seed.evidence[0].id,claim_id=seed.claim.id,citation_index=1,claim_revision=1,assertion_summary='Synthetic range from pinned raw')
    db.add(citation);db.flush()
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.AgentCitation(agent_run_id=run.id,evidence_id=seed.evidence[0].id,claim_id=seed.claim.id,citation_index=2,claim_revision=999,assertion_summary='Nonexistent revision'));db.flush()
    assert citation.claim_revision==1

def test_database_rejects_noncanonical_cve_spelling(db):
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.Vulnerability(canonical_id='cve-2099-9999001',title='SYNTHETIC noncanonical spelling'));db.flush()

def test_cve_identifier_cannot_hide_in_vendor_namespace(db,seed):
    with pytest.raises(IntegrityError),db.begin_nested():
        db.add(m.ExternalIdentifier(namespace='another-vendor',identifier_type='CVE',identifier_value=seed.vuln.canonical_id,normalized_value=seed.vuln.canonical_id,source_id=seed.sources[0].id));db.flush()
