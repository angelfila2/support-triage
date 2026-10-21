import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend import api, audit, jobs
from backend.storage import db_connection, init_database


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "tickets.db")
    monkeypatch.setattr(api, "TICKETS_FILE", tmp_path / "missing.csv")
    with TestClient(api.app) as client:
        yield client


def assessment():
    return {"category": "password_reset", "urgency": "SEV4", "confidence": 95,
            "decision": "AUTO_REPLY", "response": "Original FAQ passage", "sla": "4 days",
            "retrieved_sources": ["password_reset.md"], "is_suspicious": False, "reason": "FAQ match",
            "_evidence": [{"source": "password_reset.md", "content": "Frozen original FAQ", "sha256": "frozen-hash"}]}


def test_failed_ticket_retry_keeps_id_and_versioned_attempts(client, monkeypatch):
    monkeypatch.setattr(api, "triage_ticket", lambda *args: (_ for _ in ()).throw(RuntimeError("private error")))
    failed = client.post("/api/triage", json={"subject": "Password reset", "body": "Expired link"})
    ticket_id = failed.json()["detail"]["ticket_id"]
    monkeypatch.setattr(api, "triage_ticket", lambda *args: assessment())
    retried = client.post(f"/api/tickets/{ticket_id}/retry")
    assert retried.status_code == 200
    assert retried.json()["id"] == ticket_id
    assert retried.json()["attempt_count"] == 2
    assert client.get("/api/tickets").json()["total"] == 1
    assert client.post(f"/api/tickets/{ticket_id}/retry").status_code == 409
    history = client.get(f"/api/tickets/{ticket_id}/attempts").json()
    assert [row["status"] for row in history] == ["completed", "failed"]
    assert history[0]["evidence"][0]["content"] == "Frozen original FAQ"
    assert history[0]["provenance"]["code_sha256"]
    assert "private error" not in json.dumps(history)
    for endpoint, payload in (
        ("review", {"analysis_correct": True}),
        ("respond", {"responded": True, "urgency": "SEV4", "response_notes": "Resolved"}),
    ):
        updated = client.patch(f"/api/tickets/{ticket_id}/{endpoint}", json=payload)
        assert updated.status_code == 200
        assert updated.json()["attempt_count"] == 2
        assert updated.json()["provenance"]["code_sha256"]
        assert updated.json()["retrieved_sources"] == ["password_reset.md"]


def test_expired_attempt_recovery_rejects_late_result(tmp_path):
    db = tmp_path / "tickets.db"
    init_database(db)
    row, old_id = jobs.claim(db, 120, subject="Help", body="Text")
    with db_connection(db, write=True) as connection:
        connection.execute("UPDATE ticket_attempts SET lease_until='2000-01-01T00:00:00+00:00' WHERE id=?", (old_id,))
    assert jobs.recover_expired(db) == 1
    _, new_id = jobs.claim(db, 120, ticket_id=row["id"])
    with pytest.raises(jobs.ClaimConflict):
        jobs.finish(db, row["id"], old_id, result=assessment())
    jobs.finish(db, row["id"], new_id, result=assessment())
    with db_connection(db) as connection:
        assert connection.execute("SELECT processing_status FROM tickets").fetchone()[0] == "completed"


def test_concurrent_retry_claims_allow_only_one_attempt(tmp_path):
    db = tmp_path / "tickets.db"
    init_database(db)
    row, attempt = jobs.claim(db, 120, subject="Help", body="Text")
    jobs.finish(db, row["id"], attempt, error="Try again")
    def claim():
        try:
            jobs.claim(db, 120, ticket_id=row["id"])
            return True
        except jobs.ClaimConflict:
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(lambda _: claim(), range(4))) == 1


def test_recovery_preserves_live_leases_and_recovers_old_orphans(tmp_path):
    db = tmp_path / "tickets.db"
    init_database(db)
    active, _ = jobs.claim(db, 120, subject="Still running", body="Text")
    with db_connection(db, write=True) as connection:
        connection.execute("INSERT INTO tickets (created_at,subject,body,processing_status) VALUES ('2000-01-01T00:00:00+00:00','Interrupted','Text','processing')")
    assert jobs.recover_expired(db) == 1
    with db_connection(db) as connection:
        assert connection.execute("SELECT processing_status FROM tickets WHERE id=?", (active["id"],)).fetchone()[0] == "processing"
        assert connection.execute("SELECT processing_status FROM tickets WHERE subject='Interrupted'").fetchone()[0] == "failed"


