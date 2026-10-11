import os
from alembic import context
from app.db.base import Base
from app.db import models
from app.db.session import make_engine

metadata=Base.metadata
if context.is_offline_mode():
    context.configure(url=os.environ['AEGIS_DATABASE_URL'],target_metadata=metadata,
                      literal_binds=True,include_schemas=True,compare_type=True)
    with context.begin_transaction(): context.run_migrations()
else:
    engine=make_engine()
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=metadata,
                          include_schemas=True,compare_type=True)
        with context.begin_transaction(): context.run_migrations()
    engine.dispose()
