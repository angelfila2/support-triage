import json
from unittest.mock import Mock

import pytest

from backend.agent.responder import generate_response
from backend.evaluation.metrics import classification_metrics, critical_escalation_recall


def test_response_only_contains_verified_full_passages():
    context = "Reset links expire after 30 minutes. Request a new link if it expires."
    model = Mock()
    model.invoke.return_value = json.dumps({"passage_ids": [0]})
    assert context in generate_response(model, "Expired reset link", context)
    model.invoke.return_value = json.dumps({"passage_ids": [99]})
    assert generate_response(model, "Expired reset link", context) == ""


def test_procedure_introduction_cannot_be_selected_without_steps():
    context = "Try these steps:\n\n1. Try another browser\n2. Clear cookies\n3. Try incognito mode\n4. Try another machine\n\nEscalate if the issue persists."
    model = Mock()
    model.invoke.return_value = json.dumps({"passage_ids": [0]})
    response = generate_response(model, "Cannot sign in", context)
    assert "Try these steps:" in response
    assert "1. Try another browser" in response
    assert "2. Clear cookies" in response


def test_expired_link_reply_includes_documented_replacement_action():
    context = "Password reset links expire after 30 minutes.\n\nIf expired, request a new password reset email."
    model = Mock()
    model.invoke.return_value = json.dumps({"passage_ids": [0]})
    response = generate_response(model, "My password reset link expired", context)
    assert "request a new password reset email" in response
    model.invoke.return_value = json.dumps({"passage_ids": [True]})
    assert generate_response(model, "Expired reset link", context) == ""


def test_macro_metrics_include_missed_classes():
    result = classification_metrics(["a", "a", "b"], ["a", "a", "a"])
    assert result["accuracy"] == pytest.approx(2 / 3)
    assert result["macro_recall"] == 0.5
    assert result["per_class"]["b"]["f1"] == 0
    assert critical_escalation_recall(["SEV1", "SEV2", "SEV5"], ["ESCALATE", "AUTO_REPLY", "AUTO_REPLY"]) == 0.5
    assert critical_escalation_recall(["SEV5"], ["AUTO_REPLY"]) is None


def test_evaluator_reports_separate_intent_routing_and_severity(tmp_path, monkeypatch, capsys):
    from backend.evaluation import evaluate
    path = tmp_path / "predictions.csv"
    path.write_text(
        "category,expected_category,decision,expected_decision,urgency,expected_urgency\n"
        "other,other,ESCALATE,ESCALATE,SEV1,SEV1\n"
        "password_reset,password_reset,AUTO_REPLY,AUTO_REPLY,SEV4,SEV4\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(evaluate, "TRIAGE_RESULTS_FILE", path)
    evaluate.main()
    report = json.loads(capsys.readouterr().out)
    assert report["intent"]["accuracy"] == 1.0
    assert report["routing"]["macro_f1"] == 1.0
    assert report["severity"]["per_class"]["SEV1"]["recall"] == 1.0
    assert report["critical_escalation_recall"] == 1.0
