"""Exercise the HTTP intake flow with SQLite and a controlled AI replacement."""

import pytest
from fastapi.testclient import TestClient

from backend import api
from backend.storage import db_connection


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "tickets.db")
    monkeypatch.setattr(api, "TICKETS_FILE", tmp_path / "absent.csv")
    with TestClient(api.app) as client:
        yield client


def assert_committed_before_ai(subject, body):
    # A separate write connection proves the first transaction has committed
    # and is not holding the database write lock across inference.
    with db_connection(api.DB_PATH, write=True) as connection:
        rows = connection.execute("SELECT * FROM tickets").fetchall()
        assert len(rows) == 1
        assert rows[0]["subject"] == subject
        assert rows[0]["body"] == body
        assert rows[0]["processing_status"] == "processing"
        assert rows[0]["decision"] is None


def test_ai_failure_preserves_input_and_returns_retrievable_id(client, monkeypatch):
    def fail(subject, body):
        assert_committed_before_ai(subject, body)
        raise RuntimeError("private backend details")

    monkeypatch.setattr(api, "triage_ticket", fail)
    response = client.post("/api/triage", json={"subject": "Help", "body": "Cannot log in"})
    assert response.status_code == 503
    detail = response.json()["detail"]
    saved = client.get(f"/api/tickets/{detail['ticket_id']}")
    assert saved.status_code == 200
    ticket = saved.json()
    assert ticket["subject"] == "Help"
    assert ticket["body"] == "Cannot log in"
    assert ticket["processing_status"] == "failed"
    assert ticket["processing_error"]
    assert ticket["decision"] is None
    assert "private backend details" not in response.text + saved.text
    assert len(client.get("/api/tickets").json()["items"]) == 1


def test_success_updates_original_ticket_without_duplicate(client, monkeypatch):
    result = dict(category="password_reset", urgency="SEV4", confidence=95,
                  decision="AUTO_REPLY", is_suspicious=False, reason="FAQ match",
                  response="Request a new reset link.", sla="4 days")

    def succeed(subject, body):
        assert_committed_before_ai(subject, body)
        return result

    monkeypatch.setattr(api, "triage_ticket", succeed)
    response = client.post("/api/triage", json={"subject": "Reset", "body": "Expired link"})
    assert response.status_code == 201
    ticket = client.get(f"/api/tickets/{response.json()['id']}").json()
    assert ticket["processing_status"] == "completed"
    assert ticket["processing_error"] is None
    for key, value in result.items():
        assert ticket[key] == value
    assert len(client.get("/api/tickets").json()["items"]) == 1


def test_invalid_input_never_runs_ai_or_inserts_ticket(client, monkeypatch):
    def unexpected(*args):
        pytest.fail("Invalid input must not run inference")

    monkeypatch.setattr(api, "triage_ticket", unexpected)
    assert client.post("/api/triage", json={"subject": " ", "body": "text"}).status_code == 422
    assert client.get("/api/tickets").json()["items"] == []
