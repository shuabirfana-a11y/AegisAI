"""Exercise CI failure gates without changing source, databases or live services."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    path = ROOT / "scripts" / "ci" / (name + ".py")
    assert path.is_file(), "CI failure gate has not been implemented: " + name
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class RepositoryGateTests(unittest.TestCase):
    def test_documented_templates_and_source_are_allowed(self):
        gate = module("check_repository")
        self.assertEqual(
            gate.forbidden_paths(["backend/.env.example", "backend/app/main.py",
                                  "work/orchestration/baseline_hashes.json"]), []
        )

    def test_nested_secrets_and_local_data_are_rejected(self):
        gate = module("check_repository")
        paths = ["backend/.env", "a/.env.production", "tls/site.pem",
                 "frontend/node_modules/pkg/index.js", "data/demo.sqlite3",
                 "backend/.venv/pyvenv.cfg", "work/database_cluster/PG_VERSION",
                 "reports/run.log"]
        self.assertEqual(set(gate.forbidden_paths(paths)), set(paths))

    def test_unrelated_words_do_not_block_normal_source(self):
        gate = module("check_repository")
        self.assertEqual(gate.forbidden_paths(["docs/environment.md",
                         "backend/app/db/models.py", "docs/key-management.md"]), [])


class ContractGateTests(unittest.TestCase):
    def test_equal_contract_does_not_rewrite_the_export(self):
        gate = module("check_contracts")
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "contract.json"
            file.write_text('{"enum":["PENDING","CONFIRMED"]}\n', encoding="utf-8")
            before = file.read_bytes()
            gate.assert_json_matches({"enum": ["PENDING", "CONFIRMED"]}, file)
            self.assertEqual(file.read_bytes(), before)

    def test_state_enum_drift_is_rejected(self):
        gate = module("check_contracts")
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "contract.json"
            file.write_text('{"enum":["PENDING"]}', encoding="utf-8")
            with self.assertRaises(gate.ContractMismatch):
                gate.assert_json_matches({"enum": ["PENDING", "CONFIRMED"]}, file)

    def test_nullable_field_drift_is_rejected(self):
        gate = module("check_contracts")
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "contract.json"
            file.write_text('{"type":"string"}', encoding="utf-8")
            with self.assertRaises(gate.ContractMismatch):
                gate.assert_json_matches({"type": ["string", "null"]}, file)


if __name__ == "__main__":
    unittest.main()
