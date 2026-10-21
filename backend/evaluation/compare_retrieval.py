"""Compare top-1 and top-2 on fixed development candidates, not production traffic."""

import json

from backend.config import DATA_DIR, KNOWLEDGE_BASE_DIR, OUTPUT_DIR
from backend.evaluation.benchmark_retrieval import (
    THRESHOLDS, collect_candidates, evaluate_threshold, load_cases,
)
from backend.rag.kb import load_knowledge_base
from backend.rag.vector import create_vector_store


def compare_candidates(observations):
    results = []
    for k in (1, 2):
        limited = [
            {**row, "candidates": row["candidates"][:k]}
            for row in observations
        ]
        for threshold in THRESHOLDS:
            results.append({"top_k": k, **evaluate_threshold(limited, threshold)})
    return results


def main():
    datasets = [
        (name, load_cases(DATA_DIR / name))
        for name in ("retrieval_benchmark.json", "retrieval_challenge.json")
    ]
    print("Building one shared cosine index...", flush=True)
    store = create_vector_store(load_knowledge_base(KNOWLEDGE_BASE_DIR))
    reports = []
    for name, cases in datasets:
        print(f"Retrieving {len(cases)} queries: {name}", flush=True)
        observations = collect_candidates(store, cases)
        results = compare_candidates(observations)
        reports.append({"dataset": name, "case_count": len(cases), "results": results})
        print(" k threshold     recall precision rejection exact", flush=True)
        for result in results:
            label = "none" if result["threshold"] is None else str(result["threshold"])
            print(
                f" {result['top_k']} {label:<10} "
                f"{result['supported_recall']:>6.1%} "
                f"{result['supported_precision']:>9.1%} "
                f"{result['unsupported_rejection_rate']:>9.1%} "
                f"{result['exact_source_match_rate']:>6.1%}", flush=True,
            )
    path = OUTPUT_DIR / "retrieval_comparison_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "note": "Development only. Top-1 is a prefix of the same top-2 candidates; "
                "timings measure shared top-2 retrieval, not separate top-1 runs.",
        "datasets": reports,
    }, indent=2), encoding="utf-8")
    print(f"Report: {path}", flush=True)


if __name__ == "__main__":
    main()
