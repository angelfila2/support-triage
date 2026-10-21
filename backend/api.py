"""Support ticket API backed by Python's built-in sqlite3 module."""

from contextlib import asynccontextmanager, suppress, closing
import asyncio
import json
import logging
import sqlite3
from typing import Literal

from backend.agent.classifier import VALID_CATEGORIES
from backend.auth import authorize
from fastapi import FastAPI, HTTPException, status, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.config import CORS_ORIGINS, OUTPUT_DIR, TICKETS_FILE, TRIAGE_TIMEOUT_SECONDS, OLLAMA_MODEL
from backend import audit, jobs
from backend.storage import db_connection, init_database, utc_now
from backend.agent.triage import triage_ticket
from backend.agent.runtime import runner, TriageBusy, TriageTimeout

DB_PATH = OUTPUT_DIR / "supportflow.db"
SLA_MAP = {
    "SEV1": "4 hours", "SEV2": "1 day", "SEV3": "3 days",
    "SEV4": "4 days", "SEV5": "5 days",
}


def get_db(*, write=False):
    return db_connection(DB_PATH, write=write)


def init_db():
    return init_database(DB_PATH, TICKETS_FILE)


@asynccontextmanager
async def lifespan(app):
    # Import errors stop startup instead of silently accepting partial history.
    init_db()
    jobs.recover_expired(DB_PATH)

    async def recover_loop():
        while True:
            await asyncio.sleep(15)
            try:
                await asyncio.to_thread(jobs.recover_expired, DB_PATH)
            except sqlite3.Error:
                logging.getLogger(__name__).warning("Ticket recovery will retry after a database error.")

    recovery = asyncio.create_task(recover_loop())
    try:
        yield
    finally:
        recovery.cancel()
        with suppress(asyncio.CancelledError):
            await recovery


app = FastAPI(
    title="Support Ticket Triage API",
    description="API for classifying, routing, storing and reviewing support tickets.",
    version="1.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TicketRequest(BaseModel):
    model_config = ConfigDict(
        strict=True,
        str_strip_whitespace=True,
    )

    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=20000)


HelpdeskStatus = Literal["open", "responded_waiting_info", "responded_awaiting_confirmation", "responded_closed"]
HELPDESK_STATUS_LABELS = {
    "open": "Open",
    "responded_waiting_info": "Responded (waiting for user info)",
    "responded_awaiting_confirmation": "Responded (awaiting user confirmation)",
    "responded_closed": "Responded (closed)",
}


class TicketStatusRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)
    helpdesk_status: HelpdeskStatus
    response_notes: str = Field(min_length=1, max_length=5000)
    urgency: Literal["SEV1", "SEV2", "SEV3", "SEV4", "SEV5"] | None = None


class TicketResponseRequest(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)
    responded: bool
    urgency: Literal["SEV1", "SEV2", "SEV3", "SEV4", "SEV5"]
    response_notes: str = Field(min_length=1, max_length=5000)
    helpdesk_status: HelpdeskStatus | None = None


