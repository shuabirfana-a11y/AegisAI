"""Human PoC labels stay distinct; failed outputs retain their denominator."""
import pytest

from evaluation.bench.quality import score_variant
from evaluation.bench.schema import Annotation, Prediction, Question


SOURCES = {"s": {"document": {"record": {"fact": "official fact"}}}}
REF = {"source_id": "s", "locator": "/record/fact", "excerpt": '"official fact"'}


def score(answers, label="NO_EVIDENCE"):
    questions, annotations, predictions = [], [], []
    for index, answer in enumerate(answers):
        identifier = f"synthetic-{index}"
        questions.append(Question(id=identifier, category="poc_patch",
            question="Synthetic metric contract, not benchmark data",
            input_context={}, source_ids=["s"], origin="REAL_SOURCE"))
        annotations.append(Annotation(id=identifier, expected_answer={"poc_status": label},
            evidence_refs=[REF], confidence="HIGH", review_status="APPROVED",
            annotator_type="HUMAN", reviewer_type="HUMAN", annotator="Fixture annotator",
            reviewer="Fixture reviewer", annotation_note="Synthetic regression only",
            should_abstain=False, origin="HUMAN_GOLD"))
        predictions.append(Prediction(question_id=identifier, baseline="test",
            status="FAILED" if answer is None else "SUCCEEDED", answer=answer or {},
            error_code="TIMEOUT" if answer is None else None, abstained=False))
    return score_variant(questions, annotations, predictions, [], SOURCES)


def test_no_evidence_gold_does_not_credit_missing_or_failed_outputs():
    result = score([{}, None])
    assert result["scored_count"] == 2
    assert result["accuracy"] == 0
    assert result["poc_classification"]["sample_count"] == 2
    assert result["poc_classification"]["per_class"]["NO_EVIDENCE"]["recall"] == 0
    assert result["field_accuracy"]["poc_status"] == {"correct": 0, "n": 2, "accuracy": 0}
    assert result["execution"] == {"SUCCEEDED": 1, "FAILED": 1}
    assert result["evidence_coverage"] is None
    assert result["hallucination_rate"] is None


def test_no_evidence_is_literal_category_and_is_not_unknown():
    result = score([{"poc_status": "NO_EVIDENCE"}, {"poc_status": "UNKNOWN"}])
    assert result["accuracy"] == .5
    assert result["poc_classification"]["accuracy"] == .5
    assert result["invalid_label_count"] == 0
    matrix = result["poc_classification"]["confusion_matrix"]["NO_EVIDENCE"]
    assert matrix["NO_EVIDENCE"] == 1 and matrix["UNKNOWN"] == 1
    # NO_EVIDENCE has no automatic UNKNOWN/abstention interpretation.
    assert result["abstention"]["incorrect_abstention_count"] == 0


def test_unrecognized_gold_poc_category_still_rejected():
    with pytest.raises(ValueError, match="Unrecognized gold class label"):
        score([{"poc_status": "UNSUPPORTED"}], label="UNSUPPORTED")
