"""Optional setup for the real Python Orchestrator, guarded from production data."""
import json
import os
from pathlib import Path

from .adapters import AegisAIAdapter, backend_imports
from .data import sha256


class MemoryRecords:
    def __init__(self):
        self.records = []

    def write(self, record):
        self.records.append(record)


def configured_gateway():
    backend_imports()
    from app.llm.config import ModelConfig
    from app.llm.gateway import ModelGateway
    env = dict(os.environ)
    # Baseline text generation does not require embeddings or model downloads.
    env.update(MODEL_EMBEDDING_PROVIDER="mock", MODEL_EMBEDDING_NAME="mock-embedding-v1", MODEL_EMBEDDING_DIMENSION="384")
    config = ModelConfig.from_env(env)
    if config.provider == "mock":
        return None
    return ModelGateway(config, record_sink=MemoryRecords())


def native_adapter(gateway, data, requests_path, run_id):
    if gateway is None:
        return AegisAIAdapter()
    backend_imports()
    from sqlalchemy.engine import make_url
    from .schema import reject_labels
    url = make_url(os.environ.get("AEGIS_BENCH_DATABASE_URL", ""))
    if (url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", "::1"}
            or url.database not in {"aegis_bench_test", "aegis_phase5_test"} or url.query):
        raise ValueError("NATIVE_DEDICATED_LOCAL_BENCH_DATABASE_REQUIRED")
    path = Path(requests_path).resolve()
    root = Path(__file__).resolve().parents[1] / "experiments"
    if not path.is_relative_to(root):
        raise ValueError("NATIVE_REQUEST_MAP_OUTSIDE_EXPERIMENTS")
    mapping = json.loads(path.read_text(encoding="utf-8-sig"))
    reject_labels(mapping)
    actor = os.environ.get("AEGIS_BENCH_ACTOR", "")
    if not actor.strip():
        raise ValueError("NATIVE_OWNED_BENCH_ACTOR_REQUIRED")
    # A raw-document hash cannot attest to normalized observations, CVSS,
    # enrichment, claims or the actual selected asset/component inventory.
    # Keep live native evaluation unavailable without opening a database until
    # an effective-data/asset-parity admission check has been implemented.
    adapter = AegisAIAdapter(gateway=gateway, unavailable_reason="NATIVE_EFFECTIVE_DATA_PARITY_NOT_IMPLEMENTED")
    adapter.configuration = {"native_request_map_sha256": sha256(path),
                             "native_admission_status": "NOT_IMPLEMENTED"}
    adapter.run_id = run_id
    return adapter
