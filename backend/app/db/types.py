from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

def utcnow(): return datetime.now(timezone.utc)
def fk(target, nullable=False):
    return mapped_column(PGUUID(as_uuid=True),ForeignKey(target,ondelete='RESTRICT'),nullable=nullable)
def enum_check(column, values):
    allowed=','.join("'"+v+"'" for v in values.split())
    return CheckConstraint(f'{column} IN ({allowed})',name=column+'_values')
def timestamp(nullable=True): return mapped_column(DateTime(timezone=True),nullable=nullable)

class Record:
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4,server_default=text('gen_random_uuid()'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,default=utcnow,server_default=text('now()'))
    details: Mapped[dict] = mapped_column('metadata',JSONB,nullable=False,default=dict,server_default=text("'{}'::jsonb"))

class Mutable:
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,default=utcnow,onupdate=utcnow,server_default=text('now()'))

VERIFY='pending confirmed insufficient conflict rejected'
SEVERITY='critical high medium low info unknown'
CANDIDATE='candidate confirmed rejected unknown'
