"""SQLite connections and atomic, one-time historical CSV import."""

import csv
import logging
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
CSV_MIGRATION = "historical_tickets_csv_v1"

TICKET_COLUMNS = (
    "created_at", "subject", "body", "category", "urgency", "confidence",
    "decision", "is_suspicious", "reason", "response", "sla",
    "analysis_correct", "corrected_category", "review_notes", "responded",
    "response_datetime", "response_notes", "legacy_id",
)


class MigrationError(ValueError):
    """Historical data could not be imported safely."""


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def db_connection(db_path, *, write=False):
    """Close every connection; commit writes only after successful completion."""
    connection = sqlite3.connect(str(db_path), timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        if write:
            # Acquire the write lock before checking migration state or rows.
            connection.execute("BEGIN IMMEDIATE")
        yield connection
        if write:
            connection.commit()
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def _create_schema(connection):
    connection.execute("""
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
            response_notes TEXT,
            legacy_id TEXT,
            processing_status TEXT NOT NULL DEFAULT 'pending',
            processing_error TEXT,
            helpdesk_status TEXT NOT NULL DEFAULT 'open'
                CHECK(helpdesk_status IN ('open','responded_waiting_info','responded_awaiting_confirmation','responded_closed'))
        )
    """)
    # Existing installations already contain tickets: add the workflow field once.
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(tickets)")}
    if "helpdesk_status" not in columns:
        connection.execute("""ALTER TABLE tickets ADD COLUMN helpdesk_status TEXT NOT NULL DEFAULT 'open'
            CHECK(helpdesk_status IN ('open','responded_waiting_info','responded_awaiting_confirmation','responded_closed'))""")
        connection.execute("UPDATE tickets SET helpdesk_status='responded_awaiting_confirmation' WHERE responded=1")
    connection.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS tickets_legacy_id
        ON tickets (legacy_id)
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS ticket_attempts (
            id TEXT PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            started_at TEXT NOT NULL,
            lease_until TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL CHECK(status IN ('processing','completed','failed')),
            error TEXT,
            provenance_json TEXT NOT NULL DEFAULT '{}',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            result_json TEXT NOT NULL DEFAULT '{}'
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS ticket_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            occurred_at TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS events_ticket ON ticket_events(ticket_id,id)")
    connection.execute("CREATE INDEX IF NOT EXISTS attempts_ticket ON ticket_attempts(ticket_id,started_at)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS active_ticket_attempt ON ticket_attempts(ticket_id) WHERE status='processing'")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS app_migrations (
            name TEXT PRIMARY KEY,
            source_path TEXT NOT NULL,
            imported_count INTEGER NOT NULL,
            completed_at TEXT NOT NULL
        )
    """)


def _parse_boolean(value, *, nullable=False):
    value = (value or "").strip().lower()
    if not value:
        return None if nullable else 0
    if value in {"true", "1", "yes"}:
        return 1
    if value in {"false", "0", "no"}:
        return 0
    raise ValueError("invalid boolean")


def _parse_row(row):
    if None in row or any(value is None for value in row.values()):
        raise ValueError("row has the wrong number of fields")

    record = {column: row.get(column) or None for column in TICKET_COLUMNS}
    record["created_at"] = row.get("created_at") or utc_now()
    record["subject"] = row["subject"]
    record["body"] = row["body"]
    # Historical rows with predictions are completed; input-only fixtures are pending.
    record["processing_status"] = (
        "completed" if record["decision"] in {"AUTO_REPLY", "ESCALATE"} else "pending"
    )

    confidence = (row.get("confidence") or "").strip()
    record["confidence"] = int(confidence) if confidence else None
    if record["confidence"] is not None and not 0 <= record["confidence"] <= 100:
        raise ValueError("confidence must be between 0 and 100")

    for field in ("is_suspicious", "responded", "analysis_correct"):
        record[field] = _parse_boolean(
            row.get(field), nullable=field == "analysis_correct"
        )

    source_id = (row.get("id") or "").strip()
    ticket_id = (row.get("ticket_id") or "").strip()
    if source_id and ticket_id and source_id != ticket_id:
        raise ValueError("id and ticket_id disagree")
    source_id = source_id or ticket_id
    record["legacy_id"] = source_id or None

    if source_id and re.fullmatch(r"[0-9]+", source_id):
        numeric_id = int(source_id)
        if not 1 <= numeric_id <= 9223372036854775807:
            raise ValueError("numeric ID is outside the positive SQLite range")
        record["id"] = numeric_id

    return record


def _read_csv(csv_path):
    records = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise MigrationError("Historical CSV has duplicate column names.")
        if not {"subject", "body"}.issubset(headers):
            raise MigrationError("Historical CSV requires subject and body columns.")
        try:
            for row in reader:
                try:
                    records.append((reader.line_num, _parse_row(row)))
                except (ValueError, TypeError) as error:
                    raise MigrationError(
                        f"Invalid historical CSV record ending at line {reader.line_num}: {error}"
                    ) from error
        except csv.Error as error:
            raise MigrationError(
                f"Invalid CSV syntax near line {reader.line_num}."
            ) from error
    return records


def init_database(db_path, csv_path=None):
    """Create the initial schema and import an empty database exactly once.

    Return the number imported. Existing populated databases are preserved.
    Exceptions propagate so startup cannot silently accept a partial import.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with db_connection(db_path, write=True) as connection:
        _create_schema(connection)
        completed = connection.execute(
            "SELECT 1 FROM app_migrations WHERE name = ?", (CSV_MIGRATION,)
        ).fetchone()
        if completed or csv_path is None:
            return 0

        csv_path = Path(csv_path)
        if not csv_path.exists():
            return 0

        if connection.execute("SELECT 1 FROM tickets LIMIT 1").fetchone():
            logger.warning(
                "Historical CSV was not imported because tickets already exist. "
                "Reconcile historical data separately; existing records were preserved."
            )
            return 0

        records = _read_csv(csv_path)
        # Reserve numeric IDs before generating IDs for UUID or ID-less records.
        ordered = [item for item in records if "id" in item[1]]
        ordered += [item for item in records if "id" not in item[1]]

        for line_number, record in ordered:
            columns = list(record)
            placeholders = ", ".join("?" for _ in columns)
            try:
                connection.execute(
                    f"INSERT INTO tickets ({', '.join(columns)}) VALUES ({placeholders})",
                    [record[column] for column in columns],
                )
            except sqlite3.IntegrityError as error:
                raise MigrationError(
                    f"Historical CSV conflicts with ticket constraints at line {line_number}."
                ) from error

        connection.execute(
            """INSERT INTO app_migrations
               (name, source_path, imported_count, completed_at)
               VALUES (?, ?, ?, ?)""",
            (CSV_MIGRATION, str(csv_path.resolve()), len(records), utc_now()),
        )
        return len(records)
