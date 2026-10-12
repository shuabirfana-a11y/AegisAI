"""Published HTTP-evaluation schema must match the actual Pydantic contracts."""
import subprocess
import sys
from pathlib import Path


def test_http_evaluation_schema_export_is_current():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(root / 'scripts/export_bench_http_schema.py'), '--check'],
        cwd=root, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS' in result.stdout
