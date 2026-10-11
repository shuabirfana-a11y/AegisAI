"""Questions and gold are stored separately; only audited humans can approve gold."""
import hashlib
import json
from pathlib import Path

ACCEPTED_REVIEW_STATUSES = {"APPROVED", "REVIEWED"}


def gold_exclusion_reason(row):
    if row.get("origin") == "TEST_FIXTURE":
        return "TEST_FIXTURE is excluded from formal benchmark metrics"
    if row.get("review_status") not in ACCEPTED_REVIEW_STATUSES:
        return "Human review pending or unaccepted review status"
    if row.get("annotator_type") != "HUMAN" or row.get("reviewer_type") != "HUMAN":
        return "Agent/LLM/machine annotations are drafts, not human gold"
    if not all(isinstance(row.get(key), str) and row[key].strip() for key in ("annotator", "reviewer", "annotation_note")):
        return "Named human annotator/reviewer and annotation note required"
    if not isinstance(row.get("expected"), dict) or not row["expected"]:
        return "Expected result is missing"
    evidence = row.get("supporting_evidence")
    if not isinstance(evidence, list) or not evidence:
        return "Supporting evidence missing"
    for item in evidence:
        if not isinstance(item, dict) or not item.get("source_url") or not item.get("locator") or not item.get("excerpt"):
            return "Every supporting source requires URL, locator, and reviewed excerpt"
    return None


def assistant_payload(question, *, request_key):
    payload = {"question": question["question"], "mode": question.get("mode", "auto"),
               "request_key": request_key, "realtime": False}
    for key in ("target", "asset_id"):
        if question.get(key):
            payload[key] = question[key]
    return payload


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def load_dataset(manifest_path):
    path = Path(manifest_path).resolve()
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    questions_path = path.parent / manifest["questions_file"]
    gold_path = path.parent / manifest["ground_truth_file"]
    question_bytes = questions_path.read_bytes()
    if manifest.get("questions_sha256") and hashlib.sha256(question_bytes).hexdigest() != manifest["questions_sha256"]:
        raise ValueError("Frozen question dataset hash mismatch; create a new revision")
    questions, gold = _read_jsonl(questions_path), _read_jsonl(gold_path)
    ids = [q["case_id"] for q in questions]
    if len(ids) != len(set(ids)) or manifest["sample_count"] != len(ids):
        raise ValueError("Duplicate question IDs or sample count mismatch")
    if any("expected" in q or "ground_truth" in q or q["group"] not in manifest["groups"] for q in questions):
        raise ValueError("Question/gold separation or group contract violated")
    gold_ids = [g["case_id"] for g in gold]
    if len(gold_ids) != len(set(gold_ids)) or any(identifier not in ids for identifier in gold_ids):
        raise ValueError("Gold IDs must uniquely reference dataset cases")
    eligible, excluded = [], []
    by_id = {q["case_id"]: q for q in questions}
    for row in gold:
        reason = gold_exclusion_reason(row)
        if by_id[row["case_id"]].get("origin") == "TEST_FIXTURE":
            reason = "Question is a TEST_FIXTURE"
        if reason:
            excluded.append({"case_id": row["case_id"], "reason": reason})
        else:
            eligible.append(row)
    return {"manifest": manifest, "questions": questions, "gold": gold, "eligible_gold": eligible, "excluded_gold": excluded}
