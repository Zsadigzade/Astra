export const BUYER = import.meta.env.VITE_BUYER_URL ?? "http://localhost:8000";
export const SELLER = import.meta.env.VITE_SELLER_URL ?? "http://localhost:8001";

async function call(path, method = "GET", body) {
  const res = await fetch(`${BUYER}${path}`, {
    method,
    headers: body ? { "content-type": "application/json" } : undefined,
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
  startTask: (task) => call("/tasks", "POST", task),
  decide: (dealId, approve) => call(`/approvals/${dealId}`, "POST", { approve }),
};
