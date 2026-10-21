"""Verify benchmark arithmetic using hand-calculated results, without Ollama."""

import json
from unittest.mock import Mock

import pytest
from langchain_core.documents import Document

from backend.evaluation import benchmark_retrieval as benchmark


@pytest.fixture
def observations():
    return [
        {"id": "supported", "expected_sources": ["billing.md"], "candidates": [
            {"source": "billing.md", "score": 0.8},
            {"source": "shipping.md", "score": 0.4},
        ]},
        {"id": "unsupported", "expected_sources": [], "candidates": [
            {"source": "billing.md", "score": 0.3},
        ]},
    ]


def test_unfiltered_baseline_has_false_acceptance(observations):
    result = benchmark.evaluate_threshold(observations, None)
    assert result["supported_recall"] == 1.0
    assert result["supported_precision"] == 0.5
    assert result["unsupported_rejection_rate"] == 0.0
    assert result["exact_source_match_rate"] == 0.0


def test_threshold_keeps_boundary_match_and_rejects_noise(observations):
    result = benchmark.evaluate_threshold(observations, 0.8)
    assert result["supported_recall"] == 1.0
    assert result["supported_precision"] == 1.0
    assert result["unsupported_rejection_rate"] == 1.0
    assert result["exact_source_match_rate"] == 1.0


def test_strict_threshold_reveals_lost_recall(observations):
    result = benchmark.evaluate_threshold(observations, 0.9)
    assert result["supported_recall"] == 0.0
    assert result["supported_precision"] == 0.0
    assert result["unsupported_rejection_rate"] == 1.0
    assert result["exact_source_match_rate"] == 0.5


def test_multiple_relevant_sources_use_fractional_recall(observations):
    observations[0]["expected_sources"] = ["billing.md", "login_issues.md"]
    result = benchmark.evaluate_threshold(observations, 0.5)
    assert result["supported_recall"] == 0.5
    assert result["supported_precision"] == 1.0


def test_candidates_are_collected_once_and_scores_preserved():
    store = Mock()
    store.similarity_search_with_relevance_scores.return_value = [
        (Document(page_content="FAQ", metadata={"source": "C:\\faq\\billing.md"}), 0.75)
    ]
    cases = [{"id": "one", "query": "invoice", "expected_sources": ["billing.md"]}]
    observations = benchmark.collect_candidates(store, cases)
    store.similarity_search_with_relevance_scores.assert_called_once_with("invoice", k=2)
    assert observations[0]["candidates"] == [{"source": "billing.md", "score": 0.75}]
    assert observations[0]["retrieval_ms"] >= 0


def test_repository_dataset_loads():
    cases = benchmark.load_cases(benchmark.DATA_DIR / "retrieval_benchmark.json")
    assert len(cases) == 18


def test_challenge_dataset_covers_single_issues_and_policy_labels():
    cases = benchmark.load_cases(benchmark.DATA_DIR / "retrieval_challenge.json")
    assert len(cases) == 26
    assert all(len(case["expected_sources"]) <= 1 for case in cases)
    assert all(type(case["expected_can_auto_reply"]) is bool for case in cases)
    assert sum(not case["expected_sources"] for case in cases) == 6


def test_top_one_comparison_exposes_multi_issue_recall_loss():
    from backend.evaluation.compare_retrieval import compare_candidates

    rows = [
        {"expected_sources": ["billing.md", "shipping.md"], "candidates": [
            {"source": "billing.md", "score": 0.8},
            {"source": "shipping.md", "score": 0.7},
        ]},
        {"expected_sources": [], "candidates": []},
    ]
    results = compare_candidates(rows)
    one = next(r for r in results if r["top_k"] == 1 and r["threshold"] == 0.5)
    two = next(r for r in results if r["top_k"] == 2 and r["threshold"] == 0.5)
    assert one["supported_recall"] == 0.5
    assert two["supported_recall"] == 1.0
    assert len(rows[0]["candidates"]) == 2


@pytest.mark.parametrize("problem", ["duplicate", "unknown", "empty_query", "no_supported", "no_unsupported"])
def test_invalid_dataset_is_rejected(tmp_path, problem):
    cases = [
        {"id": "a", "query": "invoice", "expected_sources": ["billing.md"]},
        {"id": "b", "query": "recipe", "expected_sources": []},
    ]
    if problem == "duplicate":
        cases[1]["id"] = "a"
    elif problem == "unknown":
        cases[0]["expected_sources"] = ["missing.md"]
    elif problem == "empty_query":
        cases[0]["query"] = " "
    elif problem == "no_supported":
        cases = cases[1:]
    else:
        cases = cases[:1]
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    with pytest.raises(ValueError):
        benchmark.load_cases(path)
