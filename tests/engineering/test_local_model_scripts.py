"""Run Windows launch helpers; never install models or start a database in tests."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PWSH = shutil.which('pwsh')


def quoted(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(os.name == 'nt' and PWSH, 'Windows PowerShell runtime required')
class LocalModelScriptTests(unittest.TestCase):
    def run_ps(self, code):
        return subprocess.run([PWSH, '-NoProfile', '-NonInteractive', '-Command',
                               "$PSStyle.OutputRendering='PlainText'; " + code],
                              cwd=ROOT, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=20)

    def wrapper(self):
        path = ROOT / 'scripts/start-model-demo.ps1'
        self.assertTrue(path.is_file(), 'Phase12D startup helper is not implemented')
        return quoted(path)

    def test_missing_python_does_not_start_services(self):
        result = self.run_ps(f"& {self.wrapper()} -Mode MOCK -PythonPath 'X:/missing-aegis-python.exe'")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('MODEL_PYTHON_MISSING', result.stderr)

    def test_occupied_port_does_not_stop_existing_process(self):
        with socket.socket() as listener:
            try:
                listener.bind(('127.0.0.1', 8000))
            except OSError:
                self.skipTest('Existing user service occupies 8000; leave it untouched')
            listener.listen()
            result = self.run_ps(f"& {quoted(ROOT / 'scripts/start-local-demo.ps1')} -PythonPath {quoted(sys.executable)}")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('already in use', result.stderr)
            with socket.create_connection(('127.0.0.1', 8000), timeout=2):
                pass

    def test_environment_is_restored_after_start_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            starter = Path(temp) / 'starter.ps1'
            starter.write_text("param([string]$PythonPath)\nif ($env:MODEL_PROVIDER -ne 'openai_compatible' -or $env:MODEL_API_KEY) { throw 'BAD_CHILD_PROFILE' }\nthrow 'SYNTHETIC_START_FAILURE'\n", encoding='utf-8')
            code = f"""
            . {self.wrapper()}
            $env:MODEL_PROVIDER='SYNTHETIC-old-provider'
            $env:MODEL_API_KEY='SYNTHETIC-old-key'
            try {{ Start-AegisModelDemo -Mode REAL -PythonPath {quoted(sys.executable)} -StarterPath {quoted(starter)} }}
            catch {{ $failed=$_.Exception.Message -eq 'SYNTHETIC_START_FAILURE' }}
            @{{failed=$failed; provider_restored=($env:MODEL_PROVIDER -eq 'SYNTHETIC-old-provider'); key_restored=($env:MODEL_API_KEY -eq 'SYNTHETIC-old-key')}} | ConvertTo-Json -Compress
            """
            result = self.run_ps(code)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout.splitlines()[-1]), {'failed': True, 'provider_restored': True, 'key_restored': True})


if __name__ == '__main__':
    unittest.main()
