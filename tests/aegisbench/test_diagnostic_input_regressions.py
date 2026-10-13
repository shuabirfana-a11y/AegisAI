"""Input-context fidelity controls; no labels or benchmark answers are invented."""
from copy import deepcopy
from uuid import uuid4

import pytest

from evaluation.bench.http_investigation import build_request, input_values
from evaluation.bench.schema import Question


def question(category="risk", **overrides):
    context = {"target": "CVE-2099-0001", "component": "torch", "ecosystem": "PyPI",
               "asset": {"component": "torch", "version": "2.5.1",
                         "id": "synthetic-affected-hint", "scenario": "TEST_FIXTURE"}}
    context.update(overrides)
    return Question(id="synthetic-diagnostic-case", category=category,
        question="Inspect the supplied vulnerability", input_context=context,
        origin="TEST_FIXTURE", source_ids=["synthetic-source"])


def binding():
    return {"asset_id": str(uuid4()), "component_id": str(uuid4())}


def test_singular_asset_version_reaches_the_actual_public_request():
    q = question()
    original = deepcopy(q.input_context)
    body = build_request(q, binding())
    assert body["asset_scope"]["component"]["version"] == "2.5.1"
    assert body["options"]["objective_profile"] == "asset_risk_v1"
    assert q.input_context == original
    assert "synthetic-affected-hint" not in str(body)
    assert "scenario" not in str(body)


def test_conflicting_asset_and_top_level_versions_are_rejected():
    with pytest.raises(ValueError, match="INPUT_CONTEXT_CONFLICT"):
        build_request(question(version="2.6.0"), binding())


def test_singular_and_plural_assets_cannot_silently_choose_one():
    with pytest.raises(ValueError, match="AMBIGUOUS_ASSET_INPUT"):
        input_values(question(assets=[{"component": "torch", "version": "2.6.0"}]))


@pytest.mark.parametrize("category", ["facts", "poc_patch"])
def test_overview_component_hint_does_not_request_owned_asset_analysis(category):
    q = Question(id="synthetic-overview", category=category,
        question="Read the supplied vulnerability advisory", origin="TEST_FIXTURE",
        source_ids=["synthetic-source"], input_context={"component": "torch",
            "ecosystem": "PyPI", "target": "CVE-2099-0001"})
    body = build_request(q)
    assert body["asset_scope"] == {"target": "CVE-2099-0001"}
    assert body["user_query"] == q.question
    assert body["options"]["objective_profile"] == "overview_v1"


def test_plural_single_asset_and_flat_version_requests_keep_their_inputs():
    plural = Question(id="synthetic-plural", category="version",
        question="Inspect this version", origin="TEST_FIXTURE", source_ids=["s"],
        input_context={"target": "CVE-2099-0001", "ecosystem": "PyPI",
            "assets": [{"component": "torch", "version": "2.5.1"}]})
    flat = plural.model_copy(update={"input_context": {"target": "CVE-2099-0001",
        "ecosystem": "PyPI", "component": "torch", "version": "2.5.1"}})
    for q in [plural, flat]:
        body = build_request(q, binding())
        assert body["asset_scope"]["component"]["version"] == "2.5.1"


def test_component_only_overview_without_exact_target_preserves_search_hint():
    q = Question(id="synthetic-product-search", category="facts",
        question="Find advisories for this component", origin="TEST_FIXTURE",
        source_ids=["s"], input_context={"component": "torch", "ecosystem": "PyPI"})
    body = build_request(q)
    assert body["asset_scope"]["component"]["package_name"] == "torch"
