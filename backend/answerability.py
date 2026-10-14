import json
import re

from langchain_ollama import OllamaLLM


try:
    from config import OLLAMA_MODEL, OLLAMA_BASE_URL
except ImportError:
    OLLAMA_MODEL = "llama3.2"
    OLLAMA_BASE_URL = "http://localhost:11434"


def create_answerability_checker():
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

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON from answerability output: {raw_text[:200]}")


def check_answerability(model, ticket_text, context) -> bool:
    prompt = f"""
You are an answerability checker for a customer support system.

Your ONLY job is to determine whether the customer can be given a
useful next response using ONLY the provided knowledge base context.

Knowledge Base:
{context}

Customer Ticket:
{ticket_text}


ANSWERABILITY RULES

Set can_auto_reply to true when the knowledge base contains a
documented answer, troubleshooting procedure, or next step that
reasonably applies to the customer's issue.

Set can_auto_reply to false when:
- the knowledge base contains no relevant answer or procedure
- the customer has already tried the troubleshooting procedure provided
- resolving the issue requires human investigation or access to accounts/databases
- answering would require unsupported assumptions

OUTPUT RULES
Return ONLY valid JSON matching exactly:
{{
    "can_auto_reply": true
}}
"""

    try:
        response = model.invoke(prompt)
        result = _extract_json(response)
        return bool(result.get("can_auto_reply", False))
    except Exception as error:
        # Safe failure mode: If checking answerability fails, safely escalate to human review
        print(f"Warning: Answerability check failed to parse ({error}). Defaulting to ESCALATE.")
        return False