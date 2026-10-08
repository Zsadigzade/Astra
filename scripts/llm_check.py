"""Check real Max output and in-memory wallet rules without moving money.

Run: uv run python scripts/llm_check.py
Requires OPENAI_API_KEY in .env; uses MODEL even if the demo's LLM_MODE is mock.
Exit 0 requires real LLM output: scripted fallbacks always fail this check.
Up to two provider requests, bounded to 20 seconds per turn; tracing is disabled.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from buyer.guard import Verdict, WalletGuard  # noqa: E402
from buyer.ledger import Ledger  # noqa: E402
from buyer.negotiator import OpenAIMax  # noqa: E402
from buyer.payments import SimulatedPayments  # noqa: E402
from shared.config import Settings, get_settings  # noqa: E402
from shared.models import NegotiateResponse  # noqa: E402


def check_guard() -> bool:
    """Exercise the real guard with deterministic prices, independently of Max."""
    ledger = Ledger(":memory:")
    try:
        guard = WalletGuard(ledger, SimulatedPayments(ledger), cap=10, approval_over=8)
        cases = [
            ("ordinary offer", 7, 20, Verdict.allow),
            ("hard cap", 25, 50, Verdict.block),
            ("task budget", 7, 6, Verdict.block),
            ("human approval", 9, 20, Verdict.needs_approval),
        ]
        passed = True
        for label, amount, budget, expected in cases:
            actual = guard.evaluate(amount, "llm-check", budget).verdict
            ok = actual is expected
            print(f"{'OK' if ok else 'FAIL'}: SIMULATED in-memory guard {label}: {actual.value}")
            passed = passed and ok
        # Existing commitments must count toward the task budget as well.
        ledger.create_deal("prior", "llm-check", "{}", "in-memory")
        ledger.update("prior", status="locked", price=5, escrow_ref="SIMULATED-check")
        ok = guard.evaluate(7, "llm-check", 10).verdict is Verdict.block
        print(f"{'OK' if ok else 'FAIL'}: SIMULATED in-memory guard counts committed budget")
        return passed and ok
    finally:
        ledger.db.close()


async def check(settings: Settings) -> int:
    guard_ok = check_guard()
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("FAIL: OPENAI_API_KEY is missing; put it in .env. No provider request made.")
        return 1
    max_agent = OpenAIMax(settings, ceiling=10, tracing_disabled=True)
    my_last = None
    for round_no, price in enumerate((15, 7)):
        seller = NegotiateResponse(
            deal_id="llm-check", round=round_no, action="counter", price=price,
            message=f"I can deliver 20 flats in Prague 7 under 25,000 CZK for {price} tADA.")
        move = await max_agent.next_move(seller, my_last)
        if max_agent.last_backend != "openai":
            print(f"FAIL: Max used scripted fallback ({max_agent.fallback_reason}); live LLM was not verified.")
            return 1
        print(f"OK: real OpenAI Max round {round_no + 1}: {move.action}, {move.price:g} tADA")
        if move.action != "counter":
            break
        my_last = move.price
    if not guard_ok:
        return 1
    print("PASS: real Max output and independent guard rules verified. No money moved.")
    return 0


def main() -> int:
    try:
        return asyncio.run(check(get_settings()))
    except Exception as exc:
        # Avoid exposing provider response bodies, generated text, or credential values.
        print(f"FAIL: LLM check could not complete ({type(exc).__name__}).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
