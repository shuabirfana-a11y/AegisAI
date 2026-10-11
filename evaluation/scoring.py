"""Formal scores require human-reviewed gold; runtime completion is not accuracy."""
from evaluation.dataset import gold_exclusion_reason
from evaluation.metrics import abstention_metrics, classification_metrics, latency_metrics, retrieval_metrics, unsupported_claim_metrics

LABELS = {"A": ["relevant", "irrelevant", "uncertain"],
          "B": ["affected", "not_affected", "unknown"],
          "C": ["real_poc", "scanner", "reference_repository", "exploit_collection", "unrelated", "insufficient_evidence"],
          "D": ["correct_patch", "incorrect_patch", "unknown"],
          "E": ["affected", "not_affected", "uncertain"]}


def _get(value, path):
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def summarize(questions, gold, results, *, variant="full_agent", k=5):
    by_id = {q["case_id"]: q for q in questions}
    eligible = {g["case_id"]: g for g in gold if g["case_id"] in by_id and by_id[g["case_id"]].get("origin") != "TEST_FIXTURE" and gold_exclusion_reason(g) is None}
    outcomes = {r["case_id"]: r for r in results if r.get("variant") == variant}
    grouped = {group: [] for group in LABELS}
    errors, abstentions, retrieval, qa_rows = [], [], [], []
    for identifier, annotation in eligible.items():
        question = by_id[identifier]
        outcome = outcomes.get(identifier, {"status": "BLOCKED", "actual": {}, "error": "No runtime result", "error_type": "INTEGRATION_ERROR"})
        expected, actual = annotation["expected"], outcome.get("actual", {})
        failed = outcome.get("status") in {"FAILED", "BLOCKED"}
        mismatch = failed
        if "label" in expected and question["group"] in LABELS:
            predicted = None if failed else _get(actual, question.get("prediction_path", "label"))
            if predicted not in LABELS[question["group"]]:
                predicted = None
            grouped[question["group"]].append({"expected": expected["label"], "predicted": predicted})
            mismatch = mismatch or predicted != expected["label"]
        if "should_abstain" in expected:
            prediction = None if failed else _get(actual, question.get("abstention_path", "abstained"))
            if type(prediction) is not bool:
                prediction = None
            abstentions.append({"should_abstain": expected["should_abstain"], "abstained": prediction})
            mismatch = mismatch or prediction != expected["should_abstain"]
        if "relevant_ids" in expected:
            retrieved_ids = [] if failed else _get(actual, question.get("retrieval_ids_path", "retrieved_ids")) or []
            retrieval.append({"relevant_ids": expected["relevant_ids"], "retrieved_ids": retrieved_ids})
        if "fields" in expected:
            matches = [not failed and _get(actual, path) == wanted for path, wanted in expected["fields"].items()]
            complete = bool(matches) and all(matches)
            qa_rows.append({"case_id": identifier, "score": 2 if complete else 1 if any(matches) else 0})
            mismatch = mismatch or not complete
        if mismatch:
            errors.append({"case_id": identifier, "group": question["group"], "variant": variant,
                           "expected": expected, "actual": actual, "evidence": annotation["supporting_evidence"],
                           "error_type": outcome.get("error_type", "GENERATION_ERROR"),
                           "possible_cause": outcome.get("error", "Prediction differs from reviewed expected result; inspect runtime trace")})
    observed = [r["latency_ms"] for r in outcomes.values() if isinstance(r.get("latency_ms"), (int, float))]
    return {"status": "PARTIAL", "variant": variant, "candidate_cases": len(questions), "formal_scored_cases": len(eligible),
            "ground_truth_pending": len(questions) - len(eligible), "classification": {g: classification_metrics(rows, labels=LABELS[g]) for g, rows in grouped.items()},
            "qa": {"n": len(qa_rows), "accuracy": sum(r["score"] == 2 for r in qa_rows) / len(qa_rows) if qa_rows else None, "rows": qa_rows},
            "abstention": abstention_metrics(abstentions), "retrieval": retrieval_metrics(retrieval, k=k),
            "unsupported_claims": unsupported_claim_metrics([]), "latency": latency_metrics(observed), "errors": errors,
            "limitation": "Scores are unavailable without human gold; semantic QA and citation/claim audits additionally require outcome-specific human judgments"}
