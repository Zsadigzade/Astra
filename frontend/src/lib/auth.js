// Buyer access token helpers (API_TOKEN on the buyer, VITE_API_TOKEN in the dashboard build).
// Fetches send the X-API-Token header; EventSource and <audio src> cannot set headers, so their
// URLs carry ?token= instead. An empty token leaves everything unchanged (open local development).

export function authHeaders(token, headers = {}) {
  return token ? { ...headers, "X-API-Token": token } : headers;
}

export function withToken(url, token) {
  if (!token || !url) return url;
  const hash = url.indexOf("#");
  const base = hash === -1 ? url : url.slice(0, hash);
  const fragment = hash === -1 ? "" : url.slice(hash);
  const sep = base.includes("?") ? "&" : "?";
  return `${base}${sep}token=${encodeURIComponent(token)}${fragment}`;
}
