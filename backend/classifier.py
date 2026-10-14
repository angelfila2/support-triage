import json
import re

from langchain_ollama import OllamaLLM


SLA_MAP = {
    "SEV1": "4 hours",
    "SEV2": "1 day",
    "SEV3": "3 days",
    "SEV4": "4 days",
    "SEV5": "5 days",
}

VALID_CATEGORIES = {
    "password_reset",
    "billing_question",
    "shipping_delay",
    "login_issues",
    "other",
}


try:
    from config import OLLAMA_MODEL, OLLAMA_BASE_URL
except ImportError:
    OLLAMA_MODEL = "llama3.2"
    OLLAMA_BASE_URL = "http://localhost:11434"


def create_classifier():
    model = OllamaLLM(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        format="json",
        temperature=0,
    )
    return model


def _extract_json(raw_text: str) -> dict:
    """Robustly extracts JSON even if enclosed in markdown code fences or conversational text."""
    raw_text = raw_text.strip()

    # Direct parse attempt
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Extract JSON inside markdown code blocks ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Extract first outer curly braces { ... }
    match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON from classifier output: {raw_text[:200]}")


def classify_ticket(model, ticket_text, context):
    prompt = f"""
You are a customer support ticket classifier.

Analyse the customer ticket using the provided knowledge base context.
All reasoning must strictly follow the knowledge base.

Knowledge Base:
{context}

Customer Ticket:
{ticket_text}

Available categories:
- password_reset
- billing_question
- shipping_delay
- login_issues
- other


Determine:
1. category
2. urgency
3. confidence
4. a short reason for the classification


CATEGORY RULES

The category must be exactly one of:
- password_reset
- billing_question
- shipping_delay
- login_issues
- other

Choose the category that best represents the customer's actual issue.


SEVERITY RULES

Severity must be exactly one of:
- SEV1
- SEV2
- SEV3
- SEV4
- SEV5

Classify severity based on the impact, scope, and urgency of the issue.

### SEV1 — Critical: Complete service failure, widespread outage, major security breach.
### SEV2 — High: Major disruption, multiple users impacted, no immediate workaround.
### SEV3 — Medium: Standard functional bug or individual login issue after normal troubleshooting.
### SEV4 — Low: Minor issue, cosmetic bug, general questions with easy workaround.
### SEV5 — Informational: General inquiry, how-to, documentation or feature requests.

URGENCY RULES
Always return exactly one of: SEV1, SEV2, SEV3, SEV4, SEV5.

CONFIDENCE RULES
Confidence must be an integer from 0 to 100 representing certainty in the category and severity.

OUTPUT RULES
Return ONLY valid JSON matching this exact structure:
{{
    "category": "password_reset",
    "urgency": "SEV3",
    "confidence": 95,
    "reason": "Short explanation of the category and severity."
}}
"""

    response = model.invoke(prompt)
    result = _extract_json(response)

    # Normalize category (converts 'login issues' to 'login_issues')
    raw_category = str(result.get("category", "other")).strip().lower().replace(" ", "_")
    result["category"] = raw_category if raw_category in VALID_CATEGORIES else "other"

    # Normalize urgency
    urgency = str(result.get("urgency", "SEV3")).strip().upper()
    if urgency not in SLA_MAP:
        urgency = "SEV3"
    result["urgency"] = urgency

    # Normalize confidence as an integer between 0 and 100
    try:
        result["confidence"] = max(0, min(100, int(result.get("confidence", 50))))
    except (ValueError, TypeError):
        result["confidence"] = 50

    result["reason"] = str(result.get("reason", "No reason provided.")).strip()
    result["sla"] = SLA_MAP[urgency]

    return result