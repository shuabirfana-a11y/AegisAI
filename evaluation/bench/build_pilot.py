"""Build pending annotation packets from frozen real advisories, never human gold.

Version choices and reference triage labels below are transparent draft scenario
choices. The builder imports no runtime, agent, model or evaluator implementation.
"""
import json
from collections import Counter
from pathlib import Path

from .data import canonical, load_benchmark, sha256
from .schema import Annotation, Question


SCENARIOS = {
    "GHSA-53q9-r3pm-6pq6": ("2.5.1", "2.6.0", "CRITICAL", "P1"),
    "GHSA-47fc-vmwq-366v": ("1.13.0", "1.13.1", "CRITICAL", "P1"),
    "GHSA-c67j-w6g6-q2cm": ("1.2.0", "1.2.5", "CRITICAL", "P1"),
    "GHSA-9rwj-6rc7-p77c": ("3.0.0", "3.0.1", "HIGH", "P2"),
    "GHSA-935w-9g4m-p28p": ("0.29.0", "0.30.0", "LOW", "P3"),
}
POLICY = "benchmark-reference-triage-v1"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    folder = Path(__file__).resolve().parents[1] / "datasets/AegisBench-v0.2-pilot"
    if (folder / "manifest.json").exists():
        raise SystemExit("Frozen manifest exists; create a new dataset revision")
    sources, questions, annotations = [], [], []
    records = {}
    for identifier in SCENARIOS:
        path = folder / "sources" / f"{identifier}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        records[identifier] = doc["record"]
        sources.append({"id": identifier, "file": f"sources/{identifier}.json", "sha256": sha256(path),
                        "url": doc["source_url"], "retrieved_at": doc["retrieved_at"]})

    def refs(ids, fields):
        return [{"source_id": sid, "locator": f"/record/{field}",
                 "excerpt": canonical(records[sid][field])} for sid in ids for field in fields]

    def add(identifier, category, text, context, expected, source_ids, *, unknown=False,
            controlled=False, hops=None, fields=None):
        questions.append(Question(id=identifier, category=category, question=text, input_context=context,
                                  source_ids=source_ids,
                                  origin="CONTROLLED_SCENARIO" if controlled else "REAL_SOURCE").model_dump())
        annotations.append(Annotation(id=identifier, expected_answer=expected,
            evidence_refs=refs(source_ids, fields or ["vulnerabilities", "cvss_severities", "references"]),
            confidence="MEDIUM" if controlled else "HIGH", review_status="PENDING",
            annotator_type="MACHINE", reviewer_type="MACHINE", annotator="", reviewer="",
            annotation_note=("Machine reference draft; human annotation and independent review required. "
                             "Asset inputs are controlled examples; triage labels test the declared reference policy. "
                             "Absent PoC verification is UNKNOWN, not proof of absence."),
            should_abstain=unknown, origin="SOURCE_REFERENCE", required_hops=hops or []).model_dump())

    def asset(identifier, suffix, version):
        record = records[identifier]
        return {"id": f"demo-{identifier}-{suffix}", "component": record["vulnerabilities"][0]["package"]["name"],
                "version": version, "scenario": "CONTROLLED_NOT_PRODUCTION"}

    for sid, (affected, fixed, risk, priority) in SCENARIOS.items():
        record = records[sid]
        cve, component = record["cve_id"], record["vulnerabilities"][0]["package"]["name"]
        context = {"target": cve, "component": component, "ecosystem": "PyPI"}
        cvss = {name: value for name, value in (record.get("cvss_severities") or {}).items()
                if value and value.get("vector_string")}
        add(f"{sid}-facts", "facts", f"查询 {cve} 的描述、CWE 和按版本区分的 CVSS。", context,
            {"cve": cve, "summary": record["summary"], "cwes": [x["cwe_id"] for x in record["cwes"]], "cvss": cvss},
            [sid], fields=["cve_id", "summary", "cwes", "cvss_severities"])
        for suffix, version, label in (("affected", affected, "AFFECTED"),
                                        ("fixed", fixed, "NOT_AFFECTED"), ("unknown", None, "UNKNOWN")):
            add(f"{sid}-{suffix}", "version", f"{component} 版本 {version or '未提供'} 是否受 {cve} 影响？",
                {**context, "version": version}, {"affected": label}, [sid],
                unknown=version is None, controlled=True, fields=["vulnerabilities"])
        fixes = sorted({v["first_patched_version"] for v in record["vulnerabilities"] if v["first_patched_version"]})
        add(f"{sid}-release-and-poc", "poc_patch",
            f"按公告的修复版本记录判断 {cve} 的 release fix；公开 PoC 是否经过独立验证？",
            context, {"poc_status": "UNKNOWN", "patch_status": "CONFIRMED_FIX", "fixed_versions": fixes}, [sid],
            unknown=True)
        commit = next((ref for ref in record["references"] if "/commit/" in ref), None)
        add(f"{sid}-commit-candidate", "poc_patch",
            f"此链接仅出现在 {cve} 的参考文献列表。没有代码验证记录时，能否认定为已验证补丁？",
            {**context, "candidate_reference": commit, "candidate_kind": "patch"},
            {"patch_status": "PATCH_CANDIDATE"}, [sid], fields=["references"])
        for suffix, version, label, level, prio in (("affected", affected, "AFFECTED", risk, priority),
                                                   ("fixed", fixed, "NOT_AFFECTED", "LOW", "MONITOR")):
            add(f"{sid}-risk-{suffix}", "risk",
                f"按 {POLICY} 评估此演示资产对 {cve} 的风险与优先级。",
                {**context, "asset": asset(sid, suffix, version), "triage_policy": POLICY},
                {"affected": label, "risk_level": level, "priority": prio}, [sid], controlled=True)
        assets = [asset(sid, "affected", affected), asset(sid, "fixed", fixed)]
        add(f"{sid}-multihop", "multihop", f"按 {POLICY} 查询公告、比较版本并分析这两个演示资产，哪一个应优先处理？",
            {**context, "assets": assets, "triage_policy": POLICY},
            {"highest_priority_asset": assets[0]["id"], "affected_asset_ids": [assets[0]["id"]]}, [sid],
            controlled=True, hops=["vulnerability", "version", "asset", "risk"])

    langchain = "GHSA-c67j-w6g6-q2cm"
    for suffix, version in (("gap", "0.4.0"), ("older-fix", "0.3.81")):
        add(f"{langchain}-{suffix}", "version", f"langchain-core {version} 是否命中 CVE-2025-68664 的任意影响区间？",
            {"target": "CVE-2025-68664", "component": "langchain-core", "version": version, "ecosystem": "PyPI"},
            {"affected": "NOT_AFFECTED"}, [langchain], controlled=True, fields=["vulnerabilities"])
    ids = ["GHSA-53q9-r3pm-6pq6", langchain, "GHSA-9rwj-6rc7-p77c"]
    assets = [asset(ids[0], "cross", "2.5.1"), asset(ids[1], "cross", "1.2.0"), asset(ids[2], "cross", None)]
    add("cross-advisory-priorities", "multihop", f"结合多份公告，按 {POLICY} 找出须优先处理的演示资产，版本未知者应弃答。",
        {"assets": assets, "triage_policy": POLICY},
        {"affected_asset_ids": [a["id"] for a in assets[:2]], "unknown_asset_ids": [assets[2]["id"]]}, ids,
        controlled=True, hops=["vulnerability", "version", "asset", "risk"])
    add("cross-advisory-missing-version", "multihop", "这些 AI 组件的部署版本均缺失。能够确认资产不受影响吗？",
        {"assets": [asset(sid, "missing", None) for sid in ids], "triage_policy": POLICY},
        {"affected": "UNKNOWN", "risk_level": "UNKNOWN", "priority": "REVIEW"}, ids,
        unknown=True, controlled=True, hops=["vulnerability", "version", "asset", "risk"])

    for name, rows in (("questions.jsonl", questions), ("annotations.jsonl", annotations)):
        (folder / name).write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")
    manifest = {"dataset_version": "AegisBench-v0.2-pilot", "sample_count": len(questions),
                "questions_file": "questions.jsonl", "annotations_file": "annotations.jsonl",
                "questions_sha256": sha256(folder / "questions.jsonl"),
                "annotations_sha256": sha256(folder / "annotations.jsonl"), "sources": sources,
                "split": "PILOT_NOT_INDEPENDENT_HOLDOUT",
                "category_counts": dict(Counter(q["category"] for q in questions)),
                "advisory_clusters": len(records), "model": "NONE", "prompt_version": "NONE",
                "triage_policy": POLICY, "gold_status": "PENDING_HUMAN_REVIEW",
                "limitations": ["Five selected advisory clusters; questions are correlated.",
                    "Not an independent holdout; some vulnerabilities appeared in development fixtures.",
                    "No verified exploit execution evidence; positive PoC classes lack coverage.",
                    "Patch release confirmation is separate from commit correctness or exploit validation.",
                    "Asset risk labels are policy-conformance drafts, not production risk ground truth."]}
    write_json(folder / "manifest.json", manifest)
    data = load_benchmark(folder / "manifest.json")
    print(json.dumps({"samples": len(data["questions"]), "sources": len(data["sources"]),
                      "eligible_gold": len(data["eligible_gold"]), "categories": manifest["category_counts"]}))


if __name__ == "__main__":
    main()
