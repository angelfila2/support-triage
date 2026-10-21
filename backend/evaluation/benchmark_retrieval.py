"""Compare retrieval thresholds against a labelled development dataset."""

import json
from pathlib import Path
from statistics import mean
from time import perf_counter

from backend.config import (
    DATA_DIR,
    KNOWLEDGE_BASE_DIR,
    OUTPUT_DIR,
)
from backend.rag.kb import load_knowledge_base
from backend.rag.vector import create_vector_store


TOP_K = 2
THRESHOLDS = [None, 0.3, 0.5, 0.7, 0.9]


def source_name(document):
    """Normalize source paths so labels work on Windows and Linux."""

    source = str(document.metadata.get("source", ""))
    return source.replace("\\", "/").rsplit("/", 1)[-1]


def load_cases(path):
    """Validate benchmark inputs before running expensive operations."""

    cases = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(cases, list) or not cases:
        raise ValueError("Benchmark must contain a nonempty list.")

    known_sources = {
        path.name
        for path in KNOWLEDGE_BASE_DIR.glob("*.md")
    }

    seen_ids = set()

    for case in cases:
        case_id = case["id"]
        query = case["query"]
        expected = case["expected_sources"]

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("Each case requires a nonempty string ID.")

        if case_id in seen_ids:
            raise ValueError(f"Duplicate case ID: {case_id}")

        seen_ids.add(case_id)

        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Invalid query: {case_id}")

        if not isinstance(expected, list) or not all(
            isinstance(source, str) for source in expected
        ):
            raise ValueError(f"Invalid expected_sources: {case_id}")

        if not set(expected).issubset(known_sources):
            raise ValueError(f"Unknown FAQ source: {case_id}")

    if not any(case["expected_sources"] for case in cases):
        raise ValueError("Include at least one supported query.")

    if not any(not case["expected_sources"] for case in cases):
        raise ValueError("Include at least one unsupported query.")

    return cases


def collect_candidates(vector_store, cases):
    """Collect actual embedding results without applying a threshold."""

    observations = []

    for case in cases:
        started = perf_counter()

        matches = vector_store.similarity_search_with_relevance_scores(
            case["query"],
            k=TOP_K,
        )

        elapsed_ms = (perf_counter() - started) * 1000

        observations.append({
            "id": case["id"],
            "query": case["query"],
            "expected_sources": case["expected_sources"],
            "retrieval_ms": elapsed_ms,
            "candidates": [
                {
                    "source": source_name(document),
                    "score": float(score),
                }
                for document, score in matches
            ],
        })

    return observations


def evaluate_threshold(observations, threshold):
    """Score relevance and rejection separately."""

    recalls = []
    precisions = []
    unsupported_rejections = []
    exact_matches = []
    details = []

    for observation in observations:
        expected = set(observation["expected_sources"])

        selected = [
            candidate
            for candidate in observation["candidates"]
            if threshold is None
            or candidate["score"] >= threshold
        ]

        predicted = {
            candidate["source"]
            for candidate in selected
        }

        correct = expected & predicted

        if expected:
            recalls.append(len(correct) / len(expected))
            precisions.append(
                len(correct) / len(predicted)
                if predicted
                else 0.0
            )
        else:
            unsupported_rejections.append(not predicted)

        exact_matches.append(predicted == expected)

        details.append({
            **observation,
            "retrieved_sources": sorted(predicted),
            "exact_match": predicted == expected,
        })

    return {
        "threshold": threshold,
        "supported_recall": mean(recalls),
        "supported_precision": mean(precisions),
        "unsupported_rejection_rate": mean(unsupported_rejections),
        "exact_source_match_rate": mean(exact_matches),
        "cases": details,
    }


def main():
    dataset_path = DATA_DIR / "retrieval_benchmark.json"
    cases = load_cases(dataset_path)

    print("Building the FAQ index...")
    documents = load_knowledge_base(KNOWLEDGE_BASE_DIR)
    vector_store = create_vector_store(documents)

    print(f"Retrieving candidates for {len(cases)} queries...")
    observations = collect_candidates(vector_store, cases)

    results = [
        evaluate_threshold(observations, threshold)
        for threshold in THRESHOLDS
    ]

    print()
    print(
        f"{'Threshold':<12}"
        f"{'Recall':>12}"
        f"{'Precision':>12}"
        f"{'Reject OOD':>12}"
        f"{'Exact match':>14}"
    )

    for result in results:
        label = (
            "unfiltered"
            if result["threshold"] is None
            else str(result["threshold"])
        )

        print(
            f"{label:<12}"
            f"{result['supported_recall']:>12.1%}"
            f"{result['supported_precision']:>12.1%}"
            f"{result['unsupported_rejection_rate']:>12.1%}"
            f"{result['exact_source_match_rate']:>14.1%}"
        )

    average_ms = mean(
        observation["retrieval_ms"]
        for observation in observations
    )

    print(f"\nMean query retrieval time: {average_ms:.1f} ms")
    print("Timing includes query embedding and search, not index creation.")
    print("All thresholds reuse the same candidates and timings.")
    print("Development results only; no automatic threshold selection.")

    report_path = OUTPUT_DIR / "retrieval_benchmark_results.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "dataset": str(dataset_path),
        "top_k": TOP_K,
        "case_count": len(cases),
        "mean_query_retrieval_ms": average_ms,
        "results": results,
    }

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"Detailed results: {report_path}")


if __name__ == "__main__":
    main()