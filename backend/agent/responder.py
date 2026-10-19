from langchain_ollama import OllamaLLM


from backend.config import OLLAMA_MODEL, OLLAMA_BASE_URL


def create_responder():
    model = OllamaLLM(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    return model


def generate_response(model, ticket_text, context):
    prompt = f"""
You are a customer support assistant.

Write a helpful and professional response to the customer.

Use ONLY the information provided in the knowledge base context.

Do not invent policies, procedures, refund rules, timelines,
or other information that is not contained in the knowledge base.

Knowledge Base:
{context}

Customer Ticket:
{ticket_text}

Write only the customer-facing response.

At the end, write "(This email is auto-generated. If this does not resolve your issue, please reply to this email and we will assist you further.)"
"""

    response = model.invoke(prompt)

    return response
