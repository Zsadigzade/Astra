"""Check real subscription agents and in-memory wallet rules without moving money.

Run: uv run python scripts/llm_check.py
Requires Codex CLI signed in with ChatGPT subscription access; no API key is used.
Checks Codex even if the demo's LLM_MODE is mock. Scripted fallback always fails.
Use --agent max|viktor|both (default both). Up to two turns per agent,
each bounded by CODEX_TIMEOUT_SECONDS.
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.money import usd
from app.buyer.guard import Verdict, WalletGuard  # noqa: E402
from app.buyer.ledger import Ledger  # noqa: E402
from app.buyer.negotiator import CodexMax  # noqa: E402
from app.buyer.payments import SimulatedPayments  # noqa: E402
from app.core.config import Settings, get_settings  # noqa: E402
from app.core.models import NegotiateRequest, NegotiateResponse  # noqa: E402
from app.seller.persona import CodexViktor  # noqa: E402


def check_guard() -> bool:
    """Exercise the real guard with deterministic prices, independently of Max."""
    ledger = Ledger(":memory:")
    try:
        guard = WalletGuard(ledger, SimulatedPayments(ledger), cap=100, approval_over=80)
        cases = [
            ("ordinary offer", 70, 200, Verdict.allow),
            ("hard cap", 250, 500, Verdict.block),
            ("task budget", 70, 60, Verdict.block),
            ("human approval", 90, 200, Verdict.needs_approval),
        ]
        passed = True
        for label, amount, budget, expected in cases:
            actual = guard.evaluate(amount, "llm-check", budget).verdict
            ok = actual is expected
            print(f"{'OK' if ok else 'FAIL'}: SIMULATED in-memory guard {label}: {actual.value}")
            passed = passed and ok
        # Existing commitments must count toward the task budget as well.
        ledger.create_deal("prior", "llm-check", "{}", "in-memory")
        ledger.update("prior", status="locked", price=50, escrow_ref="SIMULATED-check")
        ok = guard.evaluate(70, "llm-check", 100).verdict is Verdict.block
        print(f"{'OK' if ok else 'FAIL'}: SIMULATED in-memory guard counts committed budget")
        return passed and ok
    finally:
        ledger.db.close()


async def check(settings: Settings) -> int:
    guard_ok = check_guard()
    max_agent = CodexMax(settings, ceiling=100)
    my_last = None
    for round_no, price in enumerate((150, 70)):
        seller = NegotiateResponse(
            deal_id="llm-check", round=round_no, action="counter", price=price,
            message=f"I can deliver 20 flats in Prague 7 under 25,000 CZK for {usd(price)}.")
        move = await max_agent.next_move(seller, my_last)
        if max_agent.last_backend != "codex":
            print(f"FAIL: Max used scripted fallback ({max_agent.fallback_reason}); subscription Codex was not verified.")
            print("Check that Codex CLI is installed and signed in with ChatGPT, then retry.")
            return 1
        print(f"OK: real subscription Codex Max round {round_no + 1}: {move.action}, {usd(move.price)}")
        if move.action != "counter":
            break
        my_last = move.price
    if not guard_ok:
        return 1
    print("PASS: real Max output and independent guard rules verified. No money moved.")
    return 0


async def check_viktor(settings: Settings) -> int:
    seller = CodexViktor(settings, floor=70, opening_ask=180)
    requests = [NegotiateRequest(deal_id="viktor-check", round=0, action="open"),
                NegotiateRequest(deal_id="viktor-check", round=1, action="counter", offer=70,
                                 message="Seventy dollars for the agreed rental data.")]
    for req in requests:
        response = await seller.respond_async(req)
        if response.backend != "codex":
            print(f"FAIL: Viktor used scripted fallback ({response.fallback_reason}); subscription output not verified.")
            return 1
        expected = "counter" if req.action == "open" else "accept"
        if (response.action != expected or response.price < 70
                or (expected == "accept" and response.price != 70)):
            print("FAIL: Viktor did not produce a valid opening and floor-price agreement.")
            return 1
        print(f"OK: real subscription Codex Viktor round {req.round + 1}: {response.action}, {usd(response.price)}")
    print("PASS: real Viktor opening and agreement verified. No money moved.")
    return 0


async def check_agents(settings: Settings, agent: str) -> int:
    if agent in {"max", "both"} and await check(settings):
        return 1
    if agent in {"viktor", "both"}:
        return await check_viktor(settings)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("max", "viktor", "both"), default="both")
    args = parser.parse_args()
    try:
        return asyncio.run(check_agents(get_settings(), args.agent))
    except Exception as exc:
        # Avoid exposing provider response bodies, generated text, or credential values.
        print(f"FAIL: LLM check could not complete ({type(exc).__name__}).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
