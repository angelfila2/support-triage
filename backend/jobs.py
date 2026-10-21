"""Atomic ticket claims, leased attempts and guarded finalization."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.storage import db_connection, utc_now


class ClaimConflict(ValueError):
    pass


def recover_expired(db_path):
    with db_connection(db_path, write=True) as connection:
        return _recover(connection)


def _recover(connection):
    now = utc_now()
    expired = connection.execute(
        "SELECT id,ticket_id FROM ticket_attempts WHERE status='processing' AND lease_until <= ?", (now,)
    ).fetchall()
    for row in expired:
        connection.execute("UPDATE ticket_attempts SET status='failed',completed_at=?,error='Processing interrupted; retry is available.' WHERE id=? AND status='processing'", (now, row["id"]))
        connection.execute("UPDATE tickets SET processing_status='failed',processing_error='Processing interrupted; retry is available.' WHERE id=? AND processing_status='processing'", (row["ticket_id"],))
    # Old processing rows without an attempt lease are recoverable too. Do not
    # touch recent intake rows or any ticket with an active lease.
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=180)).isoformat(timespec="seconds")
    orphans = connection.execute("""UPDATE tickets SET processing_status='failed',
        processing_error='Processing interrupted; retry is available.'
        WHERE processing_status='processing' AND datetime(created_at) < datetime(?)
        AND NOT EXISTS (SELECT 1 FROM ticket_attempts a WHERE a.ticket_id=tickets.id AND a.status='processing')""", (cutoff,)).rowcount
    return len(expired) + orphans


def claim(db_path, timeout, *, subject=None, body=None, ticket_id=None):
    with db_connection(db_path, write=True) as connection:
        _recover(connection)
        if ticket_id is None:
            cursor = connection.execute("INSERT INTO tickets (created_at,subject,body,processing_status) VALUES (?,?,?,'pending')", (utc_now(), subject, body))
            ticket_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if row is None:
            raise LookupError("Ticket not found.")
        if row["processing_status"] not in {"pending", "failed"}:
            raise ClaimConflict("Only pending or failed tickets can be retried.")
        attempt_id = uuid4().hex
        lease = (datetime.now(timezone.utc) + timedelta(seconds=timeout + 30)).isoformat(timespec="seconds")
        connection.execute("UPDATE tickets SET processing_status='processing',processing_error=NULL WHERE id=?", (ticket_id,))
        connection.execute("INSERT INTO ticket_attempts (id,ticket_id,started_at,lease_until,status) VALUES (?,?,?,?,'processing')", (attempt_id, ticket_id, utc_now(), lease))
        return dict(row), attempt_id


def finish(db_path, ticket_id, attempt_id, *, result=None, error=None, metadata=None, evidence=None):
    with db_connection(db_path, write=True) as connection:
        row = connection.execute("SELECT status,lease_until FROM ticket_attempts WHERE id=? AND ticket_id=?", (attempt_id, ticket_id)).fetchone()
        if row is None or row["status"] != "processing":
            raise ClaimConflict("Attempt is no longer active.")
        if row["lease_until"] <= utc_now():
            raise ClaimConflict("Attempt lease has expired.")
        status = "failed" if error else "completed"
        connection.execute("UPDATE ticket_attempts SET status=?,completed_at=?,error=?,provenance_json=?,evidence_json=?,result_json=? WHERE id=?", (
            status, utc_now(), error, json.dumps(metadata or {}), json.dumps(evidence or []), json.dumps(result or {}), attempt_id))
        if error:
            connection.execute("UPDATE tickets SET processing_status='failed',processing_error=? WHERE id=?", (error, ticket_id))
        else:
            connection.execute("""UPDATE tickets SET category=?,urgency=?,confidence=?,decision=?,is_suspicious=?,reason=?,response=?,sla=?,processing_status='completed',processing_error=NULL WHERE id=?""", (
                result.get("category"), result.get("urgency"), result.get("confidence"), result.get("decision"), int(bool(result.get("is_suspicious"))), result.get("reason"), result.get("response", ""), result.get("sla"), ticket_id))


def record_metadata(db_path, attempt_id, metadata):
    with db_connection(db_path, write=True) as connection:
        connection.execute("UPDATE ticket_attempts SET provenance_json=? WHERE id=? AND status='processing'", (json.dumps(metadata), attempt_id))
