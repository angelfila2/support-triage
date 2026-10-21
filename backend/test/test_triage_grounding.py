"""Pipeline grounding policy independent of model compliance and availability."""

from unittest.mock import Mock

import pytest
from langchain_core.documents import Document

from backend.agent import triage
from backend.agent.classifier import SLA_MAP


def configure_pipeline(monkeypatch, documents, severity="SEV4", answerable=True):
    monkeypatch.setattr(triage, "get_engine", lambda: ("retriever", "classifier", "responder"))
    monkeypatch.setattr(triage, "retrieve_documents", lambda *args: documents)
    classifier = Mock(return_value={
        "category": "password_reset", "urgency": severity,
        "confidence": 99, "reason": "Model assessment",
        "can_auto_reply": answerable, "sla": SLA_MAP[severity],
    })
    responder = Mock(return_value="Request a new reset link.")
    monkeypatch.setattr(triage, "classify_ticket", classifier)
    monkeypatch.setattr(triage, "generate_response", responder)
    return classifier, responder


@pytest.mark.parametrize("severity", ["SEV1", "SEV2", "SEV3", "SEV4", "SEV5"])
def test_no_evidence_overrides_model_and_never_generates_reply(monkeypatch, severity):
    classifier, responder = configure_pipeline(monkeypatch, [], severity)
    result = triage.triage_ticket("Reset issue", "Please help.")
    classifier.assert_called_once_with("classifier", "Reset issue\n\nPlease help.", "")
    responder.assert_not_called()
    assert result["decision"] == "ESCALATE"
    assert result["can_auto_reply"] is False
    assert result["response"] == ""
    assert result["retrieved_sources"] == []
    expected = severity if severity in {"SEV1", "SEV2", "SEV3"} else "SEV3"
    assert result["urgency"] == expected
    assert result["sla"] == SLA_MAP[expected]
    assert "No FAQ documents passed" in result["reason"]


def test_supported_ticket_can_still_receive_grounded_reply(monkeypatch):
    documents = [Document(page_content="Request a new reset link.", metadata={"source": "password_reset.md"})]
    classifier, responder = configure_pipeline(monkeypatch, documents)
    result = triage.triage_ticket("Password reset issue", "My link expired.")
    assert result["decision"] == "AUTO_REPLY"
    assert result["response"] == "Request a new reset link."
    assert result["retrieved_sources"] == ["password_reset.md"]
    assert classifier.call_args.args[2] == documents[0].page_content
    assert responder.call_args.args[2] == documents[0].page_content


def test_retrieved_document_does_not_override_unanswerable_assessment(monkeypatch):
    documents = [Document(page_content="Generic instructions")]
    _, responder = configure_pipeline(monkeypatch, documents, answerable=False)
    result = triage.triage_ticket("Reset issue", "I already tried the instructions.")
    assert result["decision"] == "ESCALATE"
    responder.assert_not_called()
