# Traps — append only

Format: `- YYYY-MM-DD HH:MM · who · <symptom>. Cause: <cause>. Fix/avoid: <how>.`

- 2026-10-08 17:15 · ziya · Venue Wi-Fi may block non-standard ports. Fix/avoid: keep a phone hotspot ready; prefer HTTPS 443 endpoints.
- 2026-10-08 20:10 · ziya · No OpenAI access yet, but the stack (Agents SDK, LLM verifier, research seller) needs it. Cause: partner credits not redeemed. Fix/avoid: get the credit code redeemed first; until then code against `MODEL` env var, keep verifier behind an interface so it can be mocked.
- 2026-10-08 20:10 · ziya · `.env` `MASUMI_PAYMENT_URL` still `http://localhost:3001/api/v1` (nothing listening). Cause: Railway URL not pasted yet. Fix/avoid: paste hosted URL ending in `/api/v1`, then check `/health`.
- 2026-10-08 21:45 · ziya · Masumi rejects `identifierFromPurchaser` unless hex, 14-26 chars. Cause: zod schema in masumi-payment-service. Fix/avoid: deal_id is 20 hex chars (no prefix); never add a `d-` prefix again.
- 2026-10-08 21:45 · ziya · Masumi `/payment-source-extended` returns and accepts wallet mnemonics. Fix/avoid: never call it from code or scripts; copy wallet vkeys from the admin UI.
- 2026-10-08 21:58 · ziya · Seller keeps jobs in memory: restarting the seller mid-deal makes the buyer's stored job 404; the deal stays resumable but cannot finish. Fix/avoid: during demos restart only the buyer (Act 3), never the seller mid-deal.
- 2026-10-08 21:58 · ziya · `SOKOSUMI_API_KEY` is a Sokosumi marketplace key (agents + jobs, no payments); it is not a Masumi payment-service key. Fix/avoid: MASUMI_API_KEY = ADMIN_KEY of our own payment node.
- 2026-10-08 22:05 · ziya · An agent wrote memory entries stamped 22:10-22:40 when the clock said 21:58. Cause: timestamps guessed, not read. Fix/avoid: run `date +%H:%M` before writing any memory entry.
