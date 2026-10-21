# Development evaluation data

## Retrieval and answerability development benchmarks

The supported application scope is one issue per ticket. The original retrieval
benchmark has 18 cases; `retrieval_challenge.json` adds 26 harder single-issue
cases, including paraphrases, exhausted troubleshooting, human-only billing
actions, outages and technical questions with similar terminology. Its boolean
`expected_can_auto_reply` annotations express FAQ/policy eligibility, not the
model's confidence. A relevant FAQ can still require escalation.
Seven cases additionally label `expected_troubleshooting_exhausted`, covering
the original failed login case, three paraphrases and three partial/untried
troubleshooting controls. The live report counts schema fallbacks and incorrect
exhaustion flags separately so safe fallback is not mistaken for correct reasoning.

The four earlier multi-issue probes are retained in
`retrieval_multi_issue_out_of_scope.json` for reference, excluded from the primary
benchmark. A single issue may still require several documents in a larger corpus;
the number of relevant sources is not a general detector of multi-issue tickets.
All these cases are development fixtures, not an independent held-out evaluation.
The UI asks for one issue; automatic multi-issue detection is outside this scope.

Run `python -m backend.evaluation.compare_retrieval` for top-1/top-2 comparisons
and `python -m backend.evaluation.benchmark_answerability` for real classifier
assessment using the application's current top-2, 0.5 threshold configuration.
Neither command creates live tickets or sends/generated customer replies.
The latter calls classification and routing only, not the safety filter,
severity promotion, responder or full HTTP intake. It does not measure response
faithfulness or whether an outage was assigned the correct severity.

`sample_tickets.csv` contains 30 development cases: ten short paraphrases of the
HackerRank Orchestrate samples and twenty locally authored FAQ/policy cases.
These are not thirty real customer tickets or a held-out production benchmark.

Source: https://github.com/interviewstreet/hackerrank-orchestrate-may26/blob/b5a301c9e89d2f05cf4a7b04136a1399b6f3f0f4/support_tickets/sample_support_tickets.csv

`source_record` is the one-based CSV data record, not the physical line number.
No upstream responses, contact details or support corpus are copied. The source
status is preserved separately; our expected labels are provisional SupportFlow
annotations, not official HackerRank labels. Review these before reporting scores.

## Why routing differs

Our FAQ covers password resets, billing, shipping and generic login troubleshooting.
It does not document HackerRank assessment controls, Claude privacy controls or Visa
procedures. Consequently all ten adapted cases expect escalation with this FAQ.
Their categories map to `other`; the dataset does not invent new classifier categories.
Local cases cover all five supported intent categories and both routing outcomes.
This deliberately small, imbalanced development set cannot establish real-world accuracy.

Expected severity uses the current policy: unanswerable SEV4/5 becomes SEV3.
`expected_initial_urgency` preserves the pre-routing annotation. Injection detection
is labelled separately. The benign `system prompt` case intentionally exposes the
safety guard against false positives.

## Rebuild and run

Run from the repository root:

```powershell
python -m backend.evaluation.prepare_dataset
python -m backend.evaluation.run_batch
python -m backend.evaluation.evaluate
```

The last two commands require running Ollama and the documented models. The current
evaluator scores intent, routing and severity separately using precision, recall
and macro F1, and reports critical-incident escalation recall.
Only subject/body enter the triage pipeline; answer-key columns must never enter prompts.
CSV here is a benchmark fixture, not live ticket persistence.

## Seed SQLite with inputs, not invented predictions

```powershell
python -m backend.evaluation.prepare_dataset --seed-db backend/output/demo.db
```

This creates a separate SQLite demo database using the existing storage schema.
Thirty input tickets are inserted with stable `legacy_id` values. Repeating the
command adds zero duplicates and does not change existing tickets or review data.
Predicted category, severity, confidence, decision and response remain NULL; expected
answers stay exclusively in the evaluation CSV. These are unprocessed fixtures.
Pending tickets can be processed with the retry endpoint or ticket-details button
when this database is explicitly configured as the application database. The normal API
continues to use `supportflow.db`; it is not changed by this command.

To seed an existing database, pass its path explicitly after backing it up. Existing
rows are preserved, but the inserted rows remain unprocessed. Do not use fixture
records in real operational metrics. A separate held-out dataset should be collected
before tuning and measuring production performance.

## Expanded full-pipeline regression

`evaluation_extended.json` freezes 24 additional single-issue cases, including
eligible FAQ requests, human-only actions, outages and injection/benign controls.
Expected reply facts test usefulness as well as exact source quotation. Labels
were authored before the first run and were not changed to improve scores.
The first run exposed replies quoting a login introduction without its steps;
the revised responder groups procedures and requires the documented next step.
Subsequent results are regression evidence, not unseen-test performance.

```powershell
python -m backend.evaluation.validate_agent --skip-development --holdout evaluation_extended.json --output extended_evaluation_regression_results.json
```

The runner repeats the set twice and records dataset/code/corpus hashes, model
digests, intent/routing/severity metrics, safety mismatches, exact-quote grounding
and required-fact checks. These are agent-authored synthetic cases; independent
human annotations and representative tickets are still needed.
