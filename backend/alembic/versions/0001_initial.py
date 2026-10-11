"""Immutable Phase 5 schema snapshot; never imports current model metadata."""
import json
from pathlib import Path
from alembic import op
revision='0001'
down_revision=None
branch_labels=None
depends_on=None

def statements():
    return json.loads(Path(__file__).with_name('0001_schema.json').read_text(encoding='utf-8'))
def upgrade():
    for statement in statements()['upgrade']: op.execute(statement)
def downgrade():
    for statement in statements()['downgrade']: op.execute(statement)
