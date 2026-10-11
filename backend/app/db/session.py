import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

def make_engine(url=None):
    url=url or os.environ.get('AEGIS_DATABASE_URL')
    if not url: raise RuntimeError('AEGIS_DATABASE_URL is required; connection strings are never logged')
    parsed=make_url(url)
    if parsed.drivername!='postgresql+psycopg': raise ValueError('PostgreSQL with psycopg3 is required')
    return create_engine(parsed,pool_size=5,max_overflow=5,pool_pre_ping=True,echo=False,hide_parameters=True,
                         connect_args={'options':'-c timezone=UTC -c statement_timeout=30000'})

@contextmanager
def transaction(engine):
    with Session(engine) as session:
        with session.begin(): yield session
