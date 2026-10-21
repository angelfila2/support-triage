# P0/P1 implementation and validation

Scope: one customer issue per ticket, four local FAQ capabilities, a local Ollama
model and a SQLite database. This remains a structured triage pipeline, not a
general autonomous agent. The model supplies structured assessments; application
code owns escalation policy. These rules deliberately limit automatic replies.

| Problem | Implementation | Verification |
|---|---|---|
| Submission lost on AI error | Commit intake before inference; update the same ID on completion/failure | API tests inspect the committed row from inside a mock model call |
| Model overrides human-only policy | Explicit capability policy rejects refund approval, payment investigations, lost/stale parcels and unsupported integrations | Adversarial model-permission tests plus live development/holdout runs |
| Exhausted vs partial troubleshooting | Compare reported attempts with the four documented login steps; exclude explicitly untried clauses; preserve raw model fields | Exhaustion paraphrases and partial-progress controls |
| Topical but unsupported retrieval | Minimum cosine relevance, known source selection and capability-level evidence gate; unknown actions escalate | Retrieval benchmark, no-evidence tests and unsupported technical queries |
| Invented replies | Model selects numbered FAQ passages; code renders their original complete text; invalid selection escalates | Invalid/noninteger passage IDs and live full-pipeline tests |
| Evaluation only reports accuracy | Separate intent/routing/severity precision, recall and macro F1; critical escalation recall; repeated live runs with dataset/code/corpus hashes and model digests | Hand-calculated metric tests and `validate_agent` |
| Missing development data | Reproducible adapted/synthetic cases, documented provenance and separate answer keys | Fixture validation and SQLite seed idempotence tests |
| No inference bounds | Positive configurable transport timeout, total request deadline, bounded worker pool and nonblocking capacity admission | A timed-out job retains its slot until actual completion; timeout ticket remains failed |
| Fragile injection keywords | Unicode normalization and bounded override/exfiltration patterns, capability restriction and extractive reply boundary | Benign MFA terminology and attack variants; critical severity never downgraded by safety branch |
| Unprotected ticket API | Bearer read/write scopes, constant-time credential comparison, secure default and session-only frontend credential input | Missing/incorrect credential and read-vs-write API tests |
| Response request coercion | Strict booleans, severity literals, bounded notes; frontend handles structured validation errors | Invalid response-model payload tests |
| No manual intake | Upload/manual modes, input limits and one-issue instruction | Production build, lint and API input tests |
| Rebuilt/duplicated vector index | Persistent Chroma, content-addressed IDs and embedding reuse | Restart, no-duplicate and changed-document tests |

## Run

```powershell
python -m pytest -q
python -m backend.evaluation.compare_retrieval
python -m backend.evaluation.benchmark_answerability
python -m backend.evaluation.validate_agent
python -m backend.evaluation.main
python -m backend.evaluation.evaluate
```

Live evaluation writes synthetic fixture reports under ignored `backend/output/`.
`validate_agent` repeats development and full-pipeline holdout runs twice. The
holdout labels were authored before the first validation run and are not changed
to improve reported scores. The first 12-case set became a regression set when
fixing paragraph-copy formatting. The new eight-case `heldout_v2.json` achieved
correct routing/severity in both initial runs, but one generic outage received
an unrelated shipping category. The initial result is preserved in
`agent_final_holdout_results.json`. The later unknown-capability-to-other rule
is tested as regression in `agent_final_policy_regression_results.json`. Do not present
those regression scores as unseen-test accuracy. These are small synthetic probes,
not representative production data. New independent labels are needed for later tuning.

The existing `benchmark_answerability` report measures classification plus policy
and routing only. The holdout runner exercises response generation too. A verified
passage proves provenance, not perfect applicability; policy coverage is limited to
the documented capabilities. A keyword/rule guard is not a universal semantic
injection detector. Unknown cases are intentionally escalated. Confidence remains
a model-provided number, not a calibrated probability.

## API access

Create or configure the local `backend/.env` file (not versioned). Use a random write token and,
optionally, a distinct read token, each at least 32 characters. Start the backend,
then enter the credential in the dashboard header. It is held in sessionStorage,
not a frontend environment variable or URL. Write credentials permit intake and
updates; read credentials permit ticket reads only. HTTPS and operator secret
management are required for remote use. This is scoped demo authentication, not
per-customer tenancy or a replacement for an identity provider. Deliberately
disabling it with `AUTH_REQUIRED=false` is for a trusted local demo only.

Transport timeout defaults to 45 seconds, overall triage deadline to 120 seconds,
and inference slots to two per backend process. A timed-out worker cannot safely
be killed by Python; it keeps its slot until it exits. This prevents unbounded
queued calls and late results cannot mark failed tickets completed. It is not
process isolation. Multiple backend workers each have their own capacity limit.

Fresh-schema setup is intentional. Existing older databases are not automatically
upgraded or deleted. Use a new output directory for a clean demo database.
Retry, interrupted-processing recovery, audit history, pagination and dependency
readiness are implemented; see [operations](operations.md). Mailbox integration
and deployment packaging remain separate work.


## Verification snapshot (2026-10-21)

- 234 backend tests passed; frontend production build and ESLint passed.
- npm audit reported zero vulnerabilities after the source-map-js patch.
- Two development runs of 26 cases produced zero unsafe reply decisions and
  zero unnecessary escalations after application policy enforcement.
- The refreshed standard answerability report scored 26/26 enforced decisions.
  Model parsing fallbacks are counted separately and must not be described as
  correct model reasoning.
- The final eight-case regression set was run twice through the full pipeline.
  Category, severity and routing matched all 16 expectations; all four critical
  incident observations escalated and all six eligible replies used original
  FAQ passages. These are regression results after inspection and fixes, not
  independent production accuracy estimates.
- The earlier blind eight-case result remains 87.5% category accuracy, with
  correct routing/severity and no unsafe replies in both runs.
- No real tickets were seeded, migrated, deleted or sent to customers by live
  evaluation. Browser acceptance uses an isolated synthetic database and real local Ollama;
  intake, failed intake, recovery/retry, review, resolution, paging and analytics
  are checked without changing operational ticket data.


## Expanded operations acceptance (2026-10-21)

- A frozen 24-case synthetic set was run twice through real Ollama inference.
  Initial routing/category/severity matched all labels, but two login replies
  per run omitted required troubleshooting steps. The original report remains
  under `backend/output/extended_evaluation_results.json`.
- Procedure grouping and mandatory documented next-step selection fixed those
  omissions. Two subsequent regression runs matched all 48 category, routing
  and severity labels. Eighteen eligible replies passed exact quotation and
  required-fact checks; no unsafe auto replies or safety-flag mismatches occurred.
  Critical escalation recall was 1.0 in each run. An invalid model assessment
  used the safe fallback; passing application decisions do not prove correct
  model reasoning.
- Browser acceptance covered token access, server paging/filtering, interrupted
  ticket recovery, same-ID retry, manual success/failure, email preview/analysis,
  human approval and response recording. All used a separate synthetic database.
- Retry concurrency, expired-result rejection, live-lease preservation, orphan
  recovery, read-only retry denial, retained audit metadata and whole-table
  analytics are covered by automated tests.

These are inspected regression fixtures with agent-authored labels. Independently
human-labelled representative evaluation remains future work. CI/Docker and
portfolio presentation were deliberately excluded from this change.
