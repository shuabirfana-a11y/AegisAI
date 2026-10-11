from sqlalchemy import Boolean,CheckConstraint,ForeignKeyConstraint,Integer,String,Text,UniqueConstraint,Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.db.base import Base
from app.db.types import Record,Mutable,fk,timestamp,enum_check

class EnrichmentJob(Record,Mutable,Base):
    __tablename__='enrichment_jobs'
    __table_args__=(enum_check('status','queued running success partial no_result failed conflict cancelled'),
        CheckConstraint('attempt>0 AND (duration_ms IS NULL OR duration_ms>=0)',name='attempt_duration'),
        CheckConstraint('finished_at IS NULL OR (started_at IS NOT NULL AND finished_at>=started_at)',name='time_order'),
        Index('ix_enrichment_jobs_due','status','scheduled_at'),Index('ix_enrichment_jobs_target','vulnerability_id','enrichment_type'),{'schema':'app'})
    vulnerability_id=fk('core.vulnerabilities.id')
    enrichment_type=mapped_column(String(40),nullable=False)
    status=mapped_column(String(20),nullable=False,default='queued',server_default='queued')
    scheduled_at=timestamp(False);started_at=timestamp();finished_at=timestamp()
    attempt=mapped_column(Integer,nullable=False,default=1,server_default='1')
    error_code=mapped_column(String(50));retryable=mapped_column(Boolean,nullable=False,default=False,server_default='false')
    trace_id=mapped_column(String(36),nullable=False)
    duration_ms=mapped_column(Integer);result=mapped_column(JSONB)

class ConflictRecord(Record,Mutable,Base):
    __tablename__='conflicts'
    __table_args__=(UniqueConstraint('conflict_key'),
        ForeignKeyConstraint(['claim_a_id','vulnerability_id'],['intel.claims.id','intel.claims.vulnerability_id'],ondelete='RESTRICT',name='fk_conflict_a_root'),
        ForeignKeyConstraint(['claim_b_id','vulnerability_id'],['intel.claims.id','intel.claims.vulnerability_id'],ondelete='RESTRICT',name='fk_conflict_b_root'),
        ForeignKeyConstraint(['claim_a_id','scope_key'],['intel.claims.id','intel.claims.scope_key'],ondelete='RESTRICT',name='fk_conflict_a_scope'),
        ForeignKeyConstraint(['claim_b_id','scope_key'],['intel.claims.id','intel.claims.scope_key'],ondelete='RESTRICT',name='fk_conflict_b_scope'),
        CheckConstraint('claim_a_id<>claim_b_id',name='distinct_claims'),enum_check('status','open resolved deferred'),
        Index('ix_conflicts_target_status','vulnerability_id','status'),{'schema':'intel'})
    conflict_key=mapped_column(String(200),nullable=False)
    vulnerability_id=fk('core.vulnerabilities.id')
    claim_a_id=fk('intel.claims.id');claim_b_id=fk('intel.claims.id')
    scope_key=mapped_column(String(128),nullable=False)
    conflict_type=mapped_column(String(50),nullable=False)
    detected_at=timestamp(False)
    status=mapped_column(String(20),nullable=False,default='open',server_default='open')
    review_task_id=fk('app.review_tasks.id',True)
    resolution=mapped_column(JSONB);resolved_at=timestamp();resolved_by=mapped_column(String(150))
