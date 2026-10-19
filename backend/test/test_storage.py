import csv
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from backend.storage import CSV_MIGRATION, MigrationError, db_connection, init_database


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["id", "subject", "body", "confidence"]
        )
        writer.writeheader()
        writer.writerows(rows)


def count_rows(db_path):
    with db_connection(db_path) as connection:
        return connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]


def test_preserves_numeric_ids_and_generates_ids_after_them(tmp_path):
    db = tmp_path / "tickets.db"
    source = tmp_path / "tickets.csv"
    write_csv(source, [
        dict(id="old-uuid", subject="UUID ticket", body="Body", confidence=90),
        dict(id="99", subject="Numeric ticket", body="Body", confidence=95),
    ])
    assert init_database(db, source) == 2
    with db_connection(db) as connection:
        rows = connection.execute("SELECT id, legacy_id FROM tickets ORDER BY id").fetchall()
    assert [(row["id"], row["legacy_id"]) for row in rows] == [
        (99, "99"), (100, "old-uuid")
    ]


def test_bad_row_leaves_no_partial_import_and_can_be_retried(tmp_path):
    db = tmp_path / "tickets.db"
    source = tmp_path / "tickets.csv"
    init_database(db)
    write_csv(source, [
        dict(id=1, subject="Valid", body="Body", confidence=95),
        dict(id=2, subject="Invalid", body="Body", confidence="broken"),
    ])
    with pytest.raises(MigrationError):
        init_database(db, source)
    assert count_rows(db) == 0
    with db_connection(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM app_migrations").fetchone()[0] == 0
    write_csv(source, [dict(id=1, subject="Fixed", body="Body", confidence=95)])
    assert init_database(db, source) == 1


def test_duplicate_id_rolls_back_inserts(tmp_path):
    db = tmp_path / "tickets.db"
    source = tmp_path / "tickets.csv"
    init_database(db)
    write_csv(source, [
        dict(id=1, subject="First", body="Body", confidence=95),
        dict(id=1, subject="Duplicate", body="Body", confidence=95),
    ])
    with pytest.raises(MigrationError):
        init_database(db, source)
    assert count_rows(db) == 0


def test_restart_does_not_reimport_deleted_tickets(tmp_path):
    db = tmp_path / "tickets.db"
    source = tmp_path / "tickets.csv"
    write_csv(source, [dict(id=7, subject="Ticket", body="Body", confidence=90)])
    assert init_database(db, source) == 1
    with db_connection(db, write=True) as connection:
        connection.execute("DELETE FROM tickets")
    assert init_database(db, source) == 0
    assert count_rows(db) == 0


def test_existing_records_are_not_overwritten_or_merged(tmp_path, caplog):
    db = tmp_path / "tickets.db"
    source = tmp_path / "tickets.csv"
    init_database(db)
    with db_connection(db, write=True) as connection:
        connection.execute(
            "INSERT INTO tickets (created_at,subject,body) VALUES (?,?,?)",
            ("2026-01-01", "Existing", "Body"),
        )
    write_csv(source, [dict(id=99, subject="Historical", body="Body", confidence=90)])
    assert init_database(db, source) == 0
    assert count_rows(db) == 1
    assert "already exist" in caplog.text


def test_concurrent_startup_imports_once(tmp_path):
    db = tmp_path / "tickets.db"
    source = tmp_path / "tickets.csv"
    write_csv(source, [dict(id=5, subject="Ticket", body="Body", confidence=90)])
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: init_database(db, source), range(4)))
    assert sum(results) == 1
    assert count_rows(db) == 1
    with db_connection(db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM app_migrations WHERE name = ?", (CSV_MIGRATION,)
        ).fetchone()[0] == 1


def test_concurrent_writes_keep_all_records(tmp_path):
    db = tmp_path / "tickets.db"
    init_database(db)

    def insert(number):
        with db_connection(db, write=True) as connection:
            connection.execute(
                "INSERT INTO tickets (created_at,subject,body) VALUES (?,?,?)",
                ("2026-01-01", f"Ticket {number}", "Body"),
            )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(insert, range(40)))
    assert count_rows(db) == 40


def test_connection_closes_and_failed_write_rolls_back(tmp_path):
    db = tmp_path / "tickets.db"
    init_database(db)
    with pytest.raises(RuntimeError):
        with db_connection(db, write=True) as connection:
            connection.execute(
                "INSERT INTO tickets (created_at,subject,body) VALUES (?,?,?)",
                ("2026-01-01", "Should roll back", "Body"),
            )
            raise RuntimeError("Simulated failure")
    assert count_rows(db) == 0
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


@pytest.mark.parametrize("content", [
    "subject\nMissing body header\n",
    "subject,body,confidence\nValid,Body,90\nMissing fields\n",
    "subject,body,confidence\nValid,Body,101\n",
])
def test_malformed_csv_is_rejected(tmp_path, content):
    db = tmp_path / "tickets.db"
    source = tmp_path / "tickets.csv"
    init_database(db)
    source.write_text(content, encoding="utf-8")
    with pytest.raises(MigrationError):
        init_database(db, source)
    assert count_rows(db) == 0


def test_upgrade_keeps_existing_schema_data(tmp_path):
    db = tmp_path / "tickets.db"
    # Build the exact old schema by omitting only the new legacy_id column.
    from backend.storage import _create_schema
    with db_connection(db, write=True) as connection:
        _create_schema(connection)
        connection.execute("DROP INDEX tickets_legacy_id")
        connection.execute("ALTER TABLE tickets DROP COLUMN legacy_id")
        connection.execute(
            "INSERT INTO tickets (id,created_at,subject,body) VALUES (?,?,?,?)",
            (42, "2026-01-01", "Keep me", "Body"),
        )
    init_database(db)
    with db_connection(db) as connection:
        row = connection.execute("SELECT * FROM tickets WHERE id = 42").fetchone()
    assert row["subject"] == "Keep me"
    assert row["legacy_id"] is None
