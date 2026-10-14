from pathlib import Path


from src.ticketloader import load_tickets
from src.kb import load_knowledge_base
from vector import create_vector_store
from retriever import create_retriever, retrieve_documents
from classifier import create_classifier, classify_ticket
from safety import check_prompt_injection
from router import route_ticket
from responder import create_responder, generate_response
from resultwriter import save_result

import os


from config import BASE_DIR, KNOWLEDGE_BASE_DIR, SAMPLE_TICKETS_FILE, TRIAGE_RESULTS_FILE

PROJECT_ROOT = BASE_DIR

print("Support Ticket Triage System")


# -------------------------
# 1. Load tickets
# -------------------------

tickets = load_tickets(SAMPLE_TICKETS_FILE)

print(f"Loaded {len(tickets)} tickets")


# -------------------------
# 2. Load knowledge base
# -------------------------

documents = load_knowledge_base(KNOWLEDGE_BASE_DIR)

print(f"Loaded {len(documents)} knowledge base documents")


# -------------------------
# 3. Create vector store
# -------------------------

vector_store = create_vector_store(documents)


# -------------------------
# 4. Create retriever
# -------------------------

retriever = create_retriever(vector_store)


# -------------------------
# 5. Create AI models
# -------------------------

classifier = create_classifier()
responder = create_responder()


# -------------------------
# 6. Prepare output file
# -------------------------

output_file = TRIAGE_RESULTS_FILE

os.makedirs(output_file.parent, exist_ok=True)

if os.path.exists(output_file):
    os.remove(output_file)


# -------------------------
# 7. Process every ticket
# -------------------------

for index, ticket in tickets.iterrows():

    print("\n===================================")
    print(f"Processing Ticket {ticket['ticket_id']}")
    print("===================================")

    ticket_text = (
        ticket["subject"]
        + " "
        + ticket["body"]
    )

    print("Subject:", ticket["subject"])


    # -------------------------
    # 8. Safety check
    # -------------------------

    is_suspicious = check_prompt_injection(ticket_text)

    print("Suspicious:", is_suspicious)


    # -------------------------
    # 9. Suspicious ticket
    # -------------------------

    if is_suspicious:

        decision = "ESCALATE"

        category = "unknown"
        urgency = "high"
        confidence = 0
        reason = "Potential prompt injection detected."

        customer_response = ""
        retrieved_sources = ""


    # -------------------------
    # 10. Normal ticket
    # -------------------------

    else:

        # Retrieve relevant KB documents

        relevant_documents = retrieve_documents(
            retriever,
            ticket_text
        )


        # Build context for the LLM

        context = ""

        for document in relevant_documents:
            context += document.page_content + "\n\n"


        # Store KB sources

        retrieved_sources = []

        for document in relevant_documents:
            retrieved_sources.append(
                document.metadata["source"]
            )

        retrieved_sources = ", ".join(retrieved_sources)


        # -------------------------
        # 11. Classify ticket
        # -------------------------

        classification = classify_ticket(
            classifier,
            ticket_text,
            context
        )

        category = classification["category"]
        urgency = classification["urgency"]
        confidence = classification["confidence"]
        reason = classification["reason"]


        print("Category:", category)
        print("Urgency:", urgency)
        print("Confidence:", confidence)
        print(
            "Can auto reply:",
            classification["can_auto_reply"]
        )


        # -------------------------
        # 12. Route ticket
        # -------------------------

        decision = route_ticket(
            classification,
            is_suspicious
        )


        # -------------------------
        # 13. Generate response
        # -------------------------

        customer_response = ""

        if decision == "AUTO_REPLY":

            customer_response = generate_response(
                responder,
                ticket_text,
                context
            )


    # -------------------------
    # 14. Display decision
    # -------------------------

    print("Decision:", decision)


    if customer_response:
        print("\nCustomer Response:")
        print(customer_response)


    # -------------------------
    # 15. Build result
    # -------------------------

    result = {
        "ticket_id": ticket["ticket_id"],
        "subject": ticket["subject"],
        "category": category,
        "urgency": urgency,
        "confidence": confidence,
        "is_suspicious": is_suspicious,
        "decision": decision,
        "reason": reason,
        "response": customer_response,
        "retrieved_sources": retrieved_sources,
        "expected_category": ticket["expected_category"]
    }


    # -------------------------
    # 16. Save result
    # -------------------------

    save_result(
        output_file,
        result
    )


print("\n===================================")
print("All tickets processed!")
print("===================================")

print(f"Results saved to {output_file}")