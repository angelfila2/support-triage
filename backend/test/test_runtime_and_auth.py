from threading import Event
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from backend import api, auth
from backend.agent.runtime import InferenceRunner, TriageBusy, TriageTimeout


def test_deadline_keeps_slot_until_actual_completion():
    runner = InferenceRunner(workers=1, timeout=0.02)
    release = Event()
    done = Event()

    def blocked():
        try:
            release.wait(2)
        finally:
            done.set()

    try:
        with pytest.raises(TriageTimeout):
            runner.run(blocked)
        with pytest.raises(TriageBusy):
            runner.run(lambda: None)
    finally:
        release.set()
        runner.executor.shutdown(wait=True)
    assert done.is_set()


def test_timeout_is_saved_and_late_result_cannot_complete_ticket(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "tickets.db")
    monkeypatch.setattr(api, "TICKETS_FILE", tmp_path / "missing.csv")
    fake = Mock()
    fake.run.side_effect = TriageTimeout("private trace")
    monkeypatch.setattr(api, "runner", fake)
    with TestClient(api.app) as client:
        response = client.post("/api/triage", json={"subject": "Help", "body": "text"})
        assert response.status_code == 504
        row = client.get("/api/tickets/" + response.json()["detail"]["ticket_id"]).json()
    assert row["processing_status"] == "failed"
    assert row["decision"] is None


def test_read_and_write_credentials_are_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "AUTH_REQUIRED", True)
    monkeypatch.setenv("API_WRITE_TOKEN", "w" * 40)
    monkeypatch.setenv("API_READ_TOKEN", "r" * 40)
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "tickets.db")
    monkeypatch.setattr(api, "TICKETS_FILE", tmp_path / "missing.csv")
    with TestClient(api.app) as client:
        assert client.get("/api/tickets").status_code == 401
        assert client.get("/api/tickets", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.get("/api/tickets", headers={"Authorization": "Bearer " + "r" * 40}).status_code == 200
        assert client.post("/api/triage", headers={"Authorization": "Bearer " + "r" * 40},
                           json={"subject": "Help", "body": "text"}).status_code == 403
        assert client.post("/api/tickets/1/retry", headers={"Authorization": "Bearer " + "r" * 40}).status_code == 403
        assert client.get("/api/tickets", headers={"Authorization": "Bearer " + "w" * 40}).status_code == 200


@pytest.mark.parametrize("payload", [
    {"responded": "true", "urgency": "SEV3"},
    {"responded": True, "urgency": "invalid"},
    {"responded": True, "urgency": "SEV3", "response_notes": "x" * 5001},
])
def test_response_update_rejects_invalid_input(payload):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        api.TicketResponseRequest.model_validate(payload)
