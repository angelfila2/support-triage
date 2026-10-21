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
