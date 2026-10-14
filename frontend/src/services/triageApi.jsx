import { API_URL } from "../config";

export async function triageTicket(subject, body) {
  const response = await fetch(`${API_URL}/api/triage`, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      subject,
      body,
    }),
  });

  if (!response.ok) {
    let message = "Failed to analyze ticket.";

    try {
      const error = await response.json();
      message = error.detail || message;
    } catch {
      // Keep default error
    }

    throw new Error(message);
  }

  return response.json();
}
