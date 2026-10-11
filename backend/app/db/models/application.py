from sqlalchemy import Boolean, CheckConstraint, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.db.base import Base
from app.db.types import Record, Mutable, fk, timestamp, enum_check

class Asset(Record,Mutable,Base):
    __tablename__='assets'
    __table_args__=(UniqueConstraint('owner_principal','request_key'),enum_check('environment','production staging development unknown'),enum_check('exposure','internet internal development unknown'),{'schema':'app'})
    name=mapped_column(Text,nullable=False); asset_type=mapped_column(String(40),nullable=False)
    owner_principal=mapped_column(String(150),nullable=False)
    is_demo=mapped_column(Boolean,nullable=False,default=False,server_default='false')
    deleted_at=timestamp()
    environment=mapped_column(String(20),nullable=False,default='unknown',server_default='unknown')
    exposure=mapped_column(String(20),nullable=False,default='unknown',server_default='unknown')
    description=mapped_column(Text)
    request_key=mapped_column(String(150))

class AssetComponent(Record,Mutable,Base):
    __tablename__='asset_components'
    __table_args__=(UniqueConstraint('id','package_identifier_id'),ForeignKeyConstraint(['package_identifier_id','product_id'],['core.package_identifiers.id','core.package_identifiers.product_id'],ondelete='RESTRICT',name='fk_component_package_product'),enum_check('source','manual sbom scanner'),CheckConstraint('inventory_revision>0',name='positive_revision'),Index('ix_components_asset','asset_id'),Index('uq_components_inventory_key','asset_id','inventory_key',unique=True,postgresql_where=text('deleted_at IS NULL')),{'schema':'app'})
    asset_id=fk('app.assets.id'); product_id=fk('core.products.id',True); package_identifier_id=fk('core.package_identifiers.id',True)
    version=mapped_column(Text); raw_package_name=mapped_column(Text)
    source=mapped_column(String(20),nullable=False,default='manual',server_default='manual')
    inventory_revision=mapped_column(Integer,nullable=False,default=1,server_default='1')
    identity_status=mapped_column(String(20),nullable=False,default='unknown',server_default='unknown')
    deleted_at=timestamp()
    purl=mapped_column(Text); ecosystem=mapped_column(String(40)); namespace=mapped_column(Text)
    normalized_version=mapped_column(Text); resolution_method=mapped_column(String(40))
    inventory_key=mapped_column(String(128))
    first_seen_at=timestamp();last_seen_at=timestamp()

class AssetVulnerabilityMatch(Record,Base):
    __tablename__='asset_vulnerability_matches'
    __table_args__=(UniqueConstraint('asset_component_id','vulnerability_id','component_revision','claim_revision','matcher_version'),ForeignKeyConstraint(['asset_component_id','package_identifier_id'],['app.asset_components.id','app.asset_components.package_identifier_id'],ondelete='RESTRICT',name='fk_match_component_package'),ForeignKeyConstraint(['matched_range_id','vulnerability_id','package_identifier_id'],['core.affected_version_ranges.id','core.affected_version_ranges.vulnerability_id','core.affected_version_ranges.package_identifier_id'],ondelete='RESTRICT',name='fk_match_range_scope'),enum_check('match_status','affected not_affected unknown'),CheckConstraint("match_status='unknown' OR matched_range_id IS NOT NULL",name='certain_has_range'),CheckConstraint('component_revision>0 AND claim_revision>0',name='positive_revisions'),Index('ix_matches_component_status','asset_component_id','match_status'),{'schema':'app'})
    asset_component_id=fk('app.asset_components.id'); vulnerability_id=fk('core.vulnerabilities.id')
    package_identifier_id=fk('core.package_identifiers.id',True); matched_range_id=fk('core.affected_version_ranges.id',True); claim_id=fk('intel.claims.id',True)
    match_status=mapped_column(String(20),nullable=False)
    version_at_evaluation=mapped_column(Text)
    component_revision=mapped_column(Integer,nullable=False); claim_revision=mapped_column(Integer,nullable=False)
    matcher_version=mapped_column(String(60),nullable=False)
    reason_summary=mapped_column(Text,nullable=False)
    detected_at=timestamp(False); last_evaluated_at=timestamp(False)