def test_pages_filters_and_analytics_cover_whole_table(client):
    with db_connection(api.DB_PATH, write=True) as connection:
        for number in range(60):
            connection.execute("INSERT INTO tickets (created_at,subject,body,category,urgency,decision,confidence,processing_status) VALUES ('now',?,'body',?,'SEV4','AUTO_REPLY',90,'completed')", ("100% ready" if number == 0 else f"Ticket {number}", "password_reset" if number % 2 else "billing_question"))
    first = client.get("/api/tickets").json()
    second = client.get("/api/tickets?offset=25").json()
    assert len(first["items"]) == 25 and first["total"] == 60
    assert not {row["id"] for row in first["items"]} & {row["id"] for row in second["items"]}
    assert client.get("/api/tickets?category=billing_question&limit=100").json()["total"] == 30
    assert client.get("/api/tickets", params={"q": "%"}).json()["total"] == 1
    assert client.get("/api/tickets", params={"q": "' OR 1=1 --"}).json()["total"] == 0
    assert client.get("/api/tickets?limit=101").status_code == 422
    stats = client.get("/api/analytics").json()
    assert stats["total"] == 60 and stats["auto_replies"] == 60
    assert len(stats["recent"]) == 10
    assert stats["categories"]["billing_question"] == 30


def test_readiness_requires_models_but_liveness_does_not(client, monkeypatch):
    monkeypatch.setattr(audit, "ollama_models", lambda: [])
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503
    monkeypatch.setattr(audit, "ollama_models", lambda: [{"name": api.OLLAMA_MODEL if ":" in api.OLLAMA_MODEL else api.OLLAMA_MODEL + ":latest"}, {"name": "mxbai-embed-large:latest"}])
    assert client.get("/health/ready").status_code == 200


def test_timeline_preserves_each_review_and_response(client, monkeypatch):
    monkeypatch.setattr(api, "triage_ticket", lambda *args: assessment())
    ticket_id = client.post("/api/triage", json={"subject": "Password reset", "body": "Forgot password"}).json()["id"]
    endpoint = f"/api/tickets/{ticket_id}"
    assert client.patch(endpoint + "/review", json={"analysis_correct": True}).status_code == 200
    assert client.patch(endpoint + "/review", json={"analysis_correct": False, "corrected_category": "other"}).status_code == 200
    for urgency in ("SEV4", "SEV3"):
        assert client.patch(endpoint + "/respond", json={"responded": True, "urgency": urgency, "response_notes": f"Reply recorded with urgency {urgency}"}).status_code == 200
    events = client.get(endpoint + "/timeline").json()
    assert [event["title"] for event in events] == [
        "Ticket created", "AI triage started", "AI triage completed", "Review saved", "Review saved", "Response recorded", "Helpdesk status changed", "Helpdesk update"]
    assert all(event["occurred_at"] for event in events)
    assert len({event["id"] for event in events}) == len(events)
    assert "SEV3" in events[-1]["description"]
    assert client.get("/api/tickets/999999/timeline").status_code == 404


def test_old_review_does_not_get_an_invented_timestamp(client):
    with api.get_db(write=True) as connection:
        connection.execute("INSERT INTO tickets(created_at,subject,body,analysis_correct) VALUES (?,?,?,?)",
                           ("2026-10-20T00:00:00+00:00", "Old ticket", "Help", 1))
    events = client.get("/api/tickets/1/timeline").json()
    assert events[-1]["title"] == "Review recorded"
    assert events[-1]["occurred_at"] is None


def test_helpdesk_can_change_response_status_and_reopen_without_losing_history(client):
    with api.get_db(write=True) as connection:
        connection.execute("INSERT INTO tickets(created_at,subject,body) VALUES (?,?,?)",
                           ("2026-10-20T00:00:00+00:00", "Request", "Help"))
    endpoint = "/api/tickets/1/status"
    first = client.patch(endpoint, json={"helpdesk_status": "responded_waiting_info", "response_notes": "Asked the customer for details"})
    assert first.status_code == 200
    assert first.json()["responded"] is True
    timestamp = first.json()["response_datetime"]
    for status in ("responded_awaiting_confirmation", "responded_closed", "open", "responded_waiting_info"):
        saved = client.patch(endpoint, json={"helpdesk_status": status, "response_notes": f"Moving ticket to {status}"})
        assert saved.status_code == 200
        assert saved.json()["helpdesk_status"] == status
        assert saved.json()["responded"] is True
        assert saved.json()["response_datetime"] == timestamp
        assert saved.json()["urgency"] is None  # No AI triage or severity edits are required.
    history = client.get("/api/tickets/1/timeline").json()
    assert sum(event["title"] == "Helpdesk status changed" for event in history) == 5
    assert sum(event["title"] == "Response recorded" for event in history) == 1
    assert client.patch(endpoint, json={"helpdesk_status": "responded_waiting_info", "response_notes": "Asked the customer for details"}).status_code == 200
    assert len(client.get("/api/tickets/1/timeline").json()) == len(history) + 1


