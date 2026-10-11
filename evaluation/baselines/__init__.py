"""Explicit experiment readiness; unavailable variants never imitate model runs."""


def baseline_readiness(name, metadata):
    if name == "rag_only":
        return {"status": "BLOCKED", "reason": "No configured real generation LLM adapter; vector retrieval alone is not RAG-only QA"}
    if name == "no_verification":
        return {"status": "BLOCKED", "reason": "Backend exposes no isolated no-verification control; modifying global verification would invalidate fairness"}
    if name in {"hybrid_fixed", "full_agent", "vector_retrieval"}:
        return {"status": "READY", "reason": "Executes existing runtime adapter; model-free capability disclosed separately"}
    raise ValueError("Unknown baseline variant")
