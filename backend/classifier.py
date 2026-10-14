import json

from langchain_ollama import OllamaLLM


SLA_MAP = {
    "SEV1": "4 hours",
    "SEV2": "1 day",
    "SEV3": "3 days",
    "SEV4": "4 days",
    "SEV5": "5 days",
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


def classify_ticket(model, ticket_text, context):
    prompt = f"""
You are a customer support ticket classifier.

Analyse the customer ticket using the provided
knowledge base context.

All reasoning must strictly follow the knowledge base.

Knowledge Base:
{context}

Customer Ticket:
{ticket_text}

Available categories:
- password_reset
- billing_question
- shipping_delay
- login issues
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
- login issues
- other

Choose the category that best represents the customer's actual issue.

Do not invent a category outside this list.


SEVERITY RULES

Severity must be exactly one of:

- SEV1
- SEV2
- SEV3
- SEV4
- SEV5

Classify severity based on the impact, scope, and urgency of the issue.


### SEV1 — Critical

A critical incident causing complete service failure, widespread outage,
severe security breach, data loss, or another issue that prevents most
or all users from using a critical service.

Examples:

- Entire application or production system is unavailable
- Widespread login failure affecting all or most users
- Confirmed major security breach
- Critical production data loss or corruption
- Core business operations are completely blocked


### SEV2 — High

A serious incident causing major disruption to important functionality
or affecting multiple users, but the overall service is not completely
unavailable.

Examples:

- Major feature is unavailable for many users
- Significant performance degradation affecting multiple users
- Multiple users cannot log in
- Important business operations are severely impacted
- No reasonable workaround is available


### SEV3 — Medium

An issue causing moderate impact to one or more users. Important
functionality may be impaired, but the system remains usable and a
workaround may exist.

Examples:

- A user cannot access an important feature
- Intermittent application errors
- Login issue affecting an individual user after normal troubleshooting
- Functionality is partially broken but a workaround exists
- Issue impacts normal work but does not stop critical operations


### SEV4 — Low

A minor issue with limited impact that does not significantly prevent
the user from completing their work.

Examples:

- Minor UI or display issue
- Non-critical feature behaves incorrectly
- Small inconvenience with an easy workaround
- General technical assistance request
- Issue has minimal business impact


### SEV5 — Informational

A request that does not represent a service failure or significant
technical problem.

Examples:

- General question
- How-to request
- Documentation request
- Feature information request
- Cosmetic feedback with no functional impact


URGENCY RULES

Always return exactly one of:

SEV1, SEV2, SEV3, SEV4, SEV5

Do not return values such as:

- low
- medium
- high
- critical

Do not increase or decrease severity based on whether the ticket
can be automatically answered.

Severity must represent only the impact, scope, and urgency of
the customer's issue.


CONFIDENCE RULES

Confidence must be an integer from 0 to 100.

- 0 means completely uncertain
- 100 means completely certain

Confidence represents confidence in the classification of the ticket.

Confidence must only represent confidence in the category and severity.

Do not use confidence to indicate whether an automatic reply is safe.


REASONING RULES

The reason must briefly explain why the selected category and severity
were chosen.

The reason should focus only on classification.

Do not determine whether the ticket should be automatically replied to.

Do not determine whether the ticket should be escalated.

Do not discuss whether a human needs to investigate the issue.

Do not include routing decisions in the reason.


OUTPUT RULES

Return ONLY valid JSON.

Do not include Markdown.
Do not include code fences.
Do not include text before or after the JSON.
Do not include additional fields.

Return exactly this structure:

{{
    "category": "password_reset",
    "urgency": "SEV3",
    "confidence": 95,
    "reason": "Short explanation of the category and severity."
}}
"""

    response = model.invoke(prompt)

    result = json.loads(response)

    urgency = result.get("urgency")

    if urgency not in SLA_MAP:
        raise ValueError(
            f"Invalid urgency returned by classifier: {urgency}"
        )

    result["sla"] = SLA_MAP[urgency]

    return result