# A beginner's guide to this project

Start with the flow, rather than reading every file at once:

1. A React page sends a ticket through `frontend/src/services/api.js`.
2. `backend/api.py` accepts it, saves an attempt and calls the triage pipeline.
3. `backend/agent/triage.py` coordinates retrieval, assessment, routing and a reply.

## Where to find things

| Location | What to read it for |
|---|---|
| `frontend/src/App.jsx` | Which URL opens which screen; the shared sidebar/header layout. |
| `frontend/src/pages/TicketInboxPage.jsx` | Fetching, searching, filtering and opening tickets. |
| `frontend/src/pages/NewTicketPage.jsx` | Manual/email entry and submitting a ticket for AI triage. |
| `frontend/src/pages/TicketDetailsPage.jsx` | Viewing one ticket, reviewing AI output and recording an agent response. |
| `frontend/src/pages/InsightsPage.jsx` | Aggregate statistics from the backend. |
| `frontend/src/components/` | Visible pieces used by pages, such as email preview and the sidebar. |
| `frontend/src/services/api.js` | Sending authenticated HTTP requests and submitting triage. Plain JavaScript; no JSX. |
| `frontend/src/styles/` | Styles grouped by screen plus shared layout and responsive rules. `index.css` imports them in order. |
| `backend/api.py` | API request validation, routes and connecting the other backend parts. |
| `backend/storage.py` | SQLite schema, transactions and optional historical import. |
| `backend/jobs.py` | Processing attempts, retry claims and interrupted-work recovery. |
| `backend/audit.py` | Saved source evidence and model/code versions. |
| `backend/auth.py` | Read/write API credential checks. |
| `backend/config.py` | Environment settings and file paths. |
| `backend/agent/triage.py` | The overall AI processing flow; start here to understand the agent. |
| `backend/agent/classifier.py` | One structured model assessment: category, severity, confidence and answerability. |
| `backend/agent/policy.py` | Supported capabilities and rules the model cannot override. |
| `backend/agent/router.py` | The final auto-reply/escalation decision. Kept small because this safety boundary matters. |
| `backend/agent/responder.py` | Selecting and returning complete, original FAQ passages. |
| `backend/agent/safety.py` | Suspicious-instruction checks. |
| `backend/agent/structured_output.py` | Parsing model JSON safely; used by assessment and reply generation. |
| `backend/agent/runtime.py` | Limiting inference concurrency and waiting time. |
| `backend/rag/kb.py` | Loading knowledge-base files. |
| `backend/rag/vector.py` | Creating/reusing the persistent embedding index. |
| `backend/rag/retriever.py` | Finding documents and applying the relevance threshold. |
| `backend/evaluation/run_batch.py` | Running sample tickets and writing evaluation CSV results in one place. |
| `backend/evaluation/evaluate.py` | Scoring the exported results. |
| `backend/evaluation/benchmark_*.py`, `compare_retrieval.py`, `validate_agent.py` | Focused retrieval, decision and full-pipeline experiments. |
| `backend/test/` | Automated tests. The browser server is an explicit, isolated test helper. |

## Why some small files stay separate

Small does not automatically mean unnecessary. Authentication, routing and JSON
parsing each have a clear responsibility and multiple callers or important tests.
Keeping them separate makes those boundaries easier to find. The old standalone
answerability module was different: it duplicated assessment already performed
by the classifier and had no live caller, so it was removed.

The batch-only CSV reader/writer helpers were merged into `run_batch.py`. The two
small frontend API helpers were merged into `api.js`. The unused in-memory ticket
history was removed: SQLite and the analytics endpoint are the source of truth.

## Useful commands

Run these from the repository root with the backend environment activated:

```powershell
python -m pytest -q
python -m backend.evaluation.run_batch
python -m backend.evaluation.evaluate
```

Batch inference needs Ollama; normal unit tests use mocks. Benchmark CSVs are
test data, not live ticket storage. Local `.env`, databases, vector indexes and
runtime evaluation reports are intentionally ignored by Git.

Frontend checks run from `frontend/`:

```powershell
npm run build
npm run lint
```

To change a screen, start with its page and matching stylesheet. Avoid splitting
every function into another file; extract something when it has a clear separate
job or needs to be reused.


Incident priority: `backend/agent/classifier.py` defines `IncidentAssessment` and
extracts facts in the existing model call. `backend/agent/policy.py` contains
`incident_policy()`, which assigns incident priority from those facts. The router
still enforces human escalation for SEV1 and SEV2. Regression examples are in
`backend/test/test_incident_assessment.py`.