def test_helpdesk_status_rejects_invalid_values_and_missing_tickets(client):
    assert client.patch("/api/tickets/999/status", json={"helpdesk_status": "responded_closed", "response_notes": "Resolved"}).status_code == 404
    for payload in ({"helpdesk_status": "sent"}, {"helpdesk_status": None}, {"helpdesk_status": 1}, {},
                    {"helpdesk_status": "open", "responded": True}):
        assert client.patch("/api/tickets/999/status", json=payload).status_code == 422


def test_existing_database_receives_status_field_without_losing_tickets(tmp_path):
    db = tmp_path / "legacy.db"
    init_database(db)
    with db_connection(db, write=True) as connection:
        connection.execute("ALTER TABLE tickets DROP COLUMN helpdesk_status")
        connection.execute("INSERT INTO tickets(created_at,subject,body,responded,response_datetime) VALUES (?,?,?,?,?)",
                           ("2026-10-20T00:00:00+00:00", "Existing", "Keep this", 1, "2026-10-21T00:00:00+00:00"))
    init_database(db)
    init_database(db)
    with db_connection(db) as connection:
        saved = connection.execute("SELECT * FROM tickets").fetchone()
        assert saved["body"] == "Keep this"
        assert saved["helpdesk_status"] == "responded_awaiting_confirmation"
        assert saved["response_datetime"] == "2026-10-21T00:00:00+00:00"


def test_new_ticket_stays_open_after_ai_triage(client, monkeypatch):
    monkeypatch.setattr(api, "triage_ticket", lambda *args: assessment())
    created = client.post("/api/triage", json={"subject": "Reset password", "body": "Forgot password"})
    assert created.status_code == 201
    ticket = created.json()
    assert ticket["processing_status"] == "completed"
    assert ticket["helpdesk_status"] == "open"
    assert ticket["responded"] is False
    saved = client.get(f"/api/tickets/{ticket['id']}").json()
    assert saved["helpdesk_status"] == "open"


@pytest.mark.parametrize("notes", [None, "", "   ", "\n\t", 123, "x" * 5001])
def test_helpdesk_updates_require_a_nonempty_note_and_leave_data_unchanged(client, notes):
    with api.get_db(write=True) as connection:
        connection.execute("INSERT INTO tickets(created_at,subject,body) VALUES (?,?,?)",
                           ("2026-10-20T00:00:00+00:00", "Request", "Help"))
    for endpoint, payload in (
        ("status", {"helpdesk_status": "responded_closed", "response_notes": notes}),
        ("respond", {"responded": True, "urgency": "SEV3", "response_notes": notes}),
    ):
        assert client.patch(f"/api/tickets/1/{endpoint}", json=payload).status_code == 422
    saved = client.get("/api/tickets/1").json()
    assert saved["helpdesk_status"] == "open"
    assert saved["responded"] is False
    assert saved["response_notes"] is None
    assert len(client.get("/api/tickets/1/timeline").json()) == 1


def test_helpdesk_note_status_and_urgency_are_saved_together(client):
    with api.get_db(write=True) as connection:
        connection.execute("INSERT INTO tickets(created_at,subject,body,urgency,sla) VALUES (?,?,?,?,?)",
                           ("2026-10-20T00:00:00+00:00", "Request", "Help", "SEV4", "4 days"))
    saved = client.patch("/api/tickets/1/status", json={"helpdesk_status": "responded_waiting_info",
                         "response_notes": "  Requested diagnostic logs.  ", "urgency": "SEV2"})
    assert saved.status_code == 200
    assert saved.json()["helpdesk_status"] == "responded_waiting_info"
    assert saved.json()["response_notes"] == "Requested diagnostic logs."
    assert saved.json()["urgency"] == "SEV2"
    assert saved.json()["sla"] == "1 day"
    history = client.get("/api/tickets/1/timeline").json()
    assert "Note: Requested diagnostic logs." in history[-1]["description"]
    assert "SEV4 → SEV2" in history[-1]["description"]
    client.patch("/api/tickets/1/status", json={"helpdesk_status": "responded_closed", "response_notes": "Customer confirmed the fix."})
    history = client.get("/api/tickets/1/timeline").json()
    assert any("Requested diagnostic logs." in event["description"] for event in history)
    assert "Customer confirmed the fix." in history[-1]["description"]
