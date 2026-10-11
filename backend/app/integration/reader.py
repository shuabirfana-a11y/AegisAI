"""History reads only the sealed Gate audit, independent of current live sources."""
from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.integration.store import TYPE,decode

class IntegrationReader:
    def __init__(self,engine):self.engine=engine
    def _read(self,id,actor):
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(str(id)),m.AgentRun.actor_principal==actor,m.AgentRun.agent_type==TYPE))
            if row is None:raise LookupError('Integration result not available')
            return decode(row,actor)
    def read(self,id,*,actor):return self._read(id,actor)[1]
    def read_trace(self,id,*,actor):return self._read(id,actor)[2]
