# USD Currency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every cost, price, limit, budget and balance is in US dollars at ×10 realistic amounts; payments are SIMULATED only.

**Architecture:** Money stays a float; one backend formatter (`app/core/money.py: usd`) and one frontend formatter (`formatters.js: usd`) render `$70`. Defaults scale ×10. Ledger binds `currency=USD`; defaults move to fresh `-usd` stores. `PAYMENTS_MODE=masumi` is rejected; Masumi code stays dormant.

**Tech Stack:** Python 3.13 / FastAPI / pytest (backend, `backend/.venv`), React + Vite + node:test (frontend).

**Spec:** `docs/superpowers/specs/2026-10-09-usd-currency-design.md`

## Global Constraints

- Display format: `f"${x:g}"` in Python; `usd(v, digits)` → `$` + `fmt(v, digits)` in JS; `-` for null.
- Amounts: cap 100, approval 80, budget default 200 / max 10000, Viktor ask 180, floor 70 (approval path 90), con 250, Max opens 50 / +10, wallet 1000 / top-up below 200.
- Root `.env`: change only `GUARD_CAP=100`, `GUARD_APPROVAL_OVER=80`, `SELLER_FLOOR=70` (and their comments).
- No commits (user rule). Re-read files before editing: another session edits `seller/*` and tests.
- Out of scope: `video/*`, `the-haggle.html`, recorded MP4, historical memory entries.

## Review Focus

- Old tADA ledger at `LEDGER_PATH`: startup refuses with a clear message, never shows `$7` deals → Task 4 test.
- `PAYMENTS_MODE=masumi` in a stale `.env`: startup error names "simulated" → Task 5 test.
- Fractional dollar amounts (`$115.5`) render without trailing zeros in both UIs → Task 1 / Task 6 tests.
- Runtime controls: cap slider ceiling equals server ceiling ($100); approval cannot exceed cap → existing test_controls, values updated in Task 2.
- Running services keep old code: restart after implementation → Task 7.

---

### Task 1: Backend USD formatter and guard/controls reasons

**Files:** Create `backend/app/core/money.py`; Modify `backend/app/buyer/guard.py:53-58`, `backend/app/buyer/controls.py:55`; Test `backend/tests/test_guard.py`.

**Produces:** `usd(amount: float) -> str`.

- [ ] Step 1: failing tests in `test_guard.py`:
```python
from app.core.money import usd

def test_usd_formats_whole_and_fractional_dollars():
    assert (usd(70), usd(115.5), usd(0.25)) == ("$70", "$115.5", "$0.25")

def test_guard_reasons_are_in_dollars():
    guard, _, _ = make_guard()
    guard.cap, guard.approval_over = 100, 80
    assert guard.evaluate(250, "t-1", 200).reason == "$250 is over the hard cap of $100"
    assert guard.evaluate(90, "t-1", 200).reason == "$90 is over the approval line of $80"
    assert guard.evaluate(70, "t-1", 50).reason == "$70 would exceed task budget $50 (spent $0)"
```
- [ ] Step 2: run `.venv/Scripts/python.exe -m pytest -q tests/test_guard.py` → FAIL (no module).
- [ ] Step 3: `money.py`: `def usd(amount: float) -> str: return f"${amount:g}"`; guard reasons use `usd(...)`; controls message `f"... ceiling of {usd(self.s.guard_cap)}"`.
- [ ] Step 4: tests pass.

### Task 2: ×10 amounts

**Files:** `backend/app/core/config.py:62-64`, `backend/app/core/models.py:62` (`default=200, le=10000`), `backend/app/seller/persona.py:27-29` (`18→180`, `7→70`, `CON_PRICE=250.0`), `backend/app/buyer/negotiator.py:21-22` (`50.0`, `10.0`), `backend/app/buyer/payments.py:17-18` (`1000.0`, `200.0`), `backend/app/judge.py:80`, `backend/scripts/{judge,rehearse,llm_check}.py` (env/expected numbers ×10, `SELLER_FLOOR "9"→"90"`), `frontend` none here, `.env`, `.env.example`.

- [ ] Step 1: change defaults; run full backend suite; collect failures.
- [ ] Step 2: update failing test literals by the same ×10 rule (prices, caps, budgets, balances: wallet 100→1000, e.g. `(93, 7, 0)` with default wallet becomes `(930, 70, 0)` only where the test relies on defaults). Tests that pass explicit amounts keep them.
- [ ] Step 3: full backend suite green.

### Task 3: Agents and copy speak dollars

**Files:** `backend/app/buyer/negotiator.py` (scripted lines 62-73, prompts 80-111, `Field(description="USD")`, round summary 220-221), `backend/app/seller/persona.py` (lines 86-108, con line 95 "Your manager already approved $250", prompts 245-274), `backend/app/core/dialogue.py:49`, `backend/app/core/models.py` comments 13/89/99, `backend/app/seller/app.py:214`, `backend/scripts/llm_check.py` strings, `backend/app/buyer/ledger.py:138` docstring, `payments.py` log.

