"""Live development evaluation of answerability; no ticket writes or replies."""

import json
from time import perf_counter

from backend.agent.classifier import create_classifier, classify_ticket, OLLAMA_MODEL
from backend.agent.router import route_ticket
from backend.config import DATA_DIR, KNOWLEDGE_BASE_DIR, OUTPUT_DIR
from backend.evaluation.benchmark_retrieval import load_cases, source_name
from backend.rag.kb import load_knowledge_base
from backend.rag.vector import create_vector_store



def summarize(rows):
    unsafe = sum(not r["expected_can_auto_reply"] and r["decision"] == "AUTO_REPLY" for r in rows)
    false_permissions = sum(not r["expected_can_auto_reply"] and r["assessment"]["can_auto_reply"] for r in rows)
    unnecessary = sum(r["expected_can_auto_reply"] and r["decision"] == "ESCALATE" for r in rows)
    correct = sum(r["expected_can_auto_reply"] == r["assessment"]["can_auto_reply"] for r in rows)
    return {"evaluated": len(rows), "answerability_correct": correct,
            "false_answerability_permissions": false_permissions,
            "unsafe_auto_reply_decisions": unsafe,
            "answerable_tickets_escalated": unnecessary}


def main():
    cases = load_cases(DATA_DIR / "retrieval_challenge.json")
    if any(type(case.get("expected_can_auto_reply")) is not bool for case in cases):
        raise ValueError("Every challenge case needs a boolean answerability annotation.")
    print(f"Building retrieval and classifier ({OLLAMA_MODEL})...", flush=True)
    store = create_vector_store(load_knowledge_base(KNOWLEDGE_BASE_DIR))
    model = create_classifier()
    path = OUTPUT_DIR / "answerability_benchmark_results.json"
    rows = []
    for index, case in enumerate(cases, 1):
        print(f"[{index}/{len(cases)}] {case['id']}", flush=True)
        started = perf_counter()
        matches = store.similarity_search_with_relevance_scores(case["query"], k=2)
        selected = [(doc, score) for doc, score in matches if score >= 0.5]
        context = "\n\n".join(doc.page_content for doc, _ in selected)
        assessment = classify_ticket(model, case["query"], context)
        raw_answerability = assessment["can_auto_reply"]
        if not selected:
            assessment["can_auto_reply"] = False
        decision = route_ticket(assessment, False)
        rows.append({"id": case["id"], "query": case["query"],
                     "expected_can_auto_reply": case["expected_can_auto_reply"],
                     "expected_troubleshooting_exhausted": case.get("expected_troubleshooting_exhausted"),
                     "sources": [{"source": source_name(doc), "score": score} for doc, score in selected],
                     "classifier_can_auto_reply_before_guard": raw_answerability,
                     "assessment": assessment, "decision": decision,
                     "elapsed_seconds": perf_counter() - started})
        print(f"  expected={case['expected_can_auto_reply']} actual={assessment['can_auto_reply']} route={decision}", flush=True)
        # Save partial progress so a failed later call cannot erase earlier observations.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": OLLAMA_MODEL, "threshold": 0.5,
                                   "top_k": 2, "complete": len(rows) == len(cases),
                                   "summary": summarize(rows),
                                   "fallback_count": sum(r["assessment"]["reason"] == "Invalid model assessment; human review required." for r in rows),
                                   "troubleshooting_flag_mistakes": [r["id"] for r in rows if r["expected_troubleshooting_exhausted"] is not None and r["expected_troubleshooting_exhausted"] != r["assessment"]["troubleshooting_exhausted"]],
                                   "cases": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summarize(rows), indent=2), flush=True)
    print(f"Report: {path}", flush=True)


if __name__ == "__main__":
    main()
