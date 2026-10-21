"""Zero-division-safe classification metrics; labels are separate from predictions."""


def classification_metrics(expected, predicted, labels=None):
    if len(expected) != len(predicted) or not expected:
        raise ValueError("Expected/predicted must be nonempty and equally sized.")
    labels = sorted(set(labels or []) | set(expected) | set(predicted))
    rows = {}
    for label in labels:
        tp = sum(a == b == label for a, b in zip(expected, predicted))
        fp = sum(a != label and b == label for a, b in zip(expected, predicted))
        fn = sum(a == label and b != label for a, b in zip(expected, predicted))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows[label] = dict(precision=precision, recall=recall, f1=f1, support=tp + fn)
    return dict(
        accuracy=sum(a == b for a, b in zip(expected, predicted)) / len(expected),
        macro_precision=sum(row["precision"] for row in rows.values()) / len(rows),
        macro_recall=sum(row["recall"] for row in rows.values()) / len(rows),
        macro_f1=sum(row["f1"] for row in rows.values()) / len(rows),
        per_class=rows,
    )


def critical_escalation_recall(severities, decisions):
    if len(severities) != len(decisions):
        raise ValueError("Severity/decision lengths differ.")
    critical = [decision for severity, decision in zip(severities, decisions)
                if severity in {"SEV1", "SEV2"}]
    return sum(decision == "ESCALATE" for decision in critical) / len(critical) if critical else None
