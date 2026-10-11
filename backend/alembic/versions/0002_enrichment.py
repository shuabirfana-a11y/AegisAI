"""Phase7 additive job/conflict storage and explicit rejected verification.

DDL is frozen in 0002_schema.json; published0001 is not edited.
"""
import json
from pathlib import Path
from alembic import op

revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None

def upgrade():
    ddl=json.loads(Path(__file__).with_name('0002_schema.json').read_text(encoding='utf-8'))
    for statement in ddl['upgrade']:op.execute(statement)

def downgrade():
    ddl=json.loads(Path(__file__).with_name('0002_schema.json').read_text(encoding='utf-8'))
    for statement in ddl['downgrade']:op.execute(statement)
