from sqlalchemy import String,Text,Integer,UniqueConstraint,CheckConstraint,Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.db.base import Base
from app.db.types import Record,Mutable,fk,timestamp,enum_check

class AssetInventoryEvent(Record,Base):
    __tablename__='asset_inventory_events'
    __table_args__=(UniqueConstraint('asset_id','request_key'),Index('ix_inventory_events_asset','asset_id','occurred_at'),{'schema':'app'})
    asset_id=fk('app.assets.id');component_id=fk('app.asset_components.id',True)
    event_type=mapped_column(String(40),nullable=False);actor=mapped_column(String(150),nullable=False)
    request_key=mapped_column(String(150),nullable=False);request_hash=mapped_column(String(64),nullable=False)
    occurred_at=timestamp(False);payload=mapped_column(JSONB,nullable=False)

class AssetRiskSnapshot(Record,Base):
    __tablename__='asset_risk_snapshots'
    __table_args__=(UniqueConstraint('snapshot_key'),Index('ix_risk_snapshot_component','component_id','created_at'),{'schema':'app'})
    asset_id=fk('app.assets.id');component_id=fk('app.asset_components.id');vulnerability_id=fk('core.vulnerabilities.id')
    match_id=fk('app.asset_vulnerability_matches.id');snapshot_key=mapped_column(String(128),nullable=False)
    match_status=mapped_column(String(30),nullable=False);priority=mapped_column(String(10),nullable=False)
    inventory_revision=mapped_column(Integer,nullable=False)
    intelligence_fingerprint=mapped_column(String(64),nullable=False)
    payload=mapped_column(JSONB,nullable=False)

class AssetRiskChange(Record,Base):
    __tablename__='asset_risk_changes'
    __table_args__=(UniqueConstraint('event_key'),Index('ix_risk_changes_asset','asset_id','occurred_at'),{'schema':'app'})
    asset_id=fk('app.assets.id');component_id=fk('app.asset_components.id');vulnerability_id=fk('core.vulnerabilities.id')
    previous_snapshot_id=fk('app.asset_risk_snapshots.id',True);snapshot_id=fk('app.asset_risk_snapshots.id')
    event_type=mapped_column(String(50),nullable=False);event_key=mapped_column(String(128),nullable=False)
    occurred_at=timestamp(False);before_state=mapped_column(JSONB);after_state=mapped_column(JSONB,nullable=False)

class AssetRecomputeJob(Record,Mutable,Base):
    __tablename__='asset_recompute_jobs'
    __table_args__=(UniqueConstraint('job_key'),enum_check('status','queued running succeeded failed'),CheckConstraint('attempt>=0 AND attempt<=3',name='asset_job_attempt'),Index('ix_asset_jobs_due','status','created_at'),{'schema':'app'})
    asset_id=fk('app.assets.id');intelligence_event_id=fk('intel.intelligence_events.id',True)
    job_key=mapped_column(String(150),nullable=False);status=mapped_column(String(20),nullable=False,default='queued',server_default='queued')
    attempt=mapped_column(Integer,nullable=False,default=0,server_default='0')
    started_at=timestamp();finished_at=timestamp();error_code=mapped_column(String(60))
