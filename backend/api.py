"""Support ticket API backed by Python's built-in sqlite3 module."""

from contextlib import asynccontextmanager
import sqlite3

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import CORS_ORIGINS, OUTPUT_DIR, TICKETS_FILE
from storage import db_connection, init_database, utc_now
from triage import triage_ticket

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
    yield


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
    subject: str
    body: str


class TicketReviewRequest(BaseModel):
    analysis_correct: bool
    corrected_category: str | None = None
    review_notes: str | None = None


class TicketResponseRequest(BaseModel):
    responded: bool
    urgency: str
    response_notes: str | None = None


def format_ticket(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["id"] = str(data["id"])
    data["is_suspicious"] = bool(data["is_suspicious"])
    data["responded"] = bool(data["responded"])
    if data["analysis_correct"] is not None:
        data["analysis_correct"] = bool(data["analysis_correct"])
    return data


@app.get("/")
def root():
    return {
        "message": "Support Ticket Triage API is running",
        "database": "SQLite",
        "status": "healthy",
    }


@app.post("/api/triage", status_code=status.HTTP_201_CREATED)
def triage(request: TicketRequest):
    try:
        result = triage_ticket(request.subject, request.body)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Triage engine failure (verify Ollama is running): {error}",
        ) from error

    created_at = utc_now()
    with get_db(write=True) as connection:
        cursor = connection.execute(
            """INSERT INTO tickets (
                created_at, subject, body, category, urgency, confidence,
                decision, is_suspicious, reason, response, sla, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                created_at, request.subject, request.body,
                result.get("category"), result.get("urgency"),
                result.get("confidence"), result.get("decision"),
                int(bool(result.get("is_suspicious"))),
                result.get("reason"), result.get("response", ""), result.get("sla"),
            ),
        )
        ticket_id = str(cursor.lastrowid)
    return {**result, "id": ticket_id, "created_at": created_at}


@app.get("/api/tickets")
def get_all_tickets():
    with get_db() as connection:
        rows = connection.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()
        return [format_ticket(row) for row in rows]


@app.get("/api/tickets/{ticket_id}")
def get_single_ticket(ticket_id: str):
    with get_db() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, f"Ticket {ticket_id} was not found.")
        return format_ticket(row)


@app.patch("/api/tickets/{ticket_id}/review")
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
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return format_ticket(row)


@app.patch("/api/tickets/{ticket_id}/respond")
def respond_ticket(ticket_id: str, response: TicketResponseRequest):
    if response.urgency not in SLA_MAP:
        raise HTTPException(400, "Invalid urgency. Use SEV1, SEV2, SEV3, SEV4 or SEV5.")
    with get_db(write=True) as connection:
        cursor = connection.execute(
            """UPDATE tickets
               SET urgency = ?, sla = ?, responded = ?,
                   response_datetime = ?, response_notes = ?
               WHERE id = ?""",
            (
                response.urgency, SLA_MAP[response.urgency], int(response.responded),
                utc_now() if response.responded else None,
                response.response_notes or "", ticket_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, f"Ticket {ticket_id} was not found.")
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return format_ticket(row)
