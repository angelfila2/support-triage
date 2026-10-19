def route_ticket(classification: dict, is_suspicious: bool) -> str:
    """
    Determines whether a ticket can be automatically answered or must be escalated.

    Escalation Rules:
    1. Suspicious content / Prompt injection -> Always ESCALATE.
    2. Critical & High incidents (SEV1, SEV2) -> Always ESCALATE (strict SLA policy).
    3. Low confidence (< 80%) -> Always ESCALATE.
    4. Knowledge base cannot definitively resolve issue -> Always ESCALATE.
    5. Only SEV3, SEV4, SEV5 tickets with high confidence and verified FAQ resolution
       are eligible for AUTO_REPLY.
    """
    if is_suspicious:
        return "ESCALATE"

    # Enforce strict policy: SEV1 and SEV2 incidents must NEVER be auto-replied
    urgency = str(classification.get("urgency", "")).strip().upper()
    if urgency in {"SEV1", "SEV2"}:
        return "ESCALATE"

    if classification.get("confidence", 0) < 80:
        return "ESCALATE"

    if not classification.get("can_auto_reply", False):
        return "ESCALATE"

    return "AUTO_REPLY"