// Credentials are supplied by the operator, never bundled into the frontend.
export function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers);
  const token = sessionStorage.getItem("supportflow-token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}
