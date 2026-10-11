"""Only call metadata is persisted; prompts, outputs and credentials are omitted."""
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Protocol
from app.llm.schemas import CallRecord

logger = logging.getLogger('aegis.model_gateway')


class RecordSink(Protocol):
    def write(self, record: CallRecord) -> None: ...


class JsonlRecordSink:
    _locks: dict[str, Lock] = {}
    _registry_lock = Lock()

    def __init__(self, path):
        self.path = Path(path).resolve()
        with self._registry_lock:
            self.lock = self._locks.setdefault(str(self.path), Lock())

    def write(self, record):
        line = json.dumps(record.model_dump(mode='json'), ensure_ascii=True, allow_nan=False)
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a', encoding='utf-8') as stream:
                stream.write(line + '\n')
                stream.flush()


class DefaultRecordSink(JsonlRecordSink):
    def __init__(self):
        super().__init__(Path(__file__).resolve().parents[3] / 'work' / 'model_gateway' / 'calls.jsonl')

    def write(self, record):
        super().write(record)
        logger.info(json.dumps(record.model_dump(mode='json'), ensure_ascii=True, allow_nan=False))
