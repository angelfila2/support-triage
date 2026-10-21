"""Exercise the complete sample export without making live model calls."""

import csv

from backend.evaluation import run_batch


def test_batch_processes_all_samples_and_preserves_separate_labels(tmp_path, monkeypatch):
    with run_batch.SAMPLE_TICKETS_FILE.open(encoding="utf-8", newline="") as source:
        samples = list(csv.DictReader(source))
    calls = []

    def fake_triage(subject, body):
        calls.append((subject, body))
        return {
            "category": "other", "urgency": "SEV3", "confidence": 90,
            "decision": "ESCALATE", "is_suspicious": False,
            "reason": "Synthetic test assessment", "response": "",
            "sla": "3 days", "retrieved_sources": [],
        }

    output = tmp_path / "predictions.csv"
    monkeypatch.setattr(run_batch, "TRIAGE_RESULTS_FILE", output)
    monkeypatch.setattr(run_batch, "triage_ticket", fake_triage)
    for _ in range(2):
        run_batch.main()
        with output.open(encoding="utf-8", newline="") as source:
            predictions = list(csv.DictReader(source))
        assert len(predictions) == len(samples) == 30
        for prediction, sample in zip(predictions, samples):
            for field in ("expected_category", "expected_decision", "expected_urgency"):
                assert prediction[field] == sample[field]
    assert len(calls) == 60
