from config import BASE_DIR, KNOWLEDGE_BASE_DIR
from src.kb import load_knowledge_base
from vector import create_vector_store
from retriever import create_retriever, retrieve_documents
from classifier import create_classifier, classify_ticket
from answerability import create_answerability_checker, check_answerability
from router import route_ticket
from responder import create_responder, generate_response
from safety import check_prompt_injection

documents = load_knowledge_base(
    KNOWLEDGE_BASE_DIR
)

vector_store = create_vector_store(
    documents
)

retriever = create_retriever(
    vector_store
)

classifier = create_classifier()

answerability_checker = create_answerability_checker()

responder = create_responder()


# -------------------------
# Triage one ticket
# -------------------------

def triage_ticket(subject, body):

    ticket_text = subject + " " + body


    # -------------------------
    # Safety check
    # -------------------------

    is_suspicious = check_prompt_injection(
        ticket_text
    )


    if is_suspicious:
        return {
            "category": "other",
            "urgency": "SEV3",
            "confidence": 0,
            "is_suspicious": True,
            "decision": "ESCALATE",
            "reason": "Potential prompt injection detected.",
            "response": "",
            "retrieved_sources": [],
            "sla": "3 days"
        }


    # -------------------------
    # Retrieve knowledge
    # -------------------------

    relevant_documents = retrieve_documents(
        retriever,
        ticket_text
    )


    # -------------------------
    # Build context
    # -------------------------

    context = ""

    for document in relevant_documents:
        context += (
            document.page_content
            + "\n\n"
        )


    # -------------------------
    # Store retrieved sources
    # -------------------------

    retrieved_sources = []

    for document in relevant_documents:
        retrieved_sources.append(
            document.metadata["source"]
        )


    # -------------------------
    # Classify ticket
    # -------------------------

    classification = classify_ticket(
        classifier,
        ticket_text,
        context
    )


    # -------------------------
    # Check answerability
    # -------------------------

    can_auto_reply = check_answerability(
        answerability_checker,
        ticket_text,
        context
    )

    classification["can_auto_reply"] = (
        can_auto_reply
    )


    # -------------------------
    # Route ticket
    # -------------------------

    decision = route_ticket(
        classification,
        is_suspicious
    )


    # -------------------------
    # Enforce escalation severity & SLA rules
    # If a low-severity ticket (SEV4/SEV5) cannot be auto-replied,
    # bump it to SEV3 (3 days) to guarantee timely human review.
    # -------------------------

    if (
        decision == "ESCALATE"
        and classification["urgency"] in ["SEV4", "SEV5"]
    ):
        classification["urgency"] = "SEV3"
        classification["sla"] = "3 days"


    # -------------------------
    # Generate response
    # -------------------------

    customer_response = ""

    if decision == "AUTO_REPLY":
        customer_response = generate_response(
            responder,
            ticket_text,
            context
        )


    # -------------------------
    # Return result
    # -------------------------

    return {
        "category": classification["category"],
        "urgency": classification["urgency"],
        "confidence": classification["confidence"],
        "is_suspicious": is_suspicious,
        "decision": decision,
        "reason": classification["reason"],
        "response": customer_response,
        "retrieved_sources": retrieved_sources,
        "sla": classification["sla"]
    }