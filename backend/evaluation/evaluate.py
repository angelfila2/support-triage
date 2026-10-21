"""Report intent, routing and severity metrics from batch predictions."""

import csv
import json
from backend.config import TRIAGE_RESULTS_FILE
from backend.agent.classifier import VALID_CATEGORIES, SLA_MAP
from backend.evaluation.metrics import classification_metrics, critical_escalation_recall


def main():
    if not TRIAGE_RESULTS_FILE.exists():
        print(f"Error: Results file not found at {TRIAGE_RESULTS_FILE}")
        print("Please run `python -m backend.evaluation.main` first.")
        raise SystemExit(1)
    with TRIAGE_RESULTS_FILE.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("Results contain no tickets.")
    report = {}
    for name, field, labels in [("intent", "category", VALID_CATEGORIES),
                                 ("routing", "decision", {"AUTO_REPLY", "ESCALATE"}),
                                 ("severity", "urgency", SLA_MAP)]:
        if any(not row.get("expected_" + field) or not row.get(field) for row in rows):
            raise ValueError(f"Missing prediction/ground-truth labels for {name}.")
        report[name] = classification_metrics([r["expected_"+field] for r in rows],
                                              [r[field] for r in rows], labels)
    report["critical_escalation_recall"] = critical_escalation_recall(
        [r["expected_urgency"] for r in rows], [r["decision"] for r in rows])
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
