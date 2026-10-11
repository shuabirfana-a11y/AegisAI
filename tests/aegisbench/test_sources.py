"""Source projections retain field identity rather than guessing missing facts."""
import pytest
import json
import subprocess

from evaluation.bench.sources import project_advisory, fetch_advisory


def payload():
    return {"ghsa_id": "GHSA-53q9-r3pm-6pq6", "cve_id": "CVE-2025-32434",
            "summary": "Synthetic field projection test", "description": "must not export",
            "published_at": "2025-04-18T15:19:28Z", "updated_at": "2025-08-29T19:45:47Z",
            "cvss": {"score": None, "vector_string": None},
            "cvss_severities": {"cvss_v3": {"score": 0, "vector_string": None},
                                "cvss_v4": {"score": 9.3, "vector_string": "CVSS:4.0/test"}},
            "vulnerabilities": [{"package": {"ecosystem": "pip", "name": "torch"},
                "vulnerable_version_range": "< 2.6.0", "first_patched_version": "2.6.0"}],
            "cwes": [{"cwe_id": "CWE-502", "name": "Deserialization"}],
            "references": ["https://github.com/advisories/GHSA-53q9-r3pm-6pq6"]}


def test_projection_preserves_cvss_versions_and_excludes_free_text_description():
    value = project_advisory(payload(), "2026-10-11T00:00:00Z")
    assert "description" not in value["record"]
    assert value["record"]["cvss_severities"]["cvss_v3"]["vector_string"] is None
    assert value["record"]["cvss_severities"]["cvss_v4"]["score"] == 9.3
    assert value["source_url"].endswith("GHSA-53q9-r3pm-6pq6")


def test_invalid_identity_and_missing_cve_are_not_silently_invented():
    with pytest.raises(ValueError):
        project_advisory({**payload(), "ghsa_id": "../../local"}, "2026-10-11T00:00:00Z")
    # Real GHSA-only records remain CVE-less; the dataset builder decides eligibility.
    assert project_advisory({**payload(), "cve_id": None}, "2026-10-11T00:00:00Z")["record"]["cve_id"] is None


def test_transient_read_failure_retries_but_permanent_failure_does_not(monkeypatch):
    calls = []
    def run(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            return subprocess.CompletedProcess(args, 1, b"", b"TLS handshake timeout")
        return subprocess.CompletedProcess(args, 0, json.dumps(payload()).encode(), b"")
    monkeypatch.setattr("evaluation.bench.sources.subprocess.run", run)
    assert fetch_advisory("GHSA-53q9-r3pm-6pq6")["record"]["cve_id"] == "CVE-2025-32434"
    assert len(calls) == 2
    calls.clear()
    def forbidden(*args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1, b"", b"HTTP 403")
    monkeypatch.setattr("evaluation.bench.sources.subprocess.run", forbidden)
    with pytest.raises(RuntimeError):
        fetch_advisory("GHSA-53q9-r3pm-6pq6")
    assert len(calls) == 1
