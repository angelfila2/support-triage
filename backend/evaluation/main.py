import sys

from backend.config import SAMPLE_TICKETS_FILE, TRIAGE_RESULTS_FILE
from backend.evaluation.ticketloader import load_tickets
from backend.agent.triage import triage_ticket
from backend.evaluation.resultwriter import save_result


def main():
    print("=" * 60)
    print("SupportFlow — Batch Ticket Triage Runner")
    print("=" * 60)

    # 1. Verify and load benchmark sample tickets
    if not SAMPLE_TICKETS_FILE.exists():
        print(f"Error: Sample tickets file not found at: {SAMPLE_TICKETS_FILE}")
        sys.exit(1)

    tickets = load_tickets(SAMPLE_TICKETS_FILE)
    print(f"Loaded {len(tickets)} benchmark tickets from {SAMPLE_TICKETS_FILE.name}")

    # 2. Prepare clean output results file
    output_file = TRIAGE_RESULTS_FILE
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.exists():
        output_file.unlink()

    # 3. Process every ticket through the unified triage engine
    for index, ticket in tickets.iterrows():
        ticket_id = ticket.get("ticket_id", index + 1)
        subject = str(ticket.get("subject", ""))
        body = str(ticket.get("body", ""))
        expected_category = ticket.get("expected_category", "")

        print("\n" + "-" * 50)
        print(f"Processing Ticket #{ticket_id}: {subject[:45]}...")
        print("-" * 50)

        # Execute the unified 6-stage triage pipeline
        triage_output = triage_ticket(subject, body)

        # Display decision summary to CLI
        print(f"Category:     {triage_output['category']}")
        print(f"Urgency:      {triage_output['urgency']} (SLA: {triage_output['sla']})")
        print(f"Confidence:   {triage_output['confidence']}%")
        print(f"Decision:     {triage_output['decision']}")
        print(f"Reason:       {triage_output['reason']}")

        if triage_output.get("response"):
            print("\nGenerated Auto-Reply:")
            print(triage_output["response"].strip())

        # Format retrieved sources as a readable string for CSV
        sources = triage_output.get("retrieved_sources", [])
        sources_str = ", ".join(sources) if isinstance(sources, list) else str(sources)

        # 4. Save structured result
        record = {
            "ticket_id": ticket_id,
            "subject": subject,
            "category": triage_output["category"],
            "urgency": triage_output["urgency"],
            "confidence": triage_output["confidence"],
            "is_suspicious": triage_output["is_suspicious"],
            "decision": triage_output["decision"],
            "reason": triage_output["reason"],
            "response": triage_output.get("response", ""),
            "retrieved_sources": sources_str,
            "expected_category": expected_category,
        }

        save_result(output_file, record)

    print("\n" + "=" * 60)
    print("All tickets successfully processed!")
    print(f"Results saved to: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
