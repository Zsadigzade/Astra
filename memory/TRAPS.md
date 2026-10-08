# Traps — append only

Format: `- YYYY-MM-DD HH:MM · who · <symptom>. Cause: <cause>. Fix/avoid: <how>.`

- 2026-10-08 17:15 · ziya · Venue Wi-Fi may block non-standard ports. Fix/avoid: keep a phone hotspot ready; prefer HTTPS 443 endpoints.
- 2026-10-08 20:10 · ziya · No OpenAI access yet, but the stack (Agents SDK, LLM verifier, research seller) needs it. Cause: partner credits not redeemed. Fix/avoid: get the credit code redeemed first; until then code against `MODEL` env var, keep verifier behind an interface so it can be mocked.
- 2026-10-08 20:10 · ziya · `.env` `MASUMI_PAYMENT_URL` still `http://localhost:3001/api/v1` (nothing listening). Cause: Railway URL not pasted yet. Fix/avoid: paste hosted URL ending in `/api/v1`, then check `/health`.
