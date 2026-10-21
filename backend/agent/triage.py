"""Shared pipeline for API and batch ticket processing."""

from functools import lru_cache
from hashlib import sha256
from threading import Lock

from backend.agent.classifier import (
    SLA_MAP,
    classify_ticket,
    create_classifier,
)
from backend.agent.responder import create_responder, generate_response
from backend.agent.router import route_ticket
from backend.agent.safety import check_prompt_injection
from backend.agent.policy import capability, enforce_policy
from backend.config import KNOWLEDGE_BASE_DIR
from backend.rag.kb import load_knowledge_base
from backend.rag.retriever import create_retriever, retrieve_documents
from backend.rag.vector import create_vector_store


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
        severity = "SEV2"  # Unassessed impact: priority human review without inference.
        return {
            "category": "other",
            "urgency": severity,
            "confidence": 0,
            "is_suspicious": True,
            "can_auto_reply": False,
            "decision": "ESCALATE",
            "reason": "Potential prompt injection detected. Incident impact unassessed; priority human review required.",
            "response": "",
            "retrieved_sources": [],
            "sla": SLA_MAP[severity],
        }

    retriever, classifier, responder = get_engine()

    relevant_documents = retrieve_documents(
        retriever,
        ticket_text,
    )

    # Only feed evidence for the recognized single-issue capability to the model.
    _, expected_source = capability(ticket_text)
    if expected_source:
        relevant_documents = [doc for doc in relevant_documents
                              if str(doc.metadata.get("source", "")).replace("\\", "/").rsplit("/", 1)[-1] == expected_source]

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

    # Classify even without evidence so incident severity is assessed.
    classification = classify_ticket(
        classifier,
        ticket_text,
        context,
    )

    classification = enforce_policy(ticket_text, context, classification)
    classification["sla"] = SLA_MAP[classification["urgency"]]

    # Enforce grounding in application code, regardless of what
    # the model says about answerability.
    if not relevant_documents:
        classification["can_auto_reply"] = False
        classification["reason"] = (
            "No FAQ documents passed the retrieval relevance threshold. "
            "Human review is required. "
            + classification["reason"]
        )

    decision = route_ticket(
        classification,
        is_suspicious,
    )

    # Preserve SEV1/SEV2. Promote lower-priority escalations to SEV3.
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

    if decision == "AUTO_REPLY" and not customer_response:
        decision = "ESCALATE"
        classification["can_auto_reply"] = False
        classification["reason"] = "No verifiable FAQ quotations were produced; human review required."
        if classification["urgency"] in {"SEV4", "SEV5"}:
            classification["urgency"] = "SEV3"
            classification["sla"] = SLA_MAP["SEV3"]

    return {
        "_evidence": [{"source": str(doc.metadata.get("source", "Unknown source")).replace("\\", "/").rsplit("/", 1)[-1],
                       "content": doc.page_content,
                       "sha256": sha256(doc.page_content.encode()).hexdigest()} for doc in relevant_documents],
        "_assessment": classification,
        "policy_reason": classification.get("policy_reason", ""),
        "troubleshooting_exhausted": classification.get("troubleshooting_exhausted", False),
        "model_can_auto_reply": classification.get("model_can_auto_reply", False),
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