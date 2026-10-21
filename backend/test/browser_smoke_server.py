"""Isolated browser acceptance server: synthetic records and test-only credentials.

Run explicitly with python -m backend.test.browser_smoke_server. Never use this
entry point for a deployment. Normal uvicorn backend.api:app has no failure hook.
"""

import os
from pathlib import Path
from tempfile import mkdtemp


def main():
    root = Path(__file__).resolve().parents[2]
    output = Path(mkdtemp(prefix="browser-smoke-", dir=root / "backend" / "output"))
    os.environ.update(OUTPUT_DIR=str(output), TICKETS_FILE=str(output / "absent.csv"),
                      AUTH_REQUIRED="true", API_WRITE_TOKEN="browser-test-" + "w" * 32,
                      API_READ_TOKEN="browser-test-" + "r" * 32,
                      CORS_ORIGINS="http://127.0.0.1:5174")
    from backend import api, jobs
    from backend.storage import init_database, db_connection
    import uvicorn

    init_database(api.DB_PATH)
    with db_connection(api.DB_PATH, write=True) as connection:
        for number in range(60):
            connection.execute("""INSERT INTO tickets
                (created_at,subject,body,category,urgency,confidence,decision,sla,processing_status)
                VALUES ('2026-10-21T00:00:00+00:00',?,'Synthetic browser fixture','billing_question','SEV5',95,'ESCALATE','5 days','completed')""", (f"Browser seed {number:02}",))
    row, attempt_id = jobs.claim(api.DB_PATH, 120, subject="Interrupted browser ticket", body="My password reset link expired.")
    with db_connection(api.DB_PATH, write=True) as connection:
        connection.execute("UPDATE ticket_attempts SET lease_until='2000-01-01T00:00:00+00:00' WHERE id=?", (attempt_id,))
    original = api.triage_ticket
    failures = set()

    def smoke_triage(subject, body):
        if subject == "Browser failure test" and subject not in failures:
            failures.add(subject)
            raise RuntimeError("Simulated inference outage in acceptance test")
        return original(subject, body)

    api.triage_ticket = smoke_triage
    print(f"Synthetic acceptance database: {api.DB_PATH}", flush=True)
    uvicorn.run(api.app, host="127.0.0.1", port=8011, log_level="warning")


if __name__ == "__main__":
    main()