def format_ticket(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["id"] = str(data["id"])
    data["is_suspicious"] = bool(data["is_suspicious"])
    data["responded"] = bool(data["responded"])

    if data["analysis_correct"] is not None:
        data["analysis_correct"] = bool(data["analysis_correct"])

    return data


class TicketReviewRequest(BaseModel):
    model_config = ConfigDict(
        strict=True,
        str_strip_whitespace=True,
    )

    analysis_correct: bool
    corrected_category: str | None = None
    review_notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_review(self):
        if (
            self.corrected_category is not None
            and self.corrected_category not in VALID_CATEGORIES
        ):
            raise ValueError(
                "corrected_category must be one of: "
                + ", ".join(sorted(VALID_CATEGORIES))
            )

        if not self.analysis_correct and self.corrected_category is None:
            raise ValueError(
                "corrected_category is required when analysis is marked incorrect."
            )

        if self.analysis_correct:
            self.corrected_category = None

        return self


@app.get("/")
def root():
    return {
        "message": "Support Ticket Triage API is running",
        "database": "SQLite",
        "status": "alive",
    }

def process_claim(row, attempt_id):
    ticket_id = row["id"]
    metadata = audit.provenance()
    jobs.record_metadata(DB_PATH, attempt_id, metadata)
    try:
        result = runner.run(triage_ticket, row["subject"], row["body"])
    except Exception as error:
        try:
            jobs.finish(DB_PATH, ticket_id, attempt_id,
                        error="AI processing failed. Please retry later.", metadata=metadata)
        except jobs.ClaimConflict:
            pass
        raise HTTPException(
            status_code=504 if isinstance(error, TriageTimeout) else 503,
            detail={"message": "Ticket saved, but AI processing failed.",
                    "ticket_id": str(ticket_id), "processing_status": "failed"},
        ) from error
    result = dict(result)
    evidence = result.pop("_evidence", None)
    if evidence is None:
        evidence = audit.evidence_snapshot(result.get("retrieved_sources", []))
    try:
        jobs.finish(DB_PATH, ticket_id, attempt_id, result=result, metadata=metadata, evidence=evidence)
    except jobs.ClaimConflict as error:
        raise HTTPException(409, "Attempt expired or was superseded; refresh the ticket.") from error
    return ticket_details(str(ticket_id))


@app.post("/api/triage", status_code=201, dependencies=[Depends(authorize)])
def triage(request: TicketRequest):
    row, attempt_id = jobs.claim(DB_PATH, TRIAGE_TIMEOUT_SECONDS, subject=request.subject, body=request.body)
    return process_claim(row, attempt_id)


@app.post("/api/tickets/{ticket_id}/retry", dependencies=[Depends(authorize)])
def retry_ticket(ticket_id: str):
    try:
        row, attempt_id = jobs.claim(DB_PATH, TRIAGE_TIMEOUT_SECONDS, ticket_id=ticket_id)
    except LookupError as error:
        raise HTTPException(404, "Ticket not found.") from error
    except jobs.ClaimConflict as error:
        raise HTTPException(409, str(error)) from error
    return process_claim(row, attempt_id)


@app.get("/api/tickets", dependencies=[Depends(authorize)])
def get_all_tickets(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str = Query(default="", max_length=200),
    category: str | None = None,
    urgency: Literal["SEV1", "SEV2", "SEV3", "SEV4", "SEV5"] | None = None,
    processing_status: Literal["pending", "processing", "completed", "failed"] | None = None,
    review: Literal["pending", "correct", "incorrect"] | None = None,
):
    clauses, params = [], []
    for field, value in (("category", category), ("urgency", urgency), ("processing_status", processing_status)):
        if value is not None:
            if field == "category" and value not in VALID_CATEGORIES:
                raise HTTPException(422, "Unknown category.")
            clauses.append(field + " = ?")
            params.append(value)
    if q.strip():
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(subject LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\' OR CAST(id AS TEXT) LIKE ? ESCAPE '\\')")
        params.extend(["%" + escaped + "%"] * 3)
    if review is not None:
        clauses.append({"pending": "analysis_correct IS NULL", "correct": "analysis_correct = 1", "incorrect": "analysis_correct = 0"}[review])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with get_db() as connection:
        counts = connection.execute("SELECT COUNT(*) AS total, COALESCE(SUM(analysis_correct IS NOT NULL),0) AS reviewed, COALESCE(SUM(analysis_correct=1),0) AS correct, COALESCE(SUM(analysis_correct IS NULL),0) AS pending FROM tickets" + where, params).fetchone()
        rows = connection.execute("SELECT * FROM tickets" + where + " ORDER BY id DESC LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
        return {"items": [format_ticket(row) for row in rows], "total": counts["total"],
                "limit": limit, "offset": offset, "summary": dict(counts)}


@app.get("/api/analytics", dependencies=[Depends(authorize)])
def analytics():
    with get_db() as connection:
        counts = connection.execute("""SELECT COUNT(*) AS total,
            COALESCE(SUM(processing_status='completed'),0) AS completed,
            COALESCE(SUM(processing_status='completed' AND decision='AUTO_REPLY'),0) AS auto_replies,
            COALESCE(SUM(processing_status='completed' AND decision='ESCALATE'),0) AS escalations,
            COALESCE(AVG(CASE WHEN processing_status='completed' THEN confidence END),0) AS average_confidence
            FROM tickets""").fetchone()
        categories = connection.execute("SELECT category,COUNT(*) AS count FROM tickets WHERE processing_status='completed' GROUP BY category").fetchall()
        recent = connection.execute("SELECT * FROM tickets WHERE processing_status='completed' ORDER BY id DESC LIMIT 10").fetchall()
        return {**dict(counts), "categories": {row["category"] or "unknown": row["count"] for row in categories},
                "recent": [format_ticket(row) for row in recent]}


@app.get("/health/live")
def live():
    return {"status": "alive"}


@app.get("/health/ready")
def ready():
    database_ok = False
    try:
        with closing(sqlite3.connect("file:" + DB_PATH.resolve().as_posix() + "?mode=ro", uri=True, timeout=1)) as connection:
            connection.execute("SELECT 1 FROM tickets LIMIT 1").fetchone()
            connection.execute("SELECT 1 FROM ticket_attempts LIMIT 1").fetchone()
            database_ok = True
    except sqlite3.Error:
        pass
    try:
        names = {row["name"] for row in audit.ollama_models()}
        ollama_ok = True
    except (OSError, ValueError, KeyError):
        names, ollama_ok = set(), False
    models = {name: (name if ":" in name else name + ":latest") in names for name in (OLLAMA_MODEL, "mxbai-embed-large")}
    healthy = database_ok and ollama_ok and all(models.values())
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=200 if healthy else 503, content={"status": "ready" if healthy else "not_ready", "database": database_ok, "ollama": ollama_ok, "models": models})


def ticket_details(ticket_id):
    with get_db() as connection:
        row = connection.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Ticket not found.")
        attempts = connection.execute("SELECT * FROM ticket_attempts WHERE ticket_id=? ORDER BY started_at DESC,rowid DESC LIMIT 1", (ticket_id,)).fetchall()
        data = format_ticket(row)
        if attempts:
            latest = attempts[0]
            result = json.loads(latest["result_json"])
            data.update({key: value for key, value in result.items() if key not in data and not key.startswith("_")})
            data["retrieved_sources"] = [item["source"] for item in json.loads(latest["evidence_json"])]
            data["provenance"] = json.loads(latest["provenance_json"])
        data["attempt_count"] = connection.execute("SELECT COUNT(*) FROM ticket_attempts WHERE ticket_id=?", (ticket_id,)).fetchone()[0]
        return data


@app.get("/api/tickets/{ticket_id}/timeline", dependencies=[Depends(authorize)])
def ticket_timeline(ticket_id: str):
    with get_db() as connection:
        ticket = connection.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if ticket is None:
            raise HTTPException(404, "Ticket not found.")
        events = [{"id": "created", "occurred_at": ticket["created_at"],
                   "title": "Ticket created", "description": "Request received and saved."}]
        for attempt in connection.execute("SELECT * FROM ticket_attempts WHERE ticket_id=? ORDER BY started_at,rowid", (ticket_id,)):
            events.append({"id": f"{attempt['id']}-start", "occurred_at": attempt["started_at"],
                           "title": "AI triage started", "description": "Ticket assessment began."})
            if attempt["completed_at"]:
                result = json.loads(attempt["result_json"])
                events.append({"id": f"{attempt['id']}-end", "occurred_at": attempt["completed_at"],
                               "title": "AI triage completed" if attempt["status"] == "completed" else "AI triage failed",
                               "description": ("Escalated to a human." if result.get("decision") == "ESCALATE" else "Assessment saved.") if attempt["status"] == "completed" else (attempt["error"] or "Processing did not complete.")})
        saved = [dict(row) for row in connection.execute(
            "SELECT id,occurred_at,title,description FROM ticket_events WHERE ticket_id=? ORDER BY id", (ticket_id,))]
        events.extend({**event, "id": f"event-{event['id']}"} for event in saved)
        if ticket["response_datetime"] and not any(event["title"] in ("Response recorded", "Response updated") for event in saved):
            events.append({"id": "legacy-response", "occurred_at": ticket["response_datetime"],
                           "title": "Response recorded", "description": "Helpdesk response saved."})
        events.sort(key=lambda event: event["occurred_at"])
        if ticket["analysis_correct"] is not None and not any(event["title"].startswith("Review") for event in saved):
            events.append({"id": "legacy-review", "occurred_at": None, "title": "Review recorded",
                           "description": "Approved." if ticket["analysis_correct"] else "Classification corrected."})
        return events


@app.get("/api/tickets/{ticket_id}/attempts", dependencies=[Depends(authorize)])
def attempts(ticket_id: str, limit: int = Query(default=20, ge=1, le=100)):
    with get_db() as connection:
        if not connection.execute("SELECT 1 FROM tickets WHERE id=?", (ticket_id,)).fetchone():
            raise HTTPException(404, "Ticket not found.")
        rows = connection.execute("SELECT * FROM ticket_attempts WHERE ticket_id=? ORDER BY started_at DESC,rowid DESC LIMIT ?", (ticket_id, limit)).fetchall()
        return [{**{key: row[key] for key in ("id", "started_at", "completed_at", "status", "error")},
                 "provenance": json.loads(row["provenance_json"]), "evidence": json.loads(row["evidence_json"]), "result": json.loads(row["result_json"])} for row in rows]


@app.get("/api/tickets/{ticket_id}", dependencies=[Depends(authorize)])
def get_single_ticket(ticket_id: str):
    return ticket_details(ticket_id)


@app.patch("/api/tickets/{ticket_id}/review", dependencies=[Depends(authorize)])
def review_ticket(ticket_id: str, review: TicketReviewRequest):
    if not review.analysis_correct and not review.corrected_category:
        raise HTTPException(
            400, "corrected_category is required when analysis is marked incorrect."
        )
    with get_db(write=True) as connection:
        cursor = connection.execute(
            """UPDATE tickets
               SET analysis_correct = ?, corrected_category = ?, review_notes = ?
               WHERE id = ?""",
            (
                int(review.analysis_correct),
                "" if review.analysis_correct else review.corrected_category,
                review.review_notes or "", ticket_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, f"Ticket {ticket_id} was not found.")
        connection.execute("INSERT INTO ticket_events(ticket_id,occurred_at,title,description) VALUES (?,?,?,?)",
                           (ticket_id, utc_now(), "Review saved", "AI classification approved." if review.analysis_correct else f"Category corrected to {review.corrected_category.replace('_', ' ')}."))
    return ticket_details(ticket_id)


def save_helpdesk_update(ticket_id, helpdesk_status, notes, urgency=None):
    """Save the status, required note and activity entry in one transaction."""
    with get_db(write=True) as connection:
        previous = connection.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if previous is None:
            raise HTTPException(404, "Ticket not found.")
        current = helpdesk_status or (
            previous["helpdesk_status"] if previous["helpdesk_status"] != "open"
            else "responded_awaiting_confirmation"
        )
        marks_response = current != "open"
        now = utc_now()
        connection.execute("""UPDATE tickets SET helpdesk_status=?, response_notes=?, responded=?,
                           response_datetime=?, urgency=?, sla=? WHERE id=?""",
                           (current, notes, int(bool(previous["responded"]) or marks_response),
                            previous["response_datetime"] or (now if marks_response else None),
                            urgency or previous["urgency"], SLA_MAP[urgency] if urgency else previous["sla"], ticket_id))
        if marks_response and not previous["responded"]:
            connection.execute("INSERT INTO ticket_events(ticket_id,occurred_at,title,description) VALUES (?,?,?,?)",
                               (ticket_id, now, "Response recorded", "Helpdesk marked its reply as sent."))
        title = "Helpdesk status changed" if previous["helpdesk_status"] != current else "Helpdesk update"
        description = f"{HELPDESK_STATUS_LABELS[previous['helpdesk_status']]} → {HELPDESK_STATUS_LABELS[current]}" if previous["helpdesk_status"] != current else HELPDESK_STATUS_LABELS[current]
        if urgency and urgency != previous["urgency"]:
            description += f"\nUrgency: {previous['urgency'] or 'Unassigned'} → {urgency}"
        connection.execute("INSERT INTO ticket_events(ticket_id,occurred_at,title,description) VALUES (?,?,?,?)",
                           (ticket_id, now, title, description + "\nNote: " + notes))
    return ticket_details(ticket_id)


@app.patch("/api/tickets/{ticket_id}/status", dependencies=[Depends(authorize)])
def change_ticket_status(ticket_id: str, update: TicketStatusRequest):
    return save_helpdesk_update(ticket_id, update.helpdesk_status, update.response_notes, update.urgency)


@app.patch("/api/tickets/{ticket_id}/respond", dependencies=[Depends(authorize)])
def respond_ticket(ticket_id: str, response: TicketResponseRequest):
    # Compatibility endpoint uses the same required-note update path.
    return save_helpdesk_update(ticket_id, response.helpdesk_status if response.responded else "open",
                               response.response_notes, response.urgency)
