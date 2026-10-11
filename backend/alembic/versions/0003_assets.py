"""Phase8 additive asset context, inventory history and risk snapshots/queue."""
import json
from pathlib import Path
from alembic import op
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    for sql in json.loads(Path(__file__).with_name('0003_schema.json').read_text())['upgrade']:op.execute(sql)

def downgrade():
    for sql in json.loads(Path(__file__).with_name('0003_schema.json').read_text())['downgrade']:op.execute(sql)
