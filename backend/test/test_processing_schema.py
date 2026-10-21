from backend.storage import db_connection, init_database


def test_fresh_inputs_default_to_pending(tmp_path):
    db = tmp_path / "tickets.db"
    init_database(db)
    with db_connection(db, write=True) as connection:
        connection.execute("INSERT INTO tickets (created_at,subject,body) VALUES ('now','subject','body')")
        row = connection.execute("SELECT * FROM tickets").fetchone()
    assert row["processing_status"] == "pending"
    assert row["processing_error"] is None


def test_restart_preserves_processing_status_and_error(tmp_path):
    db = tmp_path / "tickets.db"
    init_database(db)
    with db_connection(db, write=True) as connection:
        connection.execute(
            """INSERT INTO tickets
               (created_at,subject,body,processing_status,processing_error,review_notes)
               VALUES ('now','keep','body','failed','unavailable','review')"""
        )
    init_database(db)
    with db_connection(db) as connection:
        rows = connection.execute("SELECT * FROM tickets").fetchall()
    assert len(rows) == 1
    assert rows[0]["processing_status"] == "failed"
    assert rows[0]["processing_error"] == "unavailable"
    assert rows[0]["review_notes"] == "review"


def test_historical_predictions_import_as_completed(tmp_path):
    source = tmp_path / "history.csv"
    source.write_text("subject,body,decision\nold,body,ESCALATE\ninput,body,\n", encoding="utf-8")
    db = tmp_path / "tickets.db"
    assert init_database(db, source) == 2
    with db_connection(db) as connection:
        rows = connection.execute("SELECT processing_status FROM tickets ORDER BY id").fetchall()
    assert [row[0] for row in rows] == ["completed", "pending"]
