import { authHeaders } from "./lib/auth.js";

export const BUYER = import.meta.env.VITE_BUYER_URL ?? "http://localhost:8000";
export const SELLER = import.meta.env.VITE_SELLER_URL ?? "http://localhost:8001";
// Buyer API_TOKEN, injected by scripts/dev.mjs from the root .env. Empty = open local buyer.
export const API_TOKEN = import.meta.env.VITE_API_TOKEN ?? "";

async function call(path, method = "GET", body) {
  const res = await fetch(`${BUYER}${path}`, {
    method,
    headers: authHeaders(API_TOKEN, body ? { "content-type": "application/json" } : {}),
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* non-JSON error body */ }
  if (!res.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `${method} ${path} failed (${res.status})`);
  return data;
}

export const api = {
  controls: () => call("/controls"),
  updateControls: (patch) => call("/controls", "PUT", patch),
  parseRequest: (text) => call("/requests/parse", "POST", { text }),
  startTask: (task) => call("/tasks", "POST", task),
  decide: (dealId, approve) => call(`/approvals/${dealId}`, "POST", { approve }),
};
