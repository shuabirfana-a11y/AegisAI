"""A wrong DB setup must be refused before executing any regression tests."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DatabaseRegressionGateTests(unittest.TestCase):
    def gate(self):
        spec = importlib.util.spec_from_file_location(
            'database_regression_gate', ROOT / 'scripts/ci/run_database_tests.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_distinct_loopback_instances_are_accepted(self):
        validate = self.gate().validate_database_urls
        root = 'postgresql+psycopg://test@127.0.0.1:55447/aegis_phase5_test'
        runtime = 'postgresql+psycopg://test@127.0.0.1:55448/aegis_phase5_test'
        self.assertEqual(validate(root, runtime), (root, runtime))

    def test_same_database_refused_even_for_another_user_or_host_alias(self):
        validate = self.gate().validate_database_urls
        with self.assertRaisesRegex(ValueError, 'DISTINCT_TEST_DATABASES_REQUIRED'):
            validate('postgresql+psycopg://one@localhost:5432/aegis_phase5_test',
                     'postgresql+psycopg://two@127.0.0.1:5432/aegis_phase5_test')

    def test_missing_or_foreign_database_refused_without_disclosing_credentials(self):
        validate = self.gate().validate_database_urls
        valid = 'postgresql+psycopg://test@127.0.0.1:55448/aegis_phase5_test'
        for bad in ('', 'postgresql+psycopg://test:DO_NOT_LOG@127.0.0.1:5432/production',
                    'postgresql+psycopg://test@remote.example/aegis_phase5_test'):
            with self.subTest(bad=bool(bad)):
                with self.assertRaises(ValueError) as caught:
                    validate(bad, valid)
                self.assertNotIn('DO_NOT_LOG', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
