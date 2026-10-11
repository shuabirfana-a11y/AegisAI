"""Human-gated quality metrics; observed execution is a separate measurement."""
from collections import Counter

from evaluation.metrics import abstention_metrics, classification_metrics, latency_metrics, ratio
from .data import annotation_exclusion, canonical, validate_evidence


VERSION_LABELS = ["AFFECTED", "NOT_AFFECTED", "UNKNOWN"]
POC_LABELS = ["POC_CANDIDATE", "VERIFIED_EXPLOIT", "UNKNOWN"]
PATCH_LABELS = ["PATCH_CANDIDATE", "CONFIRMED_FIX", "UNKNOWN"]


def unique(items, key, kind):
    values = [key(item) for item in items]
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {kind}")


def same(expected, actual):
    # JSON comparison retains boolean/numeric distinction; no fuzzy LLM judge.
    return canonical(expected) == canonical(actual)


def classified(rows, labels):
    result = classification_metrics([
        {"expected": r["expected"].lower(),
         "predicted": r["predicted"].lower() if r["predicted"] else None}
        for r in rows], labels=[s.lower() for s in labels])
    result["per_class"] = {key.upper(): value for key, value in result["per_class"].items()}
    result["confusion_matrix"] = {key.upper(): {k.upper(): v for k, v in values.items()}
                                  for key, values in result["confusion_matrix"].items()}
    result["sample_count"] = result["n"]
    return result


