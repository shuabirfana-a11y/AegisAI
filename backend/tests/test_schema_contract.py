from app.db.base import Base
from app.db import models

def test_phase5_has_43_explicit_domain_tables():
    """Missing normalized entities, evidence links or benchmark tables breaks this."""
    original=set(Base.metadata.tables)-{'app.enrichment_jobs','intel.conflicts','app.asset_inventory_events','app.asset_risk_snapshots','app.asset_risk_changes','app.asset_recompute_jobs','intel.knowledge_embeddings'}
    assert len(original) == 43, 'Phase 5 domain tables have not been implemented'

def test_composite_unique_constraint_names_do_not_collide():
    from sqlalchemy import UniqueConstraint
    for table in Base.metadata.tables.values():
        names=[c.name for c in table.constraints if isinstance(c,UniqueConstraint)]
        assert len(names)==len(set(names)),table.fullname
