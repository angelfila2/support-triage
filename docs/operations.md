# Ticket operations and decision evidence

Live ticket storage is SQLite through Python's `sqlite3`; CSV files are evaluation
fixtures or optional historical imports. No ORM is required. Use the fresh ticket
schema for a new installation. Existing older ticket schemas are not altered or
deleted automatically.

## Intake, recovery and retry

Intake and its attempt are committed before inference. Each attempt has a unique
ID and a lease lasting the configured triage deadline plus 30 seconds. SQLite
write transactions and a unique active-attempt index prevent concurrent retries
from claiming the same ticket. Pending and failed tickets can be retried with
`POST /api/tickets/{id}/retry`; processing or completed tickets return 409.
Successful retry updates the original ticket ID and retains earlier attempts.

Startup and a 15-second background check mark expired attempts failed. Old
processing rows without an attempt are recovered after 180 seconds. Recovery
does not automatically rerun inference; the operator can inspect and retry.
Unexpired leases are preserved. Finalization checks the lease and attempt status,
so a late result cannot overwrite a recovered/retried attempt. A request deadline
does not kill a Python worker: its inference slot remains occupied until it exits.

## Evidence and versions

`GET /api/tickets/{id}` includes the latest provenance and attempt count.
`GET /api/tickets/{id}/attempts?limit=20` returns up to 100 attempts, newest first.
Each completed attempt retains its assessment/result and the actual retrieved
FAQ text with SHA-256 hashes. Provenance includes model names, available Ollama
digests, agent/prompt/RAG source hashes, corpus hashes and package versions.
Model manifests are cached for 60 seconds; the stored digest is a best-effort
observation, not an atomic attestation of the running model. Metadata is saved
before inference so interrupted attempts retain it when available. Human review
and resolution update ticket fields without rewriting the attempt snapshots.

All ticket and history endpoints require bearer access by default. Read-only
credentials cannot submit, retry or modify tickets. Credentials are configured
in ignored local `.env` files and never bundled in frontend assets.

## Pages and analytics

`GET /api/tickets` returns `{items,total,limit,offset,summary}`. Default page size
is 25, maximum 100. Filters are `q`, `category`, `urgency`, `processing_status`
and `review` (`pending`, `correct`, `incorrect`). Query values are parameterized;
search treats `%` and `_` as literal characters. Summary counts cover all matching
records. `GET /api/analytics` aggregates the full table, using completed tickets
for decision/category/confidence statistics and returning the latest ten completed
tickets. The frontend does not download the entire table to filter or summarize.

## Dependency probes

`GET /health/live` reports process liveness. `GET /health/ready` opens SQLite in
read-only mode, checks the ticket/attempt tables and queries Ollama for the
configured chat model and `mxbai-embed-large`. It returns 200 when available,
otherwise 503 with dependency flags. This checks availability, not inference
quality or a complete warm-up of the vector index. Health endpoints expose no
ticket content or credentials.

## Verification

The isolated browser harness (`python -m backend.test.browser_smoke_server`)
creates a new synthetic database under ignored `backend/output/`, listens only
on localhost, and uses explicit test credentials. Its single simulated failure
hook exists only in that test entry point. Never deploy that entry point.
The normal application entry point remains `uvicorn backend.api:app`.

CI/Docker packaging and portfolio presentation are outside this change.


## Seamless local dashboard access

The Vite development/preview server reads the write credential from `backend/.env`
and forwards same-origin `/api` requests to the loopback backend. The browser
never receives this credential. Start the two servers; there is no manual connect
step. Requests from unrelated origins are rejected before they reach the proxy.
Restart both servers after an environment change. Direct API access retains bearer
scope checks. This local proxy is not a user-authentication system for public hosting.


### Helpdesk response status

Ticket details includes an independent helpdesk status: Open / reopened,
Responded (waiting for user info), Responded (awaiting user confirmation), and
Responded (closed). Use the single Helpdesk update form to choose a status, optionally adjust urgency, and enter a required update note. Blank or whitespace-only notes are rejected by both the UI and API. Status and notes save together in one transaction; the timeline preserves each note even when the status stays the same. Selecting
a Responded state records the reply as sent by the helpdesk outside this app;
the application does not deliver email. Reopening preserves the response history.
Every transition is logged in the timeline. Helpdesk updates preserve the AI assessment and existing response timestamp. Urgency stays unchanged unless explicitly adjusted. The latest note appears on the ticket; earlier notes remain in the timeline.

Startup adds `tickets.helpdesk_status` to older databases without deleting rows.
Previously responded tickets default to awaiting user confirmation; helpdesk staff
can adjust them. New response records also default to awaiting confirmation.
