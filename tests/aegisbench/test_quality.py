"""Known numerical outcomes validate metrics, not application benchmark quality."""
import pytest
import hashlib
import json

from evaluation.bench.quality import score_variant
from evaluation.bench.schema import Annotation, OutcomeAudit, Prediction, Question


SOURCES = {"s": {"document": {"record": {"fact": "official fact"}}}}
REF = {"source_id": "s", "locator": "/record/fact", "excerpt": '"official fact"'}


def digest(prediction):
    payload = prediction.model_dump(mode="json", exclude={"metadata", "latency_ms", "error", "error_code"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def q(identifier, category="version"):
    return Question(id=identifier, category=category, question="Synthetic metric contract",
                    input_context={}, source_ids=["s"], origin="REAL_SOURCE")


def gold(identifier, expected, abstain=False, hops=None):
    return Annotation(id=identifier, expected_answer=expected, evidence_refs=[REF], confidence="HIGH",
                      review_status="APPROVED", annotator_type="HUMAN", reviewer_type="HUMAN",
                      annotator="Fixture annotator", reviewer="Fixture reviewer",
                      annotation_note="Synthetic metric test only; not a dataset record",
                      should_abstain=abstain, origin="HUMAN_GOLD", required_hops=hops or [])


def p(identifier, answer, **extra):
    return Prediction(question_id=identifier, baseline="test", status="SUCCEEDED", answer=answer,
                      abstained=False, **extra)


def test_missing_and_failed_predictions_remain_in_accuracy_denominator():
    qs = [q(x) for x in "abc"]
    gs = [gold(x, {"affected": "AFFECTED"}) for x in "abc"]
    preds = [p("a", {"affected": "AFFECTED"}),
             Prediction(question_id="b", baseline="test", status="FAILED", error_code="TIMEOUT")]
    result = score_variant(qs, gs, preds, [], SOURCES)
    assert result["accuracy"] == pytest.approx(1 / 3)
    assert result["version"]["sample_count"] == 3
    assert result["version"]["per_class"]["AFFECTED"]["recall"] == pytest.approx(1 / 3)
    assert result["missing_predictions"] == 1


def test_zero_gold_and_unavailable_variants_have_no_quality_percentage():
    question = q("a")
    candidate = gold("a", {"affected": "AFFECTED"}).model_copy(update={"reviewer_type": "MACHINE"})
    result = score_variant([question], [candidate], [p("a", {"affected": "AFFECTED"})], [], SOURCES)
    assert result["accuracy"] is None and result["status"] == "NOT_EVALUATED"
    unavailable = Prediction(question_id="a", baseline="test", status="NOT_EVALUATED", error_code="NO_MODEL")
    result = score_variant([question], [gold("a", {"affected": "AFFECTED"})], [unavailable], [], SOURCES)
    assert result["accuracy"] is None and result["status"] == "NOT_EVALUATED"


def test_abstention_precision_and_recall_include_failures():
    qs = [q(x) for x in "abc"]
    gs = [gold("a", {"affected": "UNKNOWN"}, True), gold("b", {"affected": "UNKNOWN"}, True),
          gold("c", {"affected": "NOT_AFFECTED"})]
    preds = [p("a", {"affected": "UNKNOWN"}).model_copy(update={"abstained": True}),
             Prediction(question_id="b", baseline="test", status="FAILED"),
             p("c", {"affected": "UNKNOWN"}).model_copy(update={"abstained": True})]
    result = score_variant(qs, gs, preds, [], SOURCES)
    assert result["abstention"]["precision"] == .5
    assert result["abstention"]["recall"] == .5
    assert result["abstention"]["missing_prediction_count"] == 1


def test_citation_presence_is_not_evidence_coverage_or_hallucination_audit():
    pred = p("a", {"cve": "CVE-2099-0001"}, claims=[{
        "claim_id": "claim1", "statement": "A claim", "evidence_refs": [REF]}])
    result = score_variant([q("a", "facts")], [gold("a", {"cve": "CVE-2099-0001"})], [pred], [], SOURCES)
    assert result["evidence_coverage"] is None and result["hallucination_rate"] is None
    audit = OutcomeAudit(question_id="a", baseline="test", reviewer="Human test reviewer",
                         reviewer_type="HUMAN", review_status="APPROVED", prediction_sha256=digest(pred), claim_inventory_complete=True, claims=[{
        "claim_id": "claim1", "verdict": "HALLUCINATED", "review_note": "Explicit contradiction", "evidence_refs": [REF]}])
    result = score_variant([q("a", "facts")], [gold("a", {"cve": "CVE-2099-0001"})], [pred], [audit], SOURCES)
    assert result["evidence_coverage"] == 0 and result["hallucination_rate"] == 1


def test_invalid_support_or_duplicate_audit_cannot_improve_scores():
    pred = p("a", {}, claims=[{"claim_id": "c", "statement": "Claim"}])
    audit = OutcomeAudit(question_id="a", baseline="test", reviewer="Reviewer", reviewer_type="HUMAN",
                         review_status="APPROVED", prediction_sha256=digest(pred), claims=[{
        "claim_id": "c", "verdict": "SUPPORTED", "review_note": "Checked", "evidence_refs": []}])
    with pytest.raises(ValueError, match="evidence"):
        score_variant([q("a")], [gold("a", {"affected": "UNKNOWN"}, True)], [pred], [audit], SOURCES)
    with pytest.raises(ValueError, match="Duplicate"):
        score_variant([q("a")], [], [pred], [audit, audit], SOURCES)


def test_reasoning_completeness_uses_required_steps_and_failed_task_is_zero():
    qs = [q("a", "multihop"), q("b", "multihop")]
    gs = [gold(x, {"risk_level": "HIGH"}, hops=["vulnerability", "version", "asset", "risk"]) for x in "ab"]
    preds = [p("a", {"risk_level": "HIGH"}, completed_hops=["vulnerability", "version"]),
             Prediction(question_id="b", baseline="test", status="FAILED")]
    result = score_variant(qs, gs, preds, [], SOURCES)
    assert result["reasoning_completeness"] == .25
    assert result["risk_accuracy"] == .5


def test_duplicate_prediction_and_unknown_class_label_are_rejected():
    pred = p("a", {"affected": "anything"})
    with pytest.raises(ValueError, match="Duplicate"):
        score_variant([q("a")], [], [pred, pred], [], SOURCES)
    result = score_variant([q("a")], [gold("a", {"affected": "AFFECTED"})], [pred], [], SOURCES)
    assert result["version"]["accuracy"] == 0
    assert result["invalid_label_count"] == 1


def test_old_human_audit_cannot_approve_changed_output_with_same_claim_id():
    original = p("a", {"affected": "UNKNOWN"}, claims=[{"claim_id": "c", "statement": "Old output"}])
    changed = p("a", {"affected": "NOT_AFFECTED"}, claims=[{"claim_id": "c", "statement": "Changed output"}])
    audit = OutcomeAudit(question_id="a", baseline="test", reviewer="Reviewer", reviewer_type="HUMAN",
                         review_status="APPROVED", prediction_sha256=digest(original), claims=[{
        "claim_id": "c", "verdict": "SUPPORTED", "review_note": "Reviewed old output", "evidence_refs": [REF]}])
    with pytest.raises(ValueError, match="hash"):
        score_variant([q("a")], [], [changed], [audit], SOURCES)


def test_global_evidence_metrics_require_every_substantive_answer_to_be_audited():
    pred = p("a", {"affected": "AFFECTED"}, claims=[{"claim_id": "c", "statement": "A fact"}])
    unaccounted = p("b", {"affected": "NOT_AFFECTED"}, claims=[])
    audit = OutcomeAudit(question_id="a", baseline="test", reviewer="Reviewer", reviewer_type="HUMAN",
                         review_status="APPROVED", prediction_sha256=digest(pred), claims=[{
        "claim_id": "c", "verdict": "SUPPORTED", "review_note": "Checked fact", "evidence_refs": [REF]}])
    result = score_variant([q("a"), q("b")], [], [pred, unaccounted], [audit], SOURCES)
    assert result["evidence_coverage"] is None and result["hallucination_rate"] is None
    assert result["audit"]["complete"] is False


def test_claim_list_review_without_inventory_confirmation_is_not_global_completeness():
    pred = p("a", {"affected": "AFFECTED"}, claims=[{"claim_id": "c", "statement": "A fact"}])
    audit = OutcomeAudit(question_id="a", baseline="test", reviewer="Reviewer", reviewer_type="HUMAN",
                         review_status="APPROVED", prediction_sha256=digest(pred), claims=[{
        "claim_id": "c", "verdict": "SUPPORTED", "review_note": "Only listed claim checked", "evidence_refs": [REF]}])
    result = score_variant([q("a")], [], [pred], [audit], SOURCES)
    assert result["evidence_coverage"] is None
    assert result["audit"]["complete"] is False


def test_contradictory_abstention_flag_cannot_earn_correct_abstention_credit():
    pred = p("a", {"affected": "NOT_AFFECTED"}).model_copy(update={"abstained": True})
    result = score_variant([q("a")], [gold("a", {"affected": "UNKNOWN"}, True)], [pred], [], SOURCES)
    assert result["accuracy"] == 0
    assert result["abstention"]["correct_abstention_count"] == 0
    assert result["abstention"]["false_confident_answer_count"] == 1
    assert result["abstention"]["inconsistent_flag_count"] == 1


def test_partial_poc_abstention_preserves_confirmed_release_information():
    pred = p("a", {"poc_status": "UNKNOWN", "patch_status": "CONFIRMED_FIX"}).model_copy(update={"abstained": True})
    result = score_variant([q("a", "poc_patch")], [gold("a", {"poc_status": "UNKNOWN", "patch_status": "CONFIRMED_FIX"}, True)],
                           [pred], [], SOURCES)
    assert result["accuracy"] == 1 and result["abstention"]["correct_abstention_count"] == 1


def test_confirmed_inventory_is_required_for_audited_empty_claim_answer():
    pred = p("a", {"affected": "UNKNOWN"}, claims=[]).model_copy(update={"abstained": True})
    audit = OutcomeAudit(question_id="a", baseline="test", reviewer="Reviewer", reviewer_type="HUMAN",
                         review_status="APPROVED", prediction_sha256=digest(pred), claims=[])
    result = score_variant([q("a")], [], [pred], [audit], SOURCES)
    assert result["audit"]["answers_requiring_audit"] == 1
    assert result["audit"]["human_audited_answers"] == 0


def test_complete_inventory_reviews_all_answers_including_explicit_unknown_without_claims():
    first = p("a", {"affected": "AFFECTED"}, claims=[{"claim_id": "c", "statement": "A fact"}])
    second = p("b", {"affected": "UNKNOWN"}, claims=[]).model_copy(update={"abstained": True})
    audits = [OutcomeAudit(question_id=pred.question_id, baseline="test", reviewer="Reviewer", reviewer_type="HUMAN",
        review_status="APPROVED", prediction_sha256=digest(pred), claim_inventory_complete=True, claims=claims)
        for pred, claims in [(first, [{"claim_id": "c", "verdict": "SUPPORTED", "review_note": "Checked complete inventory",
                                     "evidence_refs": [REF]}]), (second, [])]]
    result = score_variant([q("a"), q("b")], [], [first, second], audits, SOURCES)
    assert result["audit"]["human_audited_answers"] == 2 and result["audit"]["complete"] is True
    assert result["evidence_coverage"] == 1 and result["hallucination_rate"] == 0


def test_invalid_risk_shape_does_not_crash_abstention_scoring():
    pred = p("a", {"risk_level": {"invalid": "HIGH"}})
    result = score_variant([q("a", "risk")], [gold("a", {"risk_level": "UNKNOWN"}, True)], [pred], [], SOURCES)
    assert result["accuracy"] == 0 and result["abstention"]["correct_abstention_count"] == 0
