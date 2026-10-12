"""Full regression in an explicitly configured, empty dedicated test database."""
import os
import sys
from pathlib import Path
import pytest
from sqlalchemy.engine import make_url

ROOT=Path(__file__).resolve().parents[2]
url=os.environ.get('AEGIS_TEST_DATABASE_URL')
if not url or make_url(url).database!='aegis_phase5_test':
    raise SystemExit('Configure an EMPTY dedicated aegis_phase5_test database first')
os.environ.update(AEGIS_DATABASE_URL=url,AEGIS_RUNTIME_TEST_DATABASE_URL=url,
    MODEL_PROVIDER='mock',MODEL_NAME='mock-text-v1',MODEL_EMBEDDING_PROVIDER='mock',
    MODEL_EMBEDDING_NAME='mock-embedding-v1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONIOENCODING='utf-8')
for name in ('MODEL_API_KEY','MODEL_API_BASE','MODEL_EMBEDDING_API_KEY','AEGIS_ASSET_TOKEN','AEGIS_ASSET_OWNER'):
    os.environ.pop(name,None)


class EmptyFirst:
    def pytest_collection_modifyitems(self,items):
        def order(item):
            if item.nodeid.startswith('tests/test_migration.py'):return (0,item.nodeid)
            if item.nodeid.startswith('tests/test_database.py'):return (1,item.nodeid)
            if item.nodeid.startswith('tests/test_ingestion_database.py'):return (2,item.nodeid)
            if len(Path(str(item.fspath)).relative_to(ROOT/'backend/tests').parts)==1:return (3,item.nodeid)
            return (4,item.nodeid)
        items.sort(key=order)


(ROOT/'work/phase12d3').mkdir(parents=True,exist_ok=True)
os.chdir(ROOT/'backend');sys.path.insert(0,str(ROOT/'backend'))
print('Full backend collection; empty migration/count contracts first; no skips or deselections.')
raise SystemExit(pytest.main(['-q','--junitxml='+str(ROOT/'work/phase12d3/full-regression-final.xml')],plugins=[EmptyFirst()]))
