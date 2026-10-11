"""Owner-filtered read adapters for existing root audits; no new tables or writes."""
from sqlalchemy import select, func
from app.db import models as m
from app.db.session import transaction
from app.orchestration.contracts import TYPE, NAMESPACE
from app.orchestration.store import decode


class InvestigationRepository:
    def __init__(self, engine):
        self.engine = engine

    def by_key(self, actor, key):
        with transaction(self.engine) as db:
            row = db.scalar(select(m.AgentRun).where(
                m.AgentRun.agent_type == TYPE, m.AgentRun.actor_principal == actor,
                m.AgentRun.details[NAMESPACE]['request_key'].astext == key))
            return decode(row, actor) if row is not None else None

    def history(self, actor, *, status, offset, limit, sort):
        filters = [m.AgentRun.agent_type == TYPE, m.AgentRun.actor_principal == actor]
        if status:
            filters.append(m.AgentRun.details[NAMESPACE]['context']['overall_status'].astext == status)
        order = (m.AgentRun.started_at.desc(), m.AgentRun.id.desc()) if sort == 'created_desc' else (
            m.AgentRun.started_at.asc(), m.AgentRun.id.asc())
        with transaction(self.engine) as db:
            total = db.scalar(select(func.count()).select_from(m.AgentRun).where(*filters))
            rows = db.scalars(select(m.AgentRun).where(*filters).order_by(*order).offset(offset).limit(limit)).all()
            return [decode(row, actor) for row in rows], total
