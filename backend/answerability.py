import json

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


def check_answerability(model, ticket_text, context):
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

The customer's issue does NOT need to contain every technical detail.

The root cause does NOT need to be known.

If the customer's issue matches a troubleshooting procedure in the
knowledge base and the customer has not indicated that they already
completed that procedure, can_auto_reply should be true.

For example:

If the customer reports that they cannot log in and the knowledge base
contains login troubleshooting steps, can_auto_reply should be true.

The automatic response can provide those documented troubleshooting
steps.


Set can_auto_reply to false when:

- the knowledge base contains no relevant answer or procedure
- the customer's issue does not reasonably match the provided
  knowledge base
- the customer has already tried the troubleshooting procedure
  provided by the knowledge base and the issue still persists
- the knowledge base explicitly says the issue should be escalated
  after the steps the customer has already attempted
- resolving the issue requires human investigation
- resolving the issue requires access to accounts, systems, logs,
  databases, orders, payments, or other unavailable information
- answering would require unsupported assumptions


ESCALATION RULE

If the knowledge base provides troubleshooting steps followed by an
instruction to escalate if those steps fail:

- return can_auto_reply=true if the customer has NOT yet indicated
  that they completed those troubleshooting steps

- return can_auto_reply=false if the customer states that they already
  completed those troubleshooting steps and the problem still persists


IMPORTANT

Do not treat the existence of a possible future escalation as a reason
to immediately set can_auto_reply=false.

If the knowledge base provides troubleshooting steps that should be
attempted before escalation, those steps are a valid automatic reply.


OUTPUT RULES

Return ONLY valid JSON.

Do not include Markdown.
Do not include code fences.
Do not include text before or after the JSON.

Return exactly:

{{
    "can_auto_reply": true
}}
"""

    response = model.invoke(prompt)

    result = json.loads(response)

    return result["can_auto_reply"]