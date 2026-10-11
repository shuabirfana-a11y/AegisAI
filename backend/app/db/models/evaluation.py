from sqlalchemy import Boolean, CheckConstraint, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.db.base import Base
from app.db.types import Record, Mutable, fk, timestamp, enum_check

class EvaluationDataset(Record,Base):
    __tablename__='datasets'
    __table_args__=(UniqueConstraint('dataset_key','revision_hash'),enum_check('split','development validation final_test'),{'schema':'evaluation'})
    dataset_key=mapped_column(String(120),nullable=False); revision_hash=mapped_column(String(64),nullable=False)
    task_type=mapped_column(String(40),nullable=False); split=mapped_column(String(20),nullable=False)
    as_of=timestamp(False); frozen_at=timestamp()
    rubric_version=mapped_column(String(100),nullable=False)
    description=mapped_column(Text,nullable=False)

class EvaluationCase(Record,Base):
    __tablename__='cases'
    __table_args__=(UniqueConstraint('dataset_id','case_key'),UniqueConstraint('id','dataset_id'),enum_check('ground_truth_status','draft validated unknown'),{'schema':'evaluation'})
    dataset_id=fk('evaluation.datasets.id'); case_key=mapped_column(String(150),nullable=False)
    input_json=mapped_column(JSONB,nullable=False); ground_truth=mapped_column(JSONB)
    ground_truth_status=mapped_column(String(20),nullable=False,default='draft',server_default='draft')
    adjudicator=mapped_column(String(150)); ground_truth_reason=mapped_column(Text)
    evidence_snapshot=mapped_column(JSONB,nullable=False)
    lineage_group=mapped_column(String(200),nullable=False)

class EvaluationRun(Record,Base):
    __tablename__='runs'
    __table_args__=(UniqueConstraint('id','dataset_id'),enum_check('status','succeeded partial failed timeout cancelled'),CheckConstraint('finished_at>=started_at',name='time_order'),{'schema':'evaluation'})
    dataset_id=fk('evaluation.datasets.id')
    started_at=timestamp(False); finished_at=timestamp(False)
    status=mapped_column(String(20),nullable=False)
    code_revision=mapped_column(String(100),nullable=False); model_version=mapped_column(String(150))
    configuration=mapped_column(JSONB,nullable=False); environment=mapped_column(JSONB,nullable=False)

class EvaluationResult(Record,Base):
    __tablename__='results'
    __table_args__=(UniqueConstraint('run_id','case_id'),ForeignKeyConstraint(['run_id','dataset_id'],['evaluation.runs.id','evaluation.runs.dataset_id'],ondelete='RESTRICT',name='fk_result_run_dataset'),ForeignKeyConstraint(['case_id','dataset_id'],['evaluation.cases.id','evaluation.cases.dataset_id'],ondelete='RESTRICT',name='fk_result_case_dataset'),enum_check('status','succeeded partial failed timeout abstained unknown'),CheckConstraint('latency_ms>=0 AND (rubric_score IS NULL OR rubric_score BETWEEN 0 AND 2)',name='score_latency'),{'schema':'evaluation'})
    dataset_id=fk('evaluation.datasets.id'); run_id=fk('evaluation.runs.id'); case_id=fk('evaluation.cases.id')
    prediction=mapped_column(JSONB); correct=mapped_column(Boolean,nullable=True)
    status=mapped_column(String(20),nullable=False); latency_ms=mapped_column(Integer,nullable=False)
    rubric_score=mapped_column(Integer); error_summary=mapped_column(Text)

