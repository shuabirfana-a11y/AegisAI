"""Synthetic contracts test the evaluator; they are never benchmark gold."""
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evaluation.bench.schema import Question, Annotation
from evaluation.bench.data import load_benchmark, annotation_exclusion, pointer


def question(**updates):
    return {"id": "q1", "category": "facts", "question": "Describe the advisory",
            "input_context": {"target": "CVE-2099-0001"},
            "origin": "TEST_FIXTURE", "source_ids": ["s1"], **updates}


def annotation(**updates):
    return {"id": "q1", "expected_answer": {"cve": "CVE-2099-0001"},
            "evidence_refs": [{"source_id": "s1", "locator": "/record/cve_id",
                               "excerpt": '"CVE-2099-0001"'}],
            "confidence": "HIGH", "review_status": "PENDING",
            "annotator_type": "MACHINE", "reviewer_type": "MACHINE",
            "annotator": "", "reviewer": "", "annotation_note": "Synthetic test only",
            "should_abstain": False, "origin": "TEST_FIXTURE", **updates}


def bundle(tmp_path):
    root = tmp_path / "evaluation"
    dataset = root / "datasets" / "pilot"
    dataset.mkdir(parents=True)
    payload = {"record": {"cve_id": "CVE-2099-0001"}}
    (dataset / "source.json").write_text(json.dumps(payload), encoding="utf-8")
    for name, value in [("questions.jsonl", question()), ("annotations.jsonl", annotation())]:
        (dataset / name).write_text(json.dumps(value) + "\n", encoding="utf-8")
    files = {n: hashlib.sha256((dataset / n).read_bytes()).hexdigest()
             for n in ["source.json", "questions.jsonl", "annotations.jsonl"]}
    manifest = {"dataset_version": "TEST_FIXTURE", "sample_count": 1,
                "questions_file": "questions.jsonl", "annotations_file": "annotations.jsonl",
                "questions_sha256": files["questions.jsonl"],
                "annotations_sha256": files["annotations.jsonl"],
                "sources": [{"id": "s1", "file": "source.json", "sha256": files["source.json"],
                             "url": "https://api.github.com/advisories/GHSA-test",
                             "retrieved_at": "2026-10-11T00:00:00Z"}],
                "split": "PILOT_NOT_INDEPENDENT_HOLDOUT"}
    path = dataset / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_question_rejects_gold_leak_even_nested():
    with pytest.raises(ValidationError):
        Question.model_validate(question(input_context={"nested": {"expected_answer": {"x": 1}}}))
    with pytest.raises(ValidationError):
        Question.model_validate({**question(), "expected_answer": {"x": 1}})


def test_machine_annotations_and_fixture_questions_never_become_gold():
    q = Question.model_validate(question(origin="REAL_SOURCE"))
    a = Annotation.model_validate(annotation(origin="SOURCE_REFERENCE", review_status="APPROVED"))
    assert annotation_exclusion(q, a) is not None
    human = Annotation.model_validate(annotation(origin="HUMAN_GOLD", review_status="APPROVED",
                annotator_type="HUMAN", reviewer_type="HUMAN", annotator="Alice", reviewer="Bob"))
    assert annotation_exclusion(Question.model_validate(question()), human) is not None
    assert annotation_exclusion(q, human) is None


def test_pointer_unescapes_keys_and_rejects_unknown_locations():
    assert pointer({"a/b": {"~": [42]}}, "/a~1b/~0/0") == 42
    with pytest.raises(ValueError):
        pointer({"record": {}}, "/record/missing")


def test_bundle_loads_and_source_integrity_is_enforced(tmp_path):
    path = bundle(tmp_path)
    data = load_benchmark(path)
    assert len(data["questions"]) == 1 and data["eligible_gold"] == []
    (path.parent / "source.json").write_text('{"record":{}}', encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        load_benchmark(path)


def test_snapshot_escape_is_rejected_before_reading(tmp_path):
    path = bundle(tmp_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["sources"][0]["file"] = "../../../outside.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="outside"):
        load_benchmark(path)


def test_duplicate_question_ids_are_rejected(tmp_path):
    path = bundle(tmp_path)
    qpath = path.parent / "questions.jsonl"
    qpath.write_text(qpath.read_text(encoding="utf-8") * 2, encoding="utf-8")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["sample_count"] = 2
    manifest["questions_sha256"] = hashlib.sha256(qpath.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        load_benchmark(path)
