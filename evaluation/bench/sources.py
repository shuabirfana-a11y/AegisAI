"""Explicit, read-only acquisition of GitHub Advisory Database field projections."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


GHSA = re.compile(r"GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}\Z")


def project_advisory(payload, retrieved_at):
    identifier = payload.get("ghsa_id")
    if not isinstance(identifier, str) or not GHSA.fullmatch(identifier):
        raise ValueError("Invalid GitHub advisory identifier")
    cve = payload.get("cve_id")
    if cve is not None and not re.fullmatch(r"CVE-[0-9]{4}-[0-9]{4,}", cve):
        raise ValueError("Invalid CVE identifier")
    fields = ("ghsa_id", "cve_id", "summary", "severity", "published_at", "updated_at",
              "withdrawn_at", "cvss", "cvss_severities", "cwes", "references")
    record = {key: payload.get(key) for key in fields}
    record["vulnerabilities"] = [
        {"package": v["package"], "vulnerable_version_range": v.get("vulnerable_version_range"),
         "first_patched_version": v.get("first_patched_version")}
        for v in payload.get("vulnerabilities", [])
    ]
    return {
        "projection": "github-global-advisory-selected-fields-v1",
        "projection_note": "Selected original API fields. Description/PoC bodies omitted. No inferred facts.",
        "source_url": f"https://api.github.com/advisories/{identifier}",
        "retrieved_at": retrieved_at,
        "attribution": {"creator": "GitHub Advisory Database and credited upstream researchers",
                        "original_url": f"https://github.com/advisories/{identifier}",
                        "license": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
                        "license_source": "https://github.com/github/advisory-database/blob/main/LICENSE.md",
                        "changes": "Field projection; no description reproduced", "warranty": "AS-IS"},
        "record": record,
    }


def fetch_advisory(identifier):
    if not GHSA.fullmatch(identifier):
        raise ValueError("Invalid GitHub advisory identifier")
    env = dict(os.environ)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    for attempt in range(3):
        try:
            result = subprocess.run(["gh", "api", f"advisories/{identifier}"], env=env,
                                    capture_output=True, timeout=25)
        except subprocess.TimeoutExpired:
            if attempt < 2:
                continue
            raise RuntimeError("SOURCE_ACQUISITION_TIMEOUT") from None
        if result.returncode == 0:
            break
        transient = any(term in result.stderr.lower() for term in
                        (b"tls handshake timeout", b"connection reset", b"http 502", b"http 503"))
        if not transient or attempt == 2:
            # External stderr may contain account details; do not export it.
            raise RuntimeError("SOURCE_ACQUISITION_FAILED")
    payload = json.loads(result.stdout)
    if payload.get("ghsa_id") != identifier:
        raise ValueError("Source identity mismatch")
    projected = project_advisory(payload, datetime.now(timezone.utc).isoformat())
    projected["response_sha256"] = hashlib.sha256(result.stdout).hexdigest()
    return projected


def main():
    parser = argparse.ArgumentParser(description="Explicit source acquisition; no model or application calls")
    parser.add_argument("identifiers", nargs="+")
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "datasets"
    output = args.directory.resolve()
    if not output.is_relative_to(root):
        parser.error("Source output must be inside evaluation/datasets")
    output.mkdir(parents=True, exist_ok=True)
    for identifier in args.identifiers:
        target = output / f"{identifier}.json"
        if target.exists():
            parser.error("Frozen source already exists; create a new dataset revision")
        value = fetch_advisory(identifier)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"id": identifier, "cve": value["record"]["cve_id"],
                          "packages": value["record"]["vulnerabilities"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
