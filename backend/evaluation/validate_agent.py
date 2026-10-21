"""Repeated live evaluation with frozen development/held-out labels and provenance."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import urllib.request

from backend.agent.classifier import OLLAMA_MODEL, VALID_CATEGORIES, SLA_MAP, classify_ticket, create_classifier
from backend.agent.runtime import runner
from backend.agent.triage import triage_ticket
from backend.config import DATA_DIR, KNOWLEDGE_BASE_DIR, OUTPUT_DIR, OLLAMA_BASE_URL
from backend.evaluation.metrics import classification_metrics, critical_escalation_recall
from backend.rag.kb import load_knowledge_base
from backend.rag.vector import create_vector_store


def provenance():
    files = sorted(KNOWLEDGE_BASE_DIR.glob("*.md")) + [Path(__file__).parents[1] / "agent" / "classifier.py",
                                                     Path(__file__).parents[1] / "agent" / "policy.py",
                                                     Path(__file__).parents[1] / "agent" / "responder.py",
                                                     Path(__file__).parents[1] / "rag" / "vector.py"]
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    with urllib.request.urlopen(OLLAMA_BASE_URL.rstrip("/") + "/api/tags", timeout=5) as response:
        models = [{"name": row["name"], "digest": row.get("digest")} for row in json.load(response)["models"]]
    return {"model": OLLAMA_MODEL, "file_hashes": hashes, "model_digests": models,
            "note": "One-issue scope. Development cases were used in fixes. Held-out labels were frozen before this run; not a population accuracy estimate."}


def verify_reply(result, case):
    if result["decision"] != "AUTO_REPLY":
        return {"grounded": None, "expected_fact_check": None}
    from backend.agent.responder import DISCLAIMER
    response = result["response"]
    prefix = "According to our support FAQ:\n\n"
    suffix = "\n\n" + DISCLAIMER
    paragraphs = {p.strip() for item in result.get("_evidence", []) for p in item["content"].split("\n\n") if p.strip()}
    valid_format = response.startswith(prefix) and response.endswith(suffix)
    selected = response[len(prefix):-len(suffix)].split("\n\n") if valid_format else []
    grounded = bool(selected) and all(p in paragraphs for p in selected)
    normalized = " ".join(response.lower().split())
    return {"grounded": grounded, "expected_fact_check": all(" ".join(text.lower().split()) in normalized for text in case.get("expected_response_contains", []))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-development", action="store_true")
    parser.add_argument("--holdout", default="heldout_single_issue.json")
    parser.add_argument("--output", default="agent_validation_results.json")
    args = parser.parse_args()
    destination = OUTPUT_DIR / args.output
    report = {"provenance": provenance(), "complete": False, "development_runs": [], "heldout_runs": []}
    development = json.loads((DATA_DIR / "retrieval_challenge.json").read_text())
    heldout = json.loads((DATA_DIR / args.holdout).read_text())
    report["provenance"]["dataset_hashes"] = {
        name: hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest()
        for name in ("retrieval_challenge.json", args.holdout)
    }
    store = create_vector_store(load_knowledge_base(KNOWLEDGE_BASE_DIR))
    model = create_classifier()

    def save():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")

    for repeat in range(0 if args.skip_development else 2):
        run = {"repeat": repeat + 1, "cases": []}
        report["development_runs"].append(run)
        for index, case in enumerate(development, 1):
            print(f"Development {repeat+1}: {index}/{len(development)} {case['id']}", flush=True)
            docs = [doc for doc, score in store.similarity_search_with_relevance_scores(case["query"], k=2) if score >= 0.5]
            context = "\n\n".join(doc.page_content for doc in docs)
            assessment = runner.run(classify_ticket, model, case["query"], context)
            from backend.agent.router import route_ticket
            decision = route_ticket(assessment, False)
            run["cases"].append({"id": case["id"], "expected_can_auto_reply": case["expected_can_auto_reply"],
                                 "assessment": assessment, "decision": decision})
            save()
        run["unsafe_auto_reply_decisions"] = sum(not row["expected_can_auto_reply"] and row["decision"] == "AUTO_REPLY" for row in run["cases"])
        run["answerable_tickets_escalated"] = sum(row["expected_can_auto_reply"] and row["decision"] == "ESCALATE" for row in run["cases"])
        run["fallbacks"] = sum("Invalid model assessment; human review required." in row["assessment"]["reason"] for row in run["cases"])
        run["zero_confidence_assessments"] = sum(row["assessment"]["confidence"] == 0 for row in run["cases"])
        save()

    for repeat in range(2):
        run = {"repeat": repeat + 1, "cases": []}
        report["heldout_runs"].append(run)
        for index, case in enumerate(heldout, 1):
            print(f"Held-out {repeat+1}: {index}/{len(heldout)} {case['id']}", flush=True)
            started = perf_counter()
            result = runner.run(triage_ticket, case["subject"], case["body"])
            run["cases"].append({**case, "result": result, "reply_checks": verify_reply(result, case), "seconds": perf_counter() - started})
            save()
        run["metrics"] = {
            field: classification_metrics([row["expected_" + field] for row in run["cases"]],
                                           [row["result"][field] for row in run["cases"]], labels)
            for field, labels in (("category", VALID_CATEGORIES), ("decision", {"ESCALATE", "AUTO_REPLY"}), ("urgency", SLA_MAP))
        }
        run["critical_escalation_recall"] = critical_escalation_recall(
            [row["expected_urgency"] for row in run["cases"]], [row["result"]["decision"] for row in run["cases"]])
        run["unsafe_auto_reply_decisions"] = sum(row["expected_decision"] == "ESCALATE" and row["result"]["decision"] == "AUTO_REPLY" for row in run["cases"])
        run["grounding_failures"] = sum(row["reply_checks"]["grounded"] is False for row in run["cases"])
        run["expected_fact_check_failures"] = sum(row["reply_checks"]["expected_fact_check"] is False for row in run["cases"])
        run["safety_flag_mismatches"] = [row["id"] for row in run["cases"] if "expected_is_suspicious" in row and row["expected_is_suspicious"] != row["result"]["is_suspicious"]]
        run["auto_reply_count"] = sum(row["result"]["decision"] == "AUTO_REPLY" for row in run["cases"])
        save()
    report["complete"] = True
    save()
    print(f"Report: {destination}", flush=True)
    print(json.dumps({"development": [{k: v for k, v in run.items() if k != "cases"} for run in report["development_runs"]],
                      "heldout": [{k: v for k, v in run.items() if k not in {"cases", "metrics"}} for run in report["heldout_runs"]]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