class ReviewTask(Record,Mutable,Base):
    __tablename__='review_tasks'
    __table_args__=(enum_check('status','open assigned resolved deferred cancelled'),CheckConstraint('revision>0 AND priority BETWEEN 0 AND 4',name='revision_priority'),Index('ix_reviews_status_priority','status','priority'),{'schema':'app'})
    claim_id=fk('intel.claims.id')
    review_type=mapped_column(String(40),nullable=False)
    priority=mapped_column(Integer,nullable=False,default=2,server_default='2')
    status=mapped_column(String(20),nullable=False,default='open',server_default='open')
    reason=mapped_column(Text,nullable=False); assigned_to=mapped_column(String(150))
    resolved_at=timestamp(); resolution=mapped_column(String(30)); resolution_note=mapped_column(Text)
    before_state=mapped_column(JSONB); after_state=mapped_column(JSONB)
    revision=mapped_column(Integer,nullable=False,default=1,server_default='1')

class AuditLog(Record,Base):
    __tablename__='audit_logs'
    __table_args__=(UniqueConstraint('actor','request_key'),{'schema':'app'})
    actor=mapped_column(String(150),nullable=False); action=mapped_column(String(60),nullable=False)
    claim_id=fk('intel.claims.id'); review_task_id=fk('app.review_tasks.id',True); verification_result_id=fk('intel.verification_results.id',True)
    before_state=mapped_column(JSONB,nullable=False); after_state=mapped_column(JSONB,nullable=False)
    reason=mapped_column(Text,nullable=False); occurred_at=timestamp(False)
    request_key=mapped_column(String(150),nullable=False); request_hash=mapped_column(String(64),nullable=False)

class AgentRun(Record,Mutable,Base):
    __tablename__='agent_runs'
    __table_args__=(enum_check('status','queued running succeeded partial failed timeout cancelled'),CheckConstraint('duration_ms IS NULL OR duration_ms>=0',name='duration_nonnegative'),{'schema':'app'})
    actor_principal=mapped_column(String(150),nullable=False)
    user_request=mapped_column(Text,nullable=False); agent_type=mapped_column(String(60),nullable=False)
    context=mapped_column(JSONB); started_at=timestamp(False); finished_at=timestamp()
    status=mapped_column(String(20),nullable=False); duration_ms=mapped_column(Integer)
    result_summary=mapped_column(Text); error_summary=mapped_column(Text)

class ToolCallRecord(Record,Base):
    __tablename__='tool_call_records'
    __table_args__=(UniqueConstraint('agent_run_id','sequence_no','attempt'),CheckConstraint('sequence_no>=0 AND attempt>0 AND (duration_ms IS NULL OR duration_ms>=0)',name='position_duration'),enum_check('status','succeeded partial failed timeout cancelled'),{'schema':'app'})
    agent_run_id=fk('app.agent_runs.id')
    sequence_no=mapped_column(Integer,nullable=False); attempt=mapped_column(Integer,nullable=False,default=1,server_default='1')
    tool_name=mapped_column(String(100),nullable=False)
    input_summary=mapped_column(JSONB); output_summary=mapped_column(JSONB)
    started_at=timestamp(False); finished_at=timestamp(); duration_ms=mapped_column(Integer)
    status=mapped_column(String(20),nullable=False); error_summary=mapped_column(Text)

class AgentCitation(Record,Base):
    __tablename__='agent_citations'
    __table_args__=(UniqueConstraint('agent_run_id','citation_index'),CheckConstraint('citation_index>0 AND claim_revision>0',name='positive_position'),ForeignKeyConstraint(['evidence_id','claim_id'],['intel.evidence.id','intel.evidence.claim_id'],ondelete='RESTRICT',name='fk_citation_evidence_claim'),ForeignKeyConstraint(['claim_id','claim_revision'],['intel.verification_results.claim_id','intel.verification_results.claim_revision'],ondelete='RESTRICT',name='fk_citation_claim_revision'),{'schema':'app'})
    agent_run_id=fk('app.agent_runs.id'); evidence_id=fk('intel.evidence.id'); claim_id=fk('intel.claims.id')
    citation_index=mapped_column(Integer,nullable=False); claim_revision=mapped_column(Integer,nullable=False)
    assertion_summary=mapped_column(Text,nullable=False)