def score_variant(questions, annotations, predictions, audits, sources):
    unique(questions, lambda q: q.id, "question")
    unique(annotations, lambda a: a.id, "annotation")
    unique(predictions, lambda p: p.question_id, "prediction")
    unique(audits, lambda a: a.question_id, "audit")
    variants = {p.baseline for p in predictions} | {a.baseline for a in audits}
    if len(variants) > 1:
        raise ValueError("Score one baseline at a time")
    qmap = {q.id: q for q in questions}
    pmap = {p.question_id: p for p in predictions}
    if any(identifier not in qmap for identifier in pmap):
        raise ValueError("Prediction references unknown question")
    gold, exclusions = [], []
    for annotation in annotations:
        if annotation.id not in qmap:
            raise ValueError("Annotation references unknown question")
        for ref in annotation.evidence_refs:
            validate_evidence(ref, sources)
        reason = annotation_exclusion(qmap[annotation.id], annotation)
        if reason:
            exclusions.append({"id": annotation.id, "reason": reason})
        else:
            gold.append(annotation)
    unavailable = bool(questions) and len(predictions) == len(questions) and all(
        p.status == "NOT_EVALUATED" for p in predictions)
    scored = [] if unavailable else gold
    field_correct = Counter()
    field_total = Counter()
    correct = 0
    version, poc, patch, abstentions, hops = [], [], [], [], []
    invalid_labels = 0
    for annotation in scored:
        prediction = pmap.get(annotation.id)
        succeeded = prediction is not None and prediction.status == "SUCCEEDED"
        answer = prediction.answer if succeeded else {}
        matched = []
        for field, expected in annotation.expected_answer.items():
            good = field in answer and same(expected, answer[field])
            field_total[field] += 1
            field_correct[field] += good
            matched.append(good)
        correct += bool(matched) and all(matched)
        category = qmap[annotation.id].category
        for field, labels, rows in (("affected", VERSION_LABELS, version),
                                    ("poc_status", POC_LABELS, poc),
                                    ("patch_status", PATCH_LABELS, patch)):
            if field not in annotation.expected_answer:
                continue
            expected = annotation.expected_answer[field]
            if expected not in labels:
                raise ValueError("Unrecognized gold class label")
            predicted = answer.get(field)
            if predicted is not None and predicted not in labels:
                predicted = None
                invalid_labels += 1
            rows.append({"expected": expected, "predicted": predicted})
        abstentions.append({"should_abstain": annotation.should_abstain,
                            "abstained": prediction.abstained if succeeded else None})
        if category == "multihop" and annotation.required_hops:
            observed = set(prediction.completed_hops) if succeeded else set()
            hops.append(len(set(annotation.required_hops) & observed) / len(set(annotation.required_hops)))
    abstention = abstention_metrics(abstentions)
    abstention["precision"] = ratio(abstention["correct_abstention_count"],
                                     abstention["correct_abstention_count"] + abstention["incorrect_abstention_count"])
    abstention["recall"] = abstention["correct_abstention_rate"]
    abstention["missing_prediction_count"] = abstention["no_prediction_count"]
    abstention["quality_accuracy"] = ratio(sum(
        r["abstained"] is r["should_abstain"] for r in abstentions), len(abstentions))

    # Require independently reviewed, complete claims for each audited answer.
    # A valid citation only proves provenance, never semantic support by itself.
    emitted_claims, reviewed_claims, supported, hallucinated, unresolved = 0, 0, 0, 0, 0
    for prediction in predictions:
        unique(prediction.claims, lambda c: c.claim_id, "claim")
        emitted_claims += len(prediction.claims)
    for audit in audits:
        prediction = pmap.get(audit.question_id)
        if prediction is None or prediction.status != "SUCCEEDED":
            raise ValueError("Audit requires a successful observed answer")
        unique(audit.claims, lambda c: c.claim_id, "reviewed claim")
        if audit.reviewer_type != "HUMAN" or audit.review_status not in {"APPROVED", "REVIEWED"}:
            continue
        if {c.claim_id for c in audit.claims} != {c.claim_id for c in prediction.claims}:
            raise ValueError("Human audit must cover all emitted claims in its answer")
        for claim in audit.claims:
            if claim.verdict in {"SUPPORTED", "HALLUCINATED", "CONTRADICTED"} and not claim.evidence_refs:
                raise ValueError("Reviewed verdict requires supporting or contradicting evidence")
            for ref in claim.evidence_refs:
                validate_evidence(ref, sources)
            reviewed_claims += 1
            supported += claim.verdict == "SUPPORTED"
            hallucinated += claim.verdict == "HALLUCINATED"
            unresolved += claim.verdict == "UNRESOLVED"
    complete_audit = emitted_claims > 0 and reviewed_claims == emitted_claims
    return {
        "status": "EVALUATED" if scored else "NOT_EVALUATED",
        "eligible_gold_count": len(gold), "scored_count": len(scored),
        "excluded_annotations": exclusions,
        "accuracy": ratio(correct, len(scored)),
        "field_accuracy": {key: {"correct": field_correct[key], "n": total,
                                 "accuracy": ratio(field_correct[key], total)} for key, total in field_total.items()},
        "version": classified(version, VERSION_LABELS),
        "poc_classification": classified(poc, POC_LABELS),
        "patch_classification": classified(patch, PATCH_LABELS),
        "risk_accuracy": ratio(field_correct["risk_level"], field_total["risk_level"]),
        "priority_accuracy": ratio(field_correct["priority"], field_total["priority"]),
        "abstention": abstention,
        "reasoning_completeness": ratio(sum(hops), len(hops)),
        "reasoning_completeness_basis": "RECORDED_WORKFLOW_STEPS_NOT_REASONING_CORRECTNESS",
        "evidence_coverage": ratio(supported, emitted_claims) if complete_audit else None,
        "hallucination_rate": ratio(hallucinated, emitted_claims) if complete_audit else None,
        "audit": {"emitted_claims": emitted_claims, "human_reviewed_claims": reviewed_claims,
                  "coverage": ratio(reviewed_claims, emitted_claims), "complete": complete_audit,
                  "unresolved_claims": unresolved,
                  "reviewed_subset_evidence_coverage": ratio(supported, reviewed_claims),
                  "reviewed_subset_hallucination_rate": ratio(hallucinated, reviewed_claims)},
        "invalid_label_count": invalid_labels,
        "execution": dict(Counter(p.status for p in predictions)),
        "missing_predictions": len(questions) - len(predictions),
        "latency": latency_metrics([p.latency_ms for p in predictions if p.status != "NOT_EVALUATED"]),
        "limitations": ["Human gold and outcome audit are distinct gates.",
                        "Absent class support has null recall; macro F1 lists defined classes.",
                        "Workflow step coverage does not establish reasoning correctness.",
                        "Pilot questions sharing advisories are correlated, not independent trials."],
    }
