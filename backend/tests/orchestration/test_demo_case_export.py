"""Run the actual script's export expression after a real session has closed.

The expression is isolated to avoid fetching an advisory or changing a database
just to reproduce SQLAlchemy's transaction lifetime. No case fields are rebuilt
by this test: it executes the expression from the shipped preparation script.
"""
import ast
from pathlib import Path
from sqlalchemy import create_engine, Integer, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from app.db.session import transaction


class Base(DeclarativeBase):pass


class ExportRow(Base):
    __tablename__='case_export_fixture'
    id:Mapped[int]=mapped_column(Integer,primary_key=True)


def test_demo_case_can_export_after_transaction_expired_inventory_objects():
    engine=create_engine('sqlite://')
    Base.metadata.create_all(engine)
    try:
        with transaction(engine) as db:
            a=ExportRow(id=101);component=ExportRow(id=202)
            db.add_all([a,component]);db.flush()
            result={'asset_id':str(a.id),'component_id':str(component.id)}
        assert inspect(a).detached and inspect(a).expired
        script=Path(__file__).resolve().parents[3]/'demo/phase12d3/prepare_demo.py'
        parsed=ast.parse(script.read_text(encoding='utf-8'))
        export=next(node for node in parsed.body if isinstance(node,ast.Assign)
                    and any(isinstance(t,ast.Name) and t.id=='case' for t in node.targets))
        namespace={'result':result,'a':a,'component':component}
        exec(compile(ast.Module(body=[export],type_ignores=[]),str(script),'exec'),namespace)
        scope=namespace['case']['cases'][0]['request']['asset_scope']
        assert scope['asset_id']=='101' and scope['component_id']=='202'
    finally:engine.dispose()
