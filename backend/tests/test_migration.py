"""Actual PostgreSQL DDL round trip; dedicated empty test database only."""
from pathlib import Path
import json,os,datetime
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect,text
from app.db.base import Base

ROOT=Path(__file__).resolve().parents[2]
SCHEMAS=['raw','core','intel','app','evaluation']

def test_actual_upgrade_downgrade_upgrade_matches_orm(engine):
    cfg=Config(str(ROOT/'backend/alembic.ini'))
    command.upgrade(cfg,'head')
    with engine.connect() as conn:
        assert sum(conn.scalar(text(f'SELECT count(*) FROM {t.fullname}')) for t in Base.metadata.sorted_tables)==0,'Migration test requires empty owned test database'
    command.downgrade(cfg,'base')
    with engine.connect() as conn:
        assert not set(SCHEMAS)&set(inspect(conn).get_schema_names())
    command.upgrade(cfg,'head')
    with engine.connect() as conn:
        actual={f'{s}.{t}' for s in SCHEMAS for t in inspect(conn).get_table_names(schema=s)}
        assert actual==set(Base.metadata.tables)
        assert conn.scalar(text('SELECT version_num FROM alembic_version'))=='0004'
        def include_object(obj,name,type_,reflected,compare_to):
            return getattr(obj,'schema',None)!='public' if type_=='table' else True
        context=MigrationContext.configure(conn,opts={'include_schemas':True,'compare_type':True,'include_object':include_object})
        drift=compare_metadata(context,Base.metadata)
        assert not drift,str(drift)
        protected=conn.scalar(text("SELECT count(*) FROM pg_trigger WHERE tgname='immutable_history' AND NOT tgisinternal"))
        assert protected==26
        version=conn.scalar(text('SELECT version()'))
    result={'kind':'REAL POSTGRESQL TEST; NOT SQLITE OR MOCK','passed':True,
            'tested_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'sequence':['initial upgrade 0004','downgrade base','verify all five schemas absent','upgrade 0004','ORM metadata comparison'],
            'tables':len(actual),'history_guards':26,'schema_drift':[],'postgresql':version,'head':'0004'}
    (ROOT/'work/database_migration_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
