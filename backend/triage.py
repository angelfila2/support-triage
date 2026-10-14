"""Shared pipeline for API and batch ticket processing."""

from functools import lru_cache
from threading import Lock

from classifier import classify_ticket, create_classifier, SLA_MAP
from config import KNOWLEDGE_BASE_DIR
from responder import create_responder, generate_response
from retriever import create_retriever, retrieve_documents
from router import route_ticket
from safety import check_prompt_injection
from src.kb import load_knowledge_base
from vector import create_vector_store


_engine_lock = Lock()


@lru_cache(maxsize=1)
def _build_engine():
    documents = load_knowledge_base(KNOWLEDGE_BASE_DIR)
    vector_store = create_vector_store(documents)

    return (
        create_retriever(vector_store),
        create_classifier(),
        create_responder(),
    )


def get_engine():
    """Initialize resources once, when the first safe ticket is processed."""
    with _engine_lock:
        return _build_engine()


def triage_ticket(subject, body):
    ticket_text = f"{subject}\n\n{body}"

    is_suspicious = check_prompt_injection(ticket_text)

    if is_suspicious:
        return {
            "category": "other",
            "urgency": "SEV3",
            "confidence": 0,
            "is_suspicious": True,
            "can_auto_reply": False,
            "decision": "ESCALATE",
            "reason": "Potential prompt injection detected.",
            "response": "",
            "retrieved_sources": [],
            "sla": SLA_MAP["SEV3"],
        }

    retriever, classifier, responder = get_engine()

    relevant_documents = retrieve_documents(retriever, ticket_text)

    context = "\n\n".join(
        document.page_content
        for document in relevant_documents
    )

    retrieved_sources = list(
        dict.fromkeys(
            document.metadata.get("source", "Unknown source")
            for document in relevant_documents
        )
    )

    # One call determines classification and answerability together.
    classification = classify_ticket(
        classifier,
        ticket_text,
        context,
    )

    decision = route_ticket(classification, is_suspicious)

    if (
        decision == "ESCALATE"
        and classification["urgency"] in {"SEV4", "SEV5"}
    ):
        classification["urgency"] = "SEV3"
        classification["sla"] = SLA_MAP["SEV3"]

    customer_response = ""

    if decision == "AUTO_REPLY":
        customer_response = generate_response(
            responder,
            ticket_text,
            context,
        )

    return {
        "category": classification["category"],
        "urgency": classification["urgency"],
        "confidence": classification["confidence"],
        "is_suspicious": is_suspicious,
        "can_auto_reply": classification["can_auto_reply"],
        "decision": decision,
        "reason": classification["reason"],
        "response": customer_response,
        "retrieved_sources": retrieved_sources,
        "sla": classification["sla"],
    }