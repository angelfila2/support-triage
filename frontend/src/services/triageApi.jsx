import { apiFetch } from "./apiFetch";
import { API_URL } from "../config";

export async function triageTicket(subject, body) {
  const response = await apiFetch(`${API_URL}/api/triage`, {
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
      message =
        typeof error.detail === "string"
          ? error.detail
          : Array.isArray(error.detail)
            ? error.detail.map((item) => item.msg).join("; ")
          : error.detail?.message
            ? `${error.detail.message} Ticket ID: ${error.detail.ticket_id}`
            : message;
    } catch {
      // Keep default error
    }

    throw new Error(message);
  }

  return response.json();
}
