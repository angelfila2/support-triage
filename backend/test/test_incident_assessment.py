"""Policy tests use supplied semantic facts; live-model checks are separate."""
import json
from unittest.mock import Mock

import pytest

from backend.agent.classifier import classify_ticket
from backend.agent.router import route_ticket
from backend.agent import triage


def assessment(text, **facts):
    incident = {
        "impact_scope": "individual", "service_availability": "unavailable",
        "incident_status": "ongoing", "workaround_available": "unknown",
        "security_impact": "none", "evidence": [text],
    }
    incident.update(facts)
    return {"category": "login_issues", "urgency": "SEV4", "confidence": 95,
            "reason": "Ticket impact assessed.", "troubleshooting_exhausted": False,
            "can_auto_reply": True, "incident": incident}


@pytest.mark.parametrize(("text", "facts", "severity"), [
    ("ALL SYSTEMS DOWN", {"impact_scope": "widespread"}, "SEV1"),
    ("Nobody can access the platform", {"impact_scope": "widespread"}, "SEV1"),
    ("The platform is offline for every customer", {"impact_scope": "widespread"}, "SEV1"),
    ("Several colleagues cannot use the app", {"impact_scope": "multiple_users"}, "SEV2"),
    ("The platform seems broken, not sure who else is affected", {"impact_scope": "unknown"}, "SEV2"),
    ("Our service has a confirmed major security incident", {"security_impact": "major_breach"}, "SEV1"),
    ("Customer records have been irrecoverably lost", {"security_impact": "severe_data_loss"}, "SEV1"),
])
def test_semantic_facts_override_low_model_severity(text, facts, severity):
    model = Mock()
    model.invoke.return_value = json.dumps(assessment(text, **facts))
    result = classify_ticket(model, text, "Try a different browser and clear cookies.")
    assert result["urgency"] == severity
    assert not result["can_auto_reply"]
    assert route_ticket(result, False) == "ESCALATE"
    model.invoke.assert_called_once()


@pytest.mark.parametrize(("text", "status"), [
    ("Everyone can log in now; the outage is resolved", "resolved"),
    ("What should we do if all systems go down?", "hypothetical"),
    ("There is no breach. I just need a copy of my invoice", "not_incident"),
])
def test_negated_historical_or_hypothetical_incidents_are_not_current_emergencies(text, status):
    payload = assessment(text, impact_scope="widespread", service_availability="available", incident_status=status)
    payload["urgency"] = "SEV1"  # Even a contradictory severity label must follow assessed status.
    model = Mock()
    model.invoke.return_value = json.dumps(payload)
    result = classify_ticket(model, text, "FAQ")
    assert result["urgency"] not in {"SEV1", "SEV2"}


def test_single_user_login_problem_is_not_a_widespread_outage():
    text = "Only my account cannot log in"
    model = Mock()
    model.invoke.return_value = json.dumps(assessment(text))
    result = classify_ticket(model, text, "Try a different browser and clear cookies.")
    assert result["urgency"] == "SEV3"


@pytest.mark.parametrize("change", ["missing", "invalid_scope", "fake_evidence", "missing_evidence", "bad_evidence_type"])
def test_invalid_incident_assessment_requires_priority_human_review(change):
    text = "ALL SYSTEMS DOWN"
    payload = assessment(text, impact_scope="widespread")
    if change == "missing":
        del payload["incident"]
    elif change == "invalid_scope":
        payload["incident"]["impact_scope"] = "a lot"
    elif change == "fake_evidence":
        payload["incident"]["evidence"] = ["Invented customer statement"]
    elif change == "missing_evidence":
        payload["incident"]["evidence"] = []
    else:
        payload["incident"]["evidence"] = "ALL SYSTEMS DOWN"
    model = Mock()
    model.invoke.return_value = json.dumps(payload)
    result = classify_ticket(model, text, "FAQ")
    assert result["confidence"] == 0
    assert result["urgency"] == "SEV2"
    assert route_ticket(result, False) == "ESCALATE"


def test_full_pipeline_escalates_outage_without_generating_a_reply(monkeypatch):
    text = "ALL SYSTEMS DOWN"
    classifier, responder, retriever = Mock(), Mock(), Mock()
    classifier.invoke.return_value = json.dumps(assessment(text, impact_scope="widespread"))
    monkeypatch.setattr(triage, "get_engine", lambda: (retriever, classifier, responder))
    monkeypatch.setattr(triage, "retrieve_documents", lambda *args: [])
    result = triage.triage_ticket("Help", text)
    assert result["urgency"] == "SEV1"
    assert result["sla"] == "4 hours"
    assert result["decision"] == "ESCALATE"
    assert result["_assessment"]["incident"]["evidence"] == [text]
    classifier.invoke.assert_called_once()
    responder.invoke.assert_not_called()


def test_confirmed_workaround_keeps_multi_user_disruption_in_standard_human_queue():
    text = "Several colleagues cannot use the app, but the backup portal works"
    payload = assessment(text, impact_scope="multiple_users", workaround_available="yes")
    model = Mock()
    model.invoke.return_value = json.dumps(payload)
    result = classify_ticket(model, text, "FAQ")
    assert result["urgency"] == "SEV3"
    assert route_ticket(result, False) == "ESCALATE"


def test_chat_response_uses_schema_and_keeps_ticket_in_user_message():
    from langchain_core.messages import AIMessage
    text = "ALL SYSTEMS DOWN"
    model = Mock()
    model.invoke.return_value = AIMessage(content=json.dumps(assessment(text, impact_scope="widespread")))
    result = classify_ticket(model, text, "FAQ")
    assert result["urgency"] == "SEV1"
    args, kwargs = model.invoke.call_args
    assert args[0][0]["role"] == "system"
    assert args[0][-1]["role"] == "user"
    assert json.loads(args[0][-1]["content"])["ticket"] == text
    assert "incident" in kwargs["format"]["required"]


def test_faq_quotations_are_discarded_without_losing_valid_ticket_evidence():
    text = "I forgot my password. How do I request a reset link?"
    payload = assessment(text, service_availability="degraded", workaround_available="yes")
    payload["incident"]["evidence"] = [text, "Password reset links expire after 30 minutes."]
    model = Mock()
    model.invoke.return_value = json.dumps(payload)
    result = classify_ticket(model, text, "Password reset links expire after 30 minutes.")
    assert result["urgency"] == "SEV4"
    assert result["confidence"] == 95
    assert result["incident"]["evidence"] == [text]
    assert result["discarded_incident_evidence_count"] == 1
