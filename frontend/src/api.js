/**
 * API CLIENT - every call to the backend goes through here.
 *
 * WHY ONE FILE
 *   When the backend moves from localhost to a deployed URL, one line changes.
 *   Nothing else in the app knows where the server is.
 *
 * credentials: "include"
 *   Needed so the session cookie travels with the request once login exists.
 *   In production the frontend and API sit on different domains, which is why
 *   the server must set SameSite=None - see DEPLOYMENT section 11.
 */
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function get(path) {
  const response = await fetch(`${BASE}${path}`, { credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

export const listFunds = ({ q = "", category = "", limit = 20 } = {}) => {
  const params = new URLSearchParams({ limit });
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  return get(`/funds?${params}`);
};

export const getFund = (code) => get(`/funds/${code}`);
export const getMeter = (code, period) => get(`/funds/${code}/meter?period=${period}`);

/**
 * A request must never hang forever. Without a timeout a slow or stalled
 * backend leaves the UI showing "Thinking..." with no way out, and the person
 * assumes the product is broken - which is worse than an honest error.
 */
const ISAA_TIMEOUT_MS = 45000;

export async function askIsaa(question, fundCode) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ISAA_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(`${BASE}/isaa/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ question, fund_code: fundCode || null }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Isaa took too long to answer. Please try again.");
    }
    throw new Error("Could not reach the server. Is the API running?");
  } finally {
    clearTimeout(timer);
  }

  const body = await response.json().catch(() => ({}));

  if (response.status === 429) {
    const seconds = Number(response.headers.get("Retry-After")) || null;
    const error = new Error(body.detail || "Isaa is busy. Please wait a moment.");
    error.retryAfter = seconds;
    throw error;
  }
  if (!response.ok) throw new Error(body.detail || "Isaa is unavailable right now.");
  return body;
}