- [ ] Step 1: failing test in `tests/test_negotiator.py`: MockMax first counter message contains `"$50"` and no `"tADA"`; in `tests/test_seller_persona.py`: honest opening contains `"$180"`.
- [ ] Step 2: replace `{x:g} tADA` with `{usd(x)}`; prompts say "Prices are in US dollars (USD)" and "$50", "+$10".
- [ ] Step 3: `grep -rn "tADA" backend/app backend/scripts` returns only `core/masumi.py`; suite green.

### Task 4: Ledger currency binding and fresh stores

**Files:** `backend/app/buyer/ledger.py` (add `bind_currency`), `backend/app/buyer/app.py` (call after construction), `backend/app/core/config.py:72,112` (`buyer-usd.db`, `seller-usd.db`); Test `backend/tests/test_ledger_mode.py`.

**Produces:** `Ledger.bind_currency(currency: str = "USD") -> None` raising `LedgerSafetyError`.

- [ ] Step 1: failing tests:
```python
def test_fresh_ledger_binds_usd(tmp_path):
    ledger = Ledger(str(tmp_path / "b.db")); ledger.bind_currency()
    assert ledger.db.execute("SELECT value FROM ledger_metadata WHERE key='currency'").fetchone()[0] == "USD"

def test_legacy_tada_ledger_is_refused(tmp_path):
    ledger = Ledger(str(tmp_path / "b.db"))
    ledger.create_deal("d1", "t1", "{}", "http://s"); ledger.update("d1", status="released", price=7, escrow_ref="SIM-d1")
    with pytest.raises(LedgerSafetyError, match="tADA"):
        ledger.bind_currency()
```
- [ ] Step 2: implement: in `tx()`, create metadata table; if a `currency` row exists and differs → error; if none and any deal has `price`/`escrow_ref` or `sim_wallets` exists → error "Ledger holds tADA amounts from before the USD switch; use a separate LEDGER_PATH."; else insert.
- [ ] Step 3: buyer `create_app` calls `ledger.bind_currency()` right after `Ledger(...)`, before `make_payments` (which creates `sim_wallets`). Defaults to `-usd` files. Suite green.

### Task 5: Masumi dormant

**Files:** `backend/app/core/config.py:41-49`, `backend/tests/test_masumi.py`, `tests/test_masumi_check.py`, other tests constructing `payments_mode="masumi"` apps, `README.md`, `.env.example`, `backend/scripts/doctor.py`.

- [ ] Step 1: failing test: `Settings(payments_mode="masumi")` raises `ValueError` matching `"Masumi payments are disabled"`.
- [ ] Step 2: `__post_init__`: `if self.payments_mode != "simulated": raise ValueError("Masumi payments are disabled; PAYMENTS_MODE must be simulated")`.
- [ ] Step 3: tests that need masumi Settings: module-level `pytestmark = pytest.mark.skip(reason="Masumi payments dormant (2026-10-09)")` where whole file is Masumi; otherwise skip the individual tests. Adapter-only tests that bypass Settings validation stay.
- [ ] Step 4: docs stop advertising Masumi; suite green.

### Task 6: Frontend dollars

**Files:** `frontend/src/lib/formatters.js:4`, every importer of `tada` (AgentIdentity, ApprovalCard, DealsPanel, GhostStage, MessageBubble, OfferLadder, RecentRequests, UsageSummary, WalletGuardCard, eventLabels, eventReducer), `AgentLimits.jsx:45-55` (labels "(USD)", unit prefix `$`, cap/approval `min={5} step={5}`), `GhostStage.jsx:47` coin label `"USD"`, `WalletGuardCard.jsx:27` aria, `App.jsx:44` budget 200, `eventReducer.test.js` reasons; Test `frontend/src/lib/formatters.test.js` (new, added to `npm test` list).

- [ ] Step 1: failing test:
```js
import test from "node:test"; import assert from "node:assert/strict"; import { usd } from "./formatters.js";
test("usd formats dollars", () => { assert.equal(usd(70, 1), "$70"); assert.equal(usd(115.5, 1), "$115.5"); assert.equal(usd(null), "-"); });
```
- [ ] Step 2: `export const usd = (v, digits = 2) => (v == null ? "-" : `$${fmt(v, digits)}`);` remove `tada`; replace all imports/usages; `Range` unit prefix support (`$` before value).
- [ ] Step 3: `grep -rn "tADA\|tada" frontend/src` empty; `npm test` and `npm run build` pass.

### Task 7: Docs, memory, verification

- [ ] README money wording, `.env.example`, `memory/DECISIONS.md` + `INTERFACES.md` + `HANDOFF.md` entries, note in `video/README.md` that the recording predates the USD switch.
- [ ] Full backend + frontend suites, build, `Astra.exe` restart (R) so running services pick up new code; verify `/health` guard `{"cap":100.0,"approval_over":80.0}` and dashboard shows `$`.
