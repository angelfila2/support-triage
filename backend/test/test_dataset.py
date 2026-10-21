import csv

from backend.evaluation.prepare_dataset import seed_database, write_dataset
from backend.storage import db_connection


def test_dataset_matches_supported_schema_and_has_both_routes(tmp_path):
    path = tmp_path / "sample.csv"
    assert write_dataset(path) == 30
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len({row["ticket_id"] for row in rows}) == 30
    assert {row["expected_category"] for row in rows} == {
        "password_reset", "billing_question", "shipping_delay", "login_issues", "other"
    }
    assert {row["expected_decision"] for row in rows} == {"AUTO_REPLY", "ESCALATE"}
    assert all(row["subject"] and row["body"] for row in rows)
    assert all(row["expected_decision"] == "ESCALATE" for row in rows if row["expected_urgency"] in {"SEV1", "SEV2"})
    adapted = [row for row in rows if row["origin"] == "adapted"]
    assert len(adapted) == 10
    assert all(row["source_url"] and row["source_record"] for row in adapted)


def test_seed_preserves_existing_work_and_never_imports_answer_key(tmp_path):
    path = tmp_path / "demo.db"
    assert seed_database(path) == 30
    with db_connection(path, write=True) as connection:
        connection.execute("UPDATE tickets SET review_notes = 'keep this' WHERE id = 1")
        connection.execute("INSERT INTO tickets (created_at, subject, body) VALUES ('now', 'existing', 'keep')")
    assert seed_database(path) == 0
    with db_connection(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 31
        assert connection.execute("SELECT review_notes FROM tickets WHERE id = 1").fetchone()[0] == "keep this"
        assert connection.execute("SELECT COUNT(*) FROM tickets WHERE category IS NOT NULL OR decision IS NOT NULL OR response IS NOT NULL").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM tickets WHERE legacy_id LIKE 'demo-orchestrate-v1:%'").fetchone()[0] == 30
