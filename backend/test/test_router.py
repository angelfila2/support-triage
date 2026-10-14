import sys
from pathlib import Path

# Ensure backend directory is in sys.path regardless of execution directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from router import route_ticket
except ImportError:
    from backend.router import route_ticket


def test_sev1_outage_always_escalates():
    """Critical SEV1 incidents must escalate even with high confidence and answerability."""
    classification = {
        "category": "login issues",
        "urgency": "SEV1",
        "confidence": 98,
        "can_auto_reply": True,
        "reason": "Production outage."
    }
    assert route_ticket(classification, is_suspicious=False) == "ESCALATE"


def test_sev2_breach_always_escalates():
    """High-severity SEV2 incidents must escalate even with high confidence."""
    classification = {
        "category": "billing_question",
        "urgency": "SEV2",
        "confidence": 95,
        "can_auto_reply": True,
        "reason": "Substantial duplicate billing impairment."
    }
    assert route_ticket(classification, is_suspicious=False) == "ESCALATE"


def test_sev4_routine_auto_reply():
    """Eligible routine SEV4 ticket with high confidence auto-replies."""
    classification = {
        "category": "password_reset",
        "urgency": "SEV4",
        "confidence": 92,
        "can_auto_reply": True,
        "reason": "Standard self-service password reset."
    }
    assert route_ticket(classification, is_suspicious=False) == "AUTO_REPLY"


def test_low_confidence_escalates():
    """Confidence below 80% must always escalate for human review."""
    classification = {
        "category": "password_reset",
        "urgency": "SEV4",
        "confidence": 75,
        "can_auto_reply": True,
        "reason": "Ambiguous password reset request."
    }
    assert route_ticket(classification, is_suspicious=False) == "ESCALATE"


def test_unanswerable_ticket_escalates():
    """Tickets that the FAQ cannot definitively answer must escalate."""
    classification = {
        "category": "billing_question",
        "urgency": "SEV4",
        "confidence": 95,
        "can_auto_reply": False,
        "reason": "Requires human account investigation."
    }
    assert route_ticket(classification, is_suspicious=False) == "ESCALATE"


def test_suspicious_ticket_escalates():
    """Adversarial prompt injection must always escalate immediately."""
    classification = {
        "category": "password_reset",
        "urgency": "SEV4",
        "confidence": 100,
        "can_auto_reply": True,
        "reason": "Password reset."
    }
    assert route_ticket(classification, is_suspicious=True) == "ESCALATE"