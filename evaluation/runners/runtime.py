"""Bounded loopback HTTP adapter. No actor, asset, review, or source mutations."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4

from evaluation.dataset import assistant_payload

READ_ONLY_TOOLS = frozenset("search_vulnerabilities get_recent_intelligence get_vulnerability get_claims get_evidence get_timeline relation_query get_product find_vendor_advisories find_poc_candidates find_patch_candidates get_epss get_known_exploitation investigate_vulnerability get_verification_result get_evidence_for_claim list_assets get_asset get_asset_risk_changes get_asset_risks explain_asset_risk resolve_component get_remediation semantic_search get_system_status".split())


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RuntimeAdapter:
    def __init__(self, base_url="http://127.0.0.1:8000", *, token=None, timeout=30, poll_interval=0.1):
        url = urlsplit(base_url)
        if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
            raise ValueError("Runtime URL must be a plain HTTP loopback origin")
        if timeout <= 0 or poll_interval < 0:
            raise ValueError("Positive bounded timeout and nonnegative poll interval required")
        self.base_url = base_url.rstrip("/")
        self.token, self.timeout, self.poll_interval = token, timeout, poll_interval
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, path, *, payload=None, timeout=None):
        if not path.startswith("/api/v1/") or ".." in path or "?" in path:
            raise ValueError("Only local API paths are allowed")
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(self.base_url + path, data=body, headers=headers, method="POST" if body is not None else "GET")
        with self.opener.open(request, timeout=min(self.timeout, timeout if timeout is not None else self.timeout)) as response:
            return json.loads(response.read(8 * 1024 * 1024 + 1))

    @staticmethod
    def _failure(started, exc, *, error_type="TOOL_ERROR"):
        # Never echo response bodies, headers, credentials or database connection strings.
        detail = f"HTTP_{exc.code}" if isinstance(exc, HTTPError) else type(exc).__name__
        return {"status": "FAILED", "actual": {}, "error_type": error_type, "error": detail,
                "latency_ms": (time.perf_counter() - started) * 1000}

    def tool(self, name, arguments):
        if name not in READ_ONLY_TOOLS or arguments.get("refresh"):
            raise ValueError("Benchmark tool adapter allows only read-only local calls")
        started = time.perf_counter()
        try:
            value = self.request("/api/v1/tools/" + name, payload=arguments)
            status = {"success": "COMPLETED", "no_result": "COMPLETED", "partial": "PARTIAL", "failed": "FAILED"}.get(value.get("status"), "FAILED")
            result = {"status": status, "actual": value, "latency_ms": (time.perf_counter() - started) * 1000}
            if status == "FAILED":
                result.update(error_type="TOOL_ERROR", error="Tool reported failure or invalid envelope")
            return result
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            return self._failure(started, exc)

    def assistant(self, question, *, mode="auto"):
        started = time.perf_counter()
        payload = assistant_payload({**question, "mode": mode}, request_key="aegisbench-" + str(uuid4()))
        try:
            value = self.request("/api/v1/assistant/query", payload=payload)
            run_id = value.get("run_id") or value.get("id")
            if not run_id or not all(c.isalnum() or c in "-_" for c in run_id):
                raise ValueError("Missing or malformed asynchronous run ID")
            terminal = {"COMPLETED", "WAITING_REVIEW", "FAILED", "succeeded", "partial", "failed"}
            while value.get("status") not in terminal:
                elapsed = time.perf_counter() - started
                if elapsed >= self.timeout:
                    return {"status": "FAILED", "actual": value, "error_type": "TOOL_ERROR", "error": "ASSISTANT_POLL_TIMEOUT",
                            "run_id": run_id, "latency_ms": elapsed * 1000}
                if self.poll_interval:
                    time.sleep(min(self.poll_interval, max(0, self.timeout - elapsed)))
                value = self.request("/api/v1/assistant/runs/" + run_id, timeout=max(0.001, self.timeout - (time.perf_counter() - started)))
            status = "FAILED" if value["status"] in {"FAILED", "failed"} else "PARTIAL" if value["status"] in {"WAITING_REVIEW", "partial"} else "COMPLETED"
            result = {"status": status, "actual": value.get("result") or {}, "run_id": run_id,
                      "runtime_status": value["status"], "latency_ms": (time.perf_counter() - started) * 1000}
            try:
                result["trace"] = self.request("/api/v1/assistant/runs/" + run_id + "/trace")
            except (HTTPError, URLError, TimeoutError, ValueError, OSError):
                result["trace"] = None
                result["trace_warning"] = "Actual trace unavailable; no counters inferred"
            if status == "FAILED":
                result.update(error_type="INTEGRATION_ERROR", error="Assistant completed with failure")
            return result
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            return self._failure(started, exc, error_type="INTEGRATION_ERROR")
