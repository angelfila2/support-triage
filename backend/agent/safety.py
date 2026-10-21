"""Detect explicit instruction override/exfiltration attempts, not topic words."""

import re
import unicodedata

PATTERNS = [
    r"\b(?:ignore|disregard|forget|override|bypass)\b.{0,65}\b(?:instructions?|rules?|polic(?:y|ies)|system message|developer message)\b",
    r"\b(?:reveal|print|show|dump|repeat|expose|extract)\b.{0,60}\b(?:system prompt|developer message|your instructions|api keys?|secrets?)\b",
    r"\b(?:act as|you are now|pretend to be)\b.{0,45}\b(?:system|developer|administrator|unrestricted)\b",
    r"(?:<\|(?:system|im_start)\|>|\[system\])",
]


def check_prompt_injection(ticket_text):
    if not isinstance(ticket_text, str) or not ticket_text.strip() or len(ticket_text) > 20502:
        return True
    text = unicodedata.normalize("NFKC", ticket_text)
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    text = re.sub(r"\s+", " ", text).lower()
    return any(re.search(pattern, text) for pattern in PATTERNS)
