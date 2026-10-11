from sqlalchemy import Boolean, CheckConstraint, ForeignKeyConstraint, Integer, LargeBinary, String, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.db.base import Base
from app.db.types import Record, Mutable, fk, timestamp, enum_check

class Source(Record,Mutable,Base):
    __tablename__='sources'
    __table_args__=(UniqueConstraint('source_key'),enum_check('authority_level','official authoritative secondary community'),enum_check('status','planned deferred running succeeded partial failed rate_limited stale need_review'),CheckConstraint('update_interval >= 0',name='interval_nonnegative'),{'schema':'raw'})
    source_key=mapped_column(String(100),nullable=False)
    name=mapped_column(Text,nullable=False)
    source_type=mapped_column(String(40),nullable=False)
    category=mapped_column(String(60),nullable=False)
    authority_level=mapped_column(String(20),nullable=False)
    authority_scope=mapped_column(Text,nullable=False)
    acquisition_method=mapped_column(String(30),nullable=False)
    base_url=mapped_column(Text,nullable=False)
    enabled=mapped_column(Boolean,nullable=False,server_default='false',default=False)
    update_interval=mapped_column(Integer,nullable=False,default=3600,server_default='3600')
    last_sync_at=timestamp(); last_success_at=timestamp()
    status=mapped_column(String(20),nullable=False,default='planned',server_default='planned')
    license_scope=mapped_column(Text,nullable=False,default='unknown',server_default='unknown')
    checkpoint=mapped_column(JSONB,nullable=True)
    coverage_scope=mapped_column(JSONB,nullable=True)

class RawDocument(Record,Base):
    __tablename__='raw_documents'
    __table_args__=(UniqueConstraint('source_id','external_id','content_hash',name='uq_raw_revision'),UniqueConstraint('id','source_id'),CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'",name='sha256'),CheckConstraint('octet_length(raw_payload) <= 16777216',name='inline_size_limit'),Index('ix_raw_documents_identity_time','source_id','external_id','retrieved_at'),{'schema':'raw'})
    source_id=fk('raw.sources.id')
    external_id=mapped_column(Text,nullable=False)
    source_url=mapped_column(Text,nullable=False)
    published_at=timestamp(); modified_at=timestamp(); retrieved_at=timestamp(False)
    content_type=mapped_column(String(100),nullable=False)
    raw_payload=mapped_column(LargeBinary,nullable=False)
    parsed_payload=mapped_column(JSONB,nullable=True)
    content_hash=mapped_column(String(64),nullable=False)
    completeness=mapped_column(String(20),nullable=False,default='unknown',server_default='unknown')
    publisher=mapped_column(Text,nullable=False)
    license_scope=mapped_column(Text,nullable=False,default='unknown',server_default='unknown')

class SyncRun(Record,Base):
    __tablename__='sync_runs'
    __table_args__=(UniqueConstraint('id','source_id'),enum_check('status','queued running succeeded partial failed rate_limited cancelled need_review'),CheckConstraint('records_fetched>=0 AND records_created>=0 AND records_updated>=0 AND records_skipped>=0 AND records_failed>=0',name='counts_nonnegative'),CheckConstraint('finished_at IS NULL OR finished_at >= started_at',name='time_order'),CheckConstraint("status NOT IN ('succeeded','partial','failed','cancelled') OR finished_at IS NOT NULL",name='terminal_finished'),CheckConstraint("status <> 'succeeded' OR records_failed=0",name='success_no_failed'),Index('ix_sync_runs_source_started','source_id','started_at'),{'schema':'raw'})
    source_id=fk('raw.sources.id')
    started_at=timestamp(False); finished_at=timestamp()
    status=mapped_column(String(20),nullable=False,default='queued',server_default='queued')
    records_fetched=mapped_column(Integer,nullable=False,default=0,server_default='0')
    records_created=mapped_column(Integer,nullable=False,default=0,server_default='0')
    records_updated=mapped_column(Integer,nullable=False,default=0,server_default='0')
    records_skipped=mapped_column(Integer,nullable=False,default=0,server_default='0')
    records_failed=mapped_column(Integer,nullable=False,default=0,server_default='0')
    cursor_before=mapped_column(JSONB); cursor_after=mapped_column(JSONB)
    mode=mapped_column(String(20),nullable=False,default='incremental',server_default='incremental')
    coverage_scope=mapped_column(JSONB); known_gaps=mapped_column(JSONB)
    error_summary=mapped_column(Text)
    retry_of_id=fk('raw.sync_runs.id',True)

class SourceObservation(Record,Base):
    __tablename__='source_observations'
    __table_args__=(UniqueConstraint('id','raw_document_id','source_id'),ForeignKeyConstraint(['raw_document_id','source_id'],['raw.raw_documents.id','raw.raw_documents.source_id'],ondelete='RESTRICT',name='fk_observation_raw_source'),ForeignKeyConstraint(['sync_run_id','source_id'],['raw.sync_runs.id','raw.sync_runs.source_id'],ondelete='RESTRICT',name='fk_observation_run_source'),enum_check('parse_status','pending parsed unsupported failed'),CheckConstraint('http_status IS NULL OR http_status<>304 OR raw_document_id IS NOT NULL',name='304_requires_cached_body'),Index('ix_observations_raw_time','raw_document_id','retrieved_at'),{'schema':'raw'})
    source_id=fk('raw.sources.id')
    raw_document_id=fk('raw.raw_documents.id',True)
    sync_run_id=fk('raw.sync_runs.id',True)
    external_id=mapped_column(Text,nullable=False)
    record_type=mapped_column(String(30),nullable=False)
    retrieved_at=timestamp(False)
    http_status=mapped_column(Integer,nullable=True)
    raw_locator=mapped_column(JSONB,nullable=True)
    lineage_key=mapped_column(Text,nullable=False)
    publisher=mapped_column(Text,nullable=False)
    upstream_observation_id=fk('raw.source_observations.id',True)
    normalizer_version=mapped_column(String(60))
    normalized_payload=mapped_column(JSONB)
    parse_status=mapped_column(String(20),nullable=False,default='pending',server_default='pending')
