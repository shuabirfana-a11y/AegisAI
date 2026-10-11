"""Optional setup for the real Python Orchestrator, guarded from production data."""
import json
import os
from pathlib import Path

from .adapters import AegisAIAdapter, RagOnlyAdapter, backend_imports, corpus_fingerprint
from .data import canonical
from .sources import project_advisory


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
    from sqlalchemy import create_engine, select, func
    from sqlalchemy.engine import make_url
    from app.db.models import RawDocument
    from app.orchestration.service import InvestigationOrchestrator
    from .schema import reject_labels
    url = make_url(os.environ.get("AEGIS_BENCH_DATABASE_URL", ""))
    if (url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", "::1"}
            or url.database not in {"aegis_bench_test", "aegis_phase5_test"}):
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
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        # Only read existing source data. This factory never migrates, resets,
        # seeds or edits intelligence records. Exact corpus prevents comparing a
        # five-document RAG with an undeclared larger application database.
        with engine.connect() as db:
            if db.scalar(select(func.count()).select_from(RawDocument)) != len(data["sources"]):
                raise ValueError("NATIVE_CORPUS_NOT_IDENTICAL")
            for sid, source in data["sources"].items():
                rows = db.execute(select(RawDocument.parsed_payload, RawDocument.source_url,
                                          RawDocument.content_hash, RawDocument.raw_payload)
                                  .where(RawDocument.external_id == sid)).all()
                if len(rows) != 1 or rows[0].source_url != source["url"]:
                    raise ValueError("NATIVE_CORPUS_NOT_IDENTICAL")
                import hashlib
                if hashlib.sha256(rows[0].raw_payload).hexdigest() != rows[0].content_hash:
                    raise ValueError("NATIVE_SOURCE_HASH_INVALID")
                if json.loads(rows[0].raw_payload) != rows[0].parsed_payload:
                    raise ValueError("NATIVE_SOURCE_PARSED_PAYLOAD_MISMATCH")
                projected = project_advisory(rows[0].parsed_payload, source["retrieved_at"])
                if canonical(projected["record"]) != canonical(source["document"]["record"]):
                    raise ValueError("NATIVE_CORPUS_NOT_IDENTICAL")
        adapter = AegisAIAdapter(InvestigationOrchestrator(engine, gateway), gateway, actor, mapping,
                                corpus_fingerprint(data["sources"]))
        adapter.run_id = run_id
        adapter.engine = engine
        return adapter
    except Exception:
        engine.dispose()
        raise
