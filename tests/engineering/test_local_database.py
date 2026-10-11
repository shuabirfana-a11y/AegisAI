"""Launcher lifecycle checks; no PostgreSQL process or database is touched."""
import importlib.util
import json
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPT = Path(__file__).resolve().parents[2] / 'backend/scripts/local_database.py'


def load_script(driver):
    spec = importlib.util.spec_from_file_location('local_database_probe', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    original = Path.read_text

    def read_text(path, *args, **kwargs):
        if path.name == 'postgresql_runtime.json':
            return json.dumps({'bin': '/unused/postgresql/bin'})
        return original(path, *args, **kwargs)

    with patch.dict('sys.modules', {'psycopg': driver}), patch.object(Path, 'read_text', read_text):
        spec.loader.exec_module(module)
    return module


class LocalDatabaseLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.driver = types.ModuleType('psycopg')
        self.driver.connect = MagicMock()
        self.driver.sql = MagicMock()
        connection = self.driver.connect.return_value.__enter__.return_value
        connection.execute.return_value.fetchone.return_value = ('fixture-only',)
        self.module = load_script(self.driver)
        self.module.ROOT = Path(self.temp.name).resolve()
        self.module.DATA = self.module.ROOT / 'work/phase6_cluster'
        self.module.DATA.mkdir(parents=True)
        (self.module.DATA / 'PG_VERSION').write_text('17\n', encoding='utf-8')
        (self.module.DATA / 'postmaster.pid').write_text('999999\n', encoding='utf-8')
        (self.module.ROOT / 'work/postgresql_runtime.json').write_text(
            json.dumps({'bin': '/unused/postgresql/bin'}), encoding='utf-8')

    def run_action(self, action, codes):
        with patch.object(self.module.subprocess, 'run', side_effect=[
            subprocess.CompletedProcess([], code) for code in codes
        ]) as execute:
            try:
                self.module.main(action)
            except RuntimeError as exc:
                self.fail('Expected successful lifecycle operation: ' + str(exc))
        return [call.args[0] for call in execute.call_args_list]

    def test_stale_pid_marker_does_not_prevent_start(self):
        commands = self.run_action('start', [3, 0])
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][-1], 'status')
        self.assertIn('start', commands[1])
        self.assertTrue((self.module.DATA / 'PG_VERSION').exists())

    def test_live_server_is_not_started_twice(self):
        commands = self.run_action('start', [0])
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][-1], 'status')

    def test_status_probe_error_does_not_trigger_start_or_connect(self):
        with patch.object(self.module.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 1)):
            with self.assertRaises(RuntimeError):
                self.module.main('start')
        self.driver.connect.assert_not_called()

    def test_database_connection_has_finite_timeout(self):
        self.run_action('start', [0])
        timeout = self.driver.connect.call_args.kwargs.get('connect_timeout')
        self.assertIsInstance(timeout, int)
        self.assertGreater(timeout, 0)
        self.assertLessEqual(timeout, 10)

    def test_stopping_already_stopped_cluster_is_safe(self):
        commands = self.run_action('stop', [3])
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][-1], 'status')
        self.driver.connect.assert_not_called()

    def test_live_stop_uses_owned_cluster(self):
        commands = self.run_action('stop', [0, 0])
        self.assertEqual(commands[0][-1], 'status')
        self.assertIn('stop', commands[1])
        self.assertIn(str(self.module.DATA), commands[1])


if __name__ == '__main__':
    unittest.main()
