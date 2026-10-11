from pathlib import Path

from evaluation.bench.data import load_benchmark


ROOT = Path(__file__).resolve().parents[2]


def test_real_pilot_has_all_five_categories_and_no_machine_gold():
    data = load_benchmark(ROOT / "evaluation/datasets/AegisBench-v0.2-pilot/manifest.json")
    assert {q.category for q in data["questions"]} == {"facts", "version", "poc_patch", "risk", "multihop"}
    assert len(data["sources"]) >= 4
    assert data["eligible_gold"] == []
    assert all(a.annotator_type == "MACHINE" and a.review_status == "PENDING" for a in data["annotations"])
    assert {a.expected_answer.get("affected") for a in data["annotations"] if a.id.endswith(("-affected", "-fixed", "-unknown"))} >= {
        "AFFECTED", "NOT_AFFECTED", "UNKNOWN"}
    multi = [q for q in data["questions"] if q.category == "multihop"]
    assert any(len(q.source_ids) > 1 for q in multi)


def test_corrected_pending_revision_preserves_original_questions_and_sources():
    original = load_benchmark(ROOT / "evaluation/datasets/AegisBench-v0.2-pilot/manifest.json")
    revised = load_benchmark(ROOT / "evaluation/datasets/AegisBench-v0.2.1-pilot/manifest.json")
    old = next(a for a in original["annotations"] if a.id == "cross-advisory-priorities")
    new = next(a for a in revised["annotations"] if a.id == old.id)
    assert old.should_abstain is False and new.should_abstain is True
    assert revised["manifest"]["questions_sha256"] == original["manifest"]["questions_sha256"]
    assert [s["sha256"] for s in revised["manifest"]["sources"]] == [s["sha256"] for s in original["manifest"]["sources"]]
    assert len(revised["questions"]) == 49 and revised["eligible_gold"] == []
