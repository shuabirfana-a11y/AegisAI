"""Metrics use observed rows; unavailable denominators are JSON null."""
import math
from statistics import mean


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def classification_metrics(rows, *, labels):
    labels = list(labels)
    if not labels or len(labels) != len(set(labels)):
        raise ValueError("Distinct nonempty labels required")
    rows = list(rows)
    matrix = {label: {prediction: 0 for prediction in [*labels, "NO_PREDICTION"]} for label in labels}
    for row in rows:
        expected, predicted = row["expected"], row.get("predicted")
        if expected not in labels or (predicted is not None and predicted not in labels):
            raise ValueError("Unrecognized classification label")
        matrix[expected][predicted if predicted is not None else "NO_PREDICTION"] += 1
    per_class = {}
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in labels if other != label)
        support = sum(matrix[label].values())
        fn = support - tp
        per_class[label] = {"tp": tp, "fp": fp, "fn": fn, "support": support,
                            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
                            "f1": ratio(2 * tp, 2 * tp + fp + fn)}
    f1_values = [v["f1"] for v in per_class.values() if v["f1"] is not None]
    false_safe = matrix.get("affected", {}).get("not_affected", 0)
    false_affected = matrix.get("not_affected", {}).get("affected", 0)
    affected_support = sum(matrix.get("affected", {}).values())
    safe_support = sum(matrix.get("not_affected", {}).values())
    unknown_predictions = sum(row.get("predicted") in {"unknown", "uncertain", "insufficient_evidence"} for row in rows)
    return {"n": len(rows), "accuracy": ratio(sum(v["tp"] for v in per_class.values()), len(rows)),
            "per_class": per_class, "confusion_matrix": matrix,
            "macro_f1": mean(f1_values) if f1_values else None,
            "macro_f1_defined_classes": len(f1_values),
            "unknown_rate": ratio(unknown_predictions, len(rows)),
            "no_prediction_count": sum(row.get("predicted") is None for row in rows),
            "false_safe_count": false_safe, "false_safe_rate": ratio(false_safe, affected_support),
            "false_affected_count": false_affected, "false_affected_rate": ratio(false_affected, safe_support)}


def retrieval_metrics(rows, *, k=5):
    if not isinstance(k, int) or k < 1:
        raise ValueError("Positive retrieval k required")
    recalls, reciprocal_ranks, unlabeled = [], [], 0
    for row in rows:
        relevant = set(row["relevant_ids"])
        if not relevant:
            unlabeled += 1
            continue
        retrieved = row.get("retrieved_ids", [])
        recalls.append(len(relevant.intersection(retrieved[:k])) / len(relevant))
        first = next((index for index, identifier in enumerate(retrieved, 1) if identifier in relevant), None)
        reciprocal_ranks.append(1 / first if first else 0.0)
    return {"k": k, "scored_queries": len(recalls), "unlabeled_queries": unlabeled,
            "recall_at_k": mean(recalls) if recalls else None,
            "mrr": mean(reciprocal_ranks) if reciprocal_ranks else None}


def abstention_metrics(rows):
    rows = list(rows)
    for row in rows:
        if type(row["should_abstain"]) is not bool or type(row.get("abstained")) not in (bool, type(None)):
            raise ValueError("Abstention requires explicit booleans or missing prediction")
    unknown = [r for r in rows if r["should_abstain"]]
    answerable = [r for r in rows if not r["should_abstain"]]
    correct = sum(r.get("abstained") is True for r in unknown)
    incorrect = sum(r.get("abstained") is True for r in answerable)
    false_confident = sum(r.get("abstained") is False for r in unknown)
    return {"n": len(rows), "should_abstain_n": len(unknown), "answerable_n": len(answerable),
            "correct_abstention_count": correct, "correct_abstention_rate": ratio(correct, len(unknown)),
            "incorrect_abstention_count": incorrect, "incorrect_abstention_rate": ratio(incorrect, len(answerable)),
            "false_confident_answer_count": false_confident, "false_confident_answer_rate": ratio(false_confident, len(unknown)),
            "no_prediction_count": sum(r.get("abstained") is None for r in rows)}


def unsupported_claim_metrics(rows):
    rows = list(rows)
    for row in rows:
        total, unsupported = row["claim_count"], row["unsupported_claim_count"]
        if type(total) is not int or type(unsupported) is not int or not 0 <= unsupported <= total:
            raise ValueError("Invalid reviewed claim counts")
    total = sum(row["claim_count"] for row in rows)
    unsupported = sum(row["unsupported_claim_count"] for row in rows)
    return {"reviewed_answers": len(rows), "reviewed_claims": total, "unsupported_claims": unsupported,
            "unsupported_claim_rate": ratio(unsupported, total)}


def latency_metrics(values):
    values = sorted(values)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Latency must be finite nonnegative milliseconds")
    def percentile(fraction):
        if not values:
            return None
        position = (len(values) - 1) * fraction
        low, high = math.floor(position), math.ceil(position)
        return values[low] + (values[high] - values[low]) * (position - low)
    return {"n": len(values), "p50_ms": percentile(0.5), "p95_ms": percentile(0.95),
            "mean_ms": mean(values) if values else None, "max_ms": max(values) if values else None,
            "percentile_method": "linear interpolation at (n-1)*p"}
