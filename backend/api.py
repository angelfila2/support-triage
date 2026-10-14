import csv
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import BASE_DIR, CORS_ORIGINS, OUTPUT_DIR, TICKETS_FILE
from triage import triage_ticket

# =========================================================
# DATABASE CONFIGURATION & SCHEMA
# =========================================================

DB_PATH = OUTPUT_DIR / "supportflow.db"

SLA_MAP = {
    "SEV1": "4 hours",
    "SEV2": "1 day",
    "SEV3": "3 days",
    "SEV4": "4 days",
    "SEV5": "5 days",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the SQLite schema and migrates existing CSV data if present."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                category TEXT,
                urgency TEXT,
                confidence INTEGER,
                decision TEXT,
                is_suspicious INTEGER DEFAULT 0,
                reason TEXT,
                response TEXT,
                sla TEXT,
                analysis_correct INTEGER,
                corrected_category TEXT,
                review_notes TEXT,
                responded INTEGER DEFAULT 0,
                response_datetime TEXT,
                response_notes TEXT
            )
            """
        )

        # Migrate existing CSV tickets if database is empty
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets")
        count = cursor.fetchone()[0]

        if count == 0 and TICKETS_FILE.exists():
            _migrate_csv_to_sqlite(conn)


def _migrate_csv_to_sqlite(conn):
    """Imports historical tickets from tickets_processed.csv into SQLite."""
    try:
        with open(TICKETS_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                analysis_correct = None
                raw_ac = str(row.get("analysis_correct", "")).strip().lower()
                if raw_ac in {"true", "1", "yes"}:
                    analysis_correct = 1
                elif raw_ac in {"false", "0", "no"}:
                    analysis_correct = 0

                is_suspicious = 1 if str(row.get("is_suspicious", "")).lower() in {"true", "1"} else 0
                responded = 1 if str(row.get("responded", "")).lower() in {"true", "1"} else 0

                conn.execute(
                    """
                    INSERT INTO tickets (
                        created_at, subject, body, category, urgency, confidence,
                        decision, is_suspicious, reason, response, sla,
                        analysis_correct, corrected_category, review_notes,
                        responded, response_datetime, response_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("created_at") or datetime.now().isoformat(timespec="seconds"),
                        row.get("subject", ""),
                        row.get("body", ""),
                        row.get("category"),
                        row.get("urgency"),
                        int(row["confidence"]) if row.get("confidence") and row["confidence"].isdigit() else 50,
                        row.get("decision"),
                        is_suspicious,
                        row.get("reason"),
                        row.get("response"),
                        row.get("sla"),
                        analysis_correct,
                        row.get("corrected_category") or None,
                        row.get("review_notes") or None,
                        responded,
                        row.get("response_datetime") or None,
                        row.get("response_notes") or None,
                    ),
                )
    except Exception as error:
        print(f"Notice: CSV migration skipped: {error}")


def format_ticket(row: sqlite3.Row) -> dict:
    """Converts SQLite row to API-compatible dictionary."""
    d = dict(row)
    d["id"] = str(d["id"])
    d["is_suspicious"] = bool(d["is_suspicious"])
    d["responded"] = bool(d["responded"])
    if d["analysis_correct"] is not None:
        d["analysis_correct"] = bool(d["analysis_correct"])
    return d


# =========================================================
# CREATE FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Support Ticket Triage API",
    description="API for classifying, routing, storing and reviewing support tickets.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

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


# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/")
def root():
    return {"message": "Support Ticket Triage API is running", "database": "SQLite", "status": "healthy"}


@app.post("/api/triage", status_code=status.HTTP_201_CREATED)
def triage(request: TicketRequest):
    """Executes the 6-stage triage pipeline and persists the record to SQLite."""
    try:
        result = triage_ticket(request.subject, request.body)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Triage engine failure (verify Ollama is running): {str(error)}",
        )

    now = datetime.now().isoformat(timespec="seconds")

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tickets (
                created_at, subject, body, category, urgency, confidence,
                decision, is_suspicious, reason, response, sla, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                now,
                request.subject,
                request.body,
                result.get("category"),
                result.get("urgency"),
                result.get("confidence"),
                result.get("decision"),
                1 if result.get("is_suspicious") else 0,
                result.get("reason"),
                result.get("response", ""),
                result.get("sla"),
            ),
        )
        ticket_id = str(cursor.lastrowid)

    return {
        **result,
        "id": ticket_id,
        "created_at": now,
    }


@app.get("/api/tickets")
def get_all_tickets():
    """Retrieves all triaged tickets ordered by newest first."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()
        return [format_ticket(row) for row in rows]


@app.get("/api/tickets/{ticket_id}")
def get_single_ticket(ticket_id: str):
    """Retrieves a single ticket by its ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} was not found.",
            )
        return format_ticket(row)


@app.patch("/api/tickets/{ticket_id}/review")
def review_ticket(ticket_id: str, review: TicketReviewRequest):
    """Saves human QA review feedback for a ticket."""
    if review.analysis_correct is False and not review.corrected_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="corrected_category is required when analysis is marked incorrect.",
        )

    corrected = "" if review.analysis_correct else (review.corrected_category or "")
    notes = review.review_notes or ""
    analysis_val = 1 if review.analysis_correct else 0

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE tickets
            SET analysis_correct = ?, corrected_category = ?, review_notes = ?
            WHERE id = ?
            """,
            (analysis_val, corrected, notes, ticket_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} was not found.",
            )

        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return format_ticket(row)


@app.patch("/api/tickets/{ticket_id}/respond")
def respond_ticket(ticket_id: str, response: TicketResponseRequest):
    """Updates severity, agent notes, and marks ticket as responded."""
    if response.urgency not in SLA_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid urgency '{response.urgency}'. Must be one of {list(SLA_MAP.keys())}",
        )

    sla = SLA_MAP[response.urgency]
    now = datetime.now().isoformat(timespec="seconds")
    responded_val = 1 if response.responded else 0
    notes = response.response_notes or ""

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE tickets
            SET urgency = ?, sla = ?, responded = ?, response_datetime = ?, response_notes = ?
            WHERE id = ?
            """,
            (response.urgency, sla, responded_val, now, notes, ticket_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} was not found.",
            )

        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return format_ticket(row)


# =========================================================
# INITIALIZE DATABASE ON IMPORT
# =========================================================

init_db()