"""Fail-closed PostgreSQL regression entry; never creates/deletes databases.

Two separately provisioned empty local test instances are required. Committed
Runtime fixtures must not share the rollback-only suite's database.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
CRITICAL_TESTS = [
    'tests/test_api.py', 'tests/test_collectors_sync.py', 'tests/test_database.py',
    'tests/test_ingestion_database.py', 'tests/test_migration.py',
    'tests/test_semantic_empty_index.py',
    'tests/test_phase14_api.py', 'tests/test_phase14_storage.py',
    'tests/test_phase14b2_agent.py', 'tests/test_phase14b2_pipeline.py',
    'tests/test_phase7_api_jobs.py', 'tests/test_phase7_enrichers.py',
    'tests/test_phase8_api_events.py', 'tests/test_phase8_final_regressions.py',
    'tests/investigation_api/test_bench_http.py',
    'tests/orchestration/test_failure_cancel.py', 'tests/orchestration/test_handoff.py',
    'tests/investigation_api/test_multi_asset.py',
    'tests/investigation_api/test_multi_asset_database.py',
    'tests/investigation_api/test_multi_asset_chain.py',
]


def validate_database_urls(root_url, runtime_url):
    identities = []
    for value in (root_url, runtime_url):
        try:
            parsed = urlsplit(value or '')
            if (parsed.scheme != 'postgresql+psycopg'
                    or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
                    or parsed.path != '/aegis_phase5_test' or parsed.query or parsed.fragment):
                raise ValueError()
            # Credentials and localhost aliases do not make different databases.
            identities.append((parsed.port or 5432, parsed.path))
        except (ValueError, TypeError):
            raise ValueError('EXPLICIT_LOCAL_TEST_DATABASE_REQUIRED') from None
    if identities[0] == identities[1]:
        raise ValueError('DISTINCT_TEST_DATABASES_REQUIRED')
    return root_url, runtime_url


def prepare_empty_database(url):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import func, select
    from app.db.base import Base
    from app.db.session import make_engine
    import app.db.models  # register metadata
    cfg = Config(str(ROOT / 'backend/alembic.ini'))
    cfg.set_main_option('script_location', str(ROOT / 'backend/alembic'))
    # Alembic env reads only this explicit test URL. No default developer DB.
    os.environ['AEGIS_DATABASE_URL'] = url
    command.upgrade(cfg, 'head')
    engine = make_engine(url)
    try:
        with engine.connect() as conn:
            if any(conn.scalar(select(func.count()).select_from(table))
                   for table in Base.metadata.sorted_tables):
                raise ValueError('EMPTY_TEST_DATABASE_REQUIRED; provision a fresh test instance')
    finally:
        engine.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true', help='All backend/tests, no deselection')
    parser.add_argument('--output', default='work/database-regression')
    args = parser.parse_args(argv)
    try:
        root_url, runtime_url = validate_database_urls(
            os.environ.get('AEGIS_TEST_DATABASE_URL'),
            os.environ.get('AEGIS_RUNTIME_TEST_DATABASE_URL'))
        sys.path.insert(0, str(ROOT / 'backend'))
        prepare_empty_database(root_url)
        prepare_empty_database(runtime_url)
    except (ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    output = (ROOT / args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.environ.update(AEGIS_DATABASE_URL=root_url, MODEL_PROVIDER='mock',
                      MODEL_EMBEDDING_PROVIDER='mock', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    selected = [] if args.full else CRITICAL_TESTS
    command = [sys.executable, '-m', 'pytest', '-q', *selected,
               '--junitxml=' + str(output / 'results.xml')]
    (output / 'entry.json').write_text(json.dumps({
        'scope': 'FULL_BACKEND' if args.full else 'DATABASE_CRITICAL_REGRESSION',
        'test_paths': selected or ['tests'], 'deselected': 0, 'model_mode': 'MOCK',
        'databases': 'INDEPENDENT_EMPTY_LOCAL_TEST_INSTANCES',
        'python': sys.version, 'interpreter': sys.executable,
        'command': command, 'business_accuracy': 'NOT_MEASURED'}, indent=2), encoding='utf-8')
    print('Isolated PostgreSQL regression; scope=' + ('FULL_BACKEND' if args.full else 'CRITICAL'))
    # Preserve pytest's exact exit code, including collection/setup failures.
    return subprocess.run(command, cwd=ROOT / 'backend', env=os.environ.copy()).returncode


if __name__ == '__main__':
    raise SystemExit(main())
