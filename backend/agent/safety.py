
#guard against prompt injection attacks
def check_prompt_injection(ticket_text):
    suspicious_phrases = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "ignore your instructions",
        "system prompt",
        "developer message",
        "reveal your instructions",
        "forget your instructions"
    ]

    ticket_text = ticket_text.lower()

    for phrase in suspicious_phrases:
        if phrase in ticket_text:
            return True

    return False