"""Frozen sources, RFC 6901 evidence locations and the existing human-gold gate."""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from evaluation.dataset import gold_exclusion_reason
from .schema import Annotation, Question


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pointer(document, locator):
    if locator == "":
        return document
    if not isinstance(locator, str) or not locator.startswith("/"):
        raise ValueError("Invalid JSON Pointer")
    current = document
    for raw in locator[1:].split("/"):
        if re.search(r"~(?![01])", raw):
            raise ValueError("Invalid JSON Pointer escape")
        key = raw.replace("~1", "/").replace("~0", "~")
        try:
            if isinstance(current, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", key):
                    raise ValueError("Invalid array index")
                current = current[int(key)]
            elif isinstance(current, dict):
                current = current[key]
            else:
                raise ValueError("JSON Pointer traverses a scalar")
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("JSON Pointer location does not exist") from exc
    return current


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def prediction_fingerprint(prediction):
    payload = prediction.model_dump(mode="json", exclude={"metadata", "latency_ms", "error", "error_code"})
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


def annotation_exclusion(question, annotation):
    if question.origin == "TEST_FIXTURE":
        return "Question is a TEST_FIXTURE"
    if annotation.origin != "HUMAN_GOLD":
        return "Source references and machine drafts are not HUMAN_GOLD"
    row = annotation.model_dump()
    row["expected"] = row.pop("expected_answer")
    # The legacy gate checks presence; load_benchmark separately resolves these
    # catalogue IDs to verified HTTPS source URLs, hashes and exact locations.
    row["supporting_evidence"] = [
        {"source_url": item.source_id, "locator": item.locator, "excerpt": item.excerpt}
        for item in annotation.evidence_refs
    ]
    reason = gold_exclusion_reason(row)
    if not reason and annotation.annotator.strip() == annotation.reviewer.strip():
        return "Independent human annotation and review required"
    return reason


def safe_path(base, name, root):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("File outside evaluation root")
    result = (base / name).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("File outside evaluation root")
    return result


def checked_file(base, name, digest, root):
    path = safe_path(base, name, root)
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Missing frozen file hash")
    if sha256(path) != digest:
        raise ValueError("Frozen file hash mismatch")
    return path


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
            if line.strip()]


def validate_evidence(reference, sources):
    source = sources.get(reference.source_id)
    if source is None:
        raise ValueError("Unknown evidence source")
    actual = pointer(source["document"], reference.locator)
    if reference.excerpt != canonical(actual):
        raise ValueError("Evidence excerpt does not match frozen source location")


def load_benchmark(manifest_path):
    path = Path(manifest_path).resolve()
    # Standard layout evaluation/datasets/<version>/manifest.json. Restrict both
    # annotations and sources to this evaluation tree, including resolved links.
    root = path.parents[2]
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    qp = checked_file(path.parent, manifest["questions_file"],
                      manifest["questions_sha256"], root)
    ap = checked_file(path.parent, manifest["annotations_file"],
                      manifest["annotations_sha256"], root)
    questions = [Question.model_validate(row) for row in read_jsonl(qp)]
    annotations = [Annotation.model_validate(row) for row in read_jsonl(ap)]
    ids = [q.id for q in questions]
    if len(set(ids)) != len(ids) or len(ids) != manifest["sample_count"]:
        raise ValueError("Duplicate question IDs or sample count mismatch")
    aids = [a.id for a in annotations]
    if len(aids) != len(set(aids)) or any(aid not in ids for aid in aids):
        raise ValueError("Duplicate or unknown annotation IDs")
    sources = {}
    for row in manifest["sources"]:
        if row["id"] in sources:
            raise ValueError("Duplicate source IDs")
        url = urlsplit(row["url"])
        if url.scheme != "https" or not url.netloc or url.username or url.password or url.query or url.fragment:
            raise ValueError("Sources require credential-free HTTPS provenance")
        retrieved = datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00"))
        if retrieved.tzinfo is None:
            raise ValueError("Source retrieval time requires timezone")
        sp = checked_file(path.parent, row["file"], row["sha256"], root)
        sources[row["id"]] = {**row, "document": json.loads(sp.read_text(encoding="utf-8-sig"))}
    by_id = {q.id: q for q in questions}
    for question in questions:
        if any(s not in sources for s in question.source_ids):
            raise ValueError("Question references unknown source")
    eligible, excluded = [], []
    for annotation in annotations:
        for ref in annotation.evidence_refs:
            if ref.source_id not in by_id[annotation.id].source_ids:
                raise ValueError("Annotation source is unrelated to its question")
            validate_evidence(ref, sources)
        reason = annotation_exclusion(by_id[annotation.id], annotation)
        if reason:
            excluded.append({"id": annotation.id, "reason": reason})
        else:
            eligible.append(annotation)
    return {"manifest": manifest, "questions": questions, "annotations": annotations,
            "eligible_gold": eligible, "excluded_gold": excluded, "sources": sources}
