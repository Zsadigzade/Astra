# USD currency, simulated payments only — design

Date: 2026-10-09 · Approved in chat by Ziya

## Intent

Masumi payments are unavailable (provider-side issue). Astra works with SIMULATED
transactions only, and every cost, price, limit, budget and balance is in US dollars at
realistic prices instead of tADA.

## Decisions

1. **Unit.** Money stays a plain float in APIs, env variable names and DB columns; the unit
   is USD. Display format `$70`, `$115.5` (Python `f"${x:g}"`; one frontend formatter).
2. **Amounts (×10 of the tADA values).**

   | Item | tADA | USD |
   |---|---|---|
   | `GUARD_CAP` default | 10 | 100 |
   | `GUARD_APPROVAL_OVER` default | 8 | 80 |
   | Task budget default / maximum | 20 / 1000 | 200 / 10000 |
   | Viktor opening ask `SELLER_OPENING_ASK` | 18 | 180 |
   | Viktor floor `SELLER_FLOOR` (approval-path value) | 7 (9) | 70 (90) |
   | Act 2 con price | 25 | 250 |
   | Max opening offer / raise per round | 5 / 1 | 50 / 10 |
   | Simulated buyer wallet / top-up threshold | 100 / 20 | 1000 / 200 |

   Root `.env` gets `GUARD_CAP=100`, `GUARD_APPROVAL_OVER=80`, `SELLER_FLOOR=70` (only those
   lines). Integer halfway rounding may make mid-haggle prices differ from exact ×10 copies;
   outcomes (honest accepts $70, con $250 blocked, approval above $80) are unchanged.
3. **Agents.** Max and Viktor prompts and scripted lines speak in US dollars.
4. **Old data.** Default stores become `backend/data/buyer-usd.db` and `seller-usd.db`; old
   tADA files are left untouched. The ledger binds `currency=USD` in `ledger_metadata`
   (same pattern as `bind_payment_mode`). A ledger with payment activity and no currency
   record is legacy tADA: startup refuses with a message to use a separate `LEDGER_PATH`.
5. **Masumi dormant.** `PAYMENTS_MODE=masumi` is rejected at startup ("Masumi payments are
   disabled; use simulated"). Adapter/client code stays. End-to-end Masumi tests are skipped
   as dormant; adapter-level tests keep running. README, `.env.example`, doctor/readiness stop
   advertising Masumi.

## Out of scope

Recorded video/MP4, deck (`the-haggle.html`), `video/*` and historical memory entries:
they describe the recorded tADA take. A note records the switch.

## Testing

TDD for USD guard reasons, currency binding and Masumi rejection. Update tests asserting
tADA strings or amounts. Full backend and frontend suites, frontend build, Astra.exe smoke.

## Risk

Another session is editing `seller/persona.py`, `seller/app.py` and tests concurrently;
re-read files before each edit and report any overlap.
