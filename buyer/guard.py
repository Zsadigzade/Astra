"""The wallet guard: the core idea. The AI can ask to pay; only the guard can pay.

Plain code, no LLM. Checks before any money moves:
1. deal already paid?  -> never pay twice (survives crashes via the ledger)
2. amount > hard cap?  -> BLOCK, even if the AI was talked into it
3. over task budget?   -> BLOCK
4. over approval line? -> pause until a human approves on the dashboard
"""

from dataclasses import dataclass
from enum import StrEnum

from buyer.ledger import Ledger
from buyer.payments import Payments
from shared.models import StartJobResponse


class Verdict(StrEnum):
    allow = "allow"
    needs_approval = "needs_approval"
    block = "block"


@dataclass
class Decision:
    verdict: Verdict
    reason: str


@dataclass
class PayOutcome:
    kind: str  # "locked" | "already_paid" | "blocked" | "needs_approval"
    reason: str = ""
    ref: str | None = None


class WalletGuard:
    def __init__(self, ledger: Ledger, payments: Payments, cap: float, approval_over: float):
        self.ledger = ledger
        self._payments = payments
        self.cap = cap
        self.approval_over = approval_over

    def evaluate(self, amount: float, task_id: str, budget: float, deal_id: str | None = None) -> Decision:
        if amount <= 0:
            return Decision(Verdict.block, f"amount {amount} is not positive")
        if amount > self.cap:
            return Decision(Verdict.block, f"{amount:g} tADA is over the hard cap of {self.cap:g}")
        spent = self.ledger.spent(task_id, exclude_deal=deal_id)
        if spent + amount > budget:
            return Decision(Verdict.block, f"{amount:g} tADA would exceed task budget {budget:g} (spent {spent:g})")
        if amount > self.approval_over:
            return Decision(Verdict.needs_approval, f"{amount:g} tADA is over the approval line of {self.approval_over:g}")
        return Decision(Verdict.allow, "within cap and budget")

    async def pay(
        self,
        deal_id: str,
        amount: float,
        task_id: str,
        budget: float,
        seller: str,
        start: StartJobResponse,
        approved: bool = False,
    ) -> PayOutcome:
        deal = self.ledger.get(deal_id)
        if deal and deal["escrow_ref"]:
            return PayOutcome("already_paid", "deal already in paid list", deal["escrow_ref"])

        d = self.evaluate(amount, task_id, budget, deal_id)
        if d.verdict is Verdict.block:
            return PayOutcome("blocked", d.reason)
        if d.verdict is Verdict.needs_approval and not approved:
            return PayOutcome("needs_approval", d.reason)

        # Mark intent first: a crash after this line is recovered by resume(), and the
        # adapter's lock is idempotent per deal_id, so the retry finds the money already locked.
        self.ledger.update(deal_id, status="paying", price=amount, approved=int(approved))
        res = await self._payments.lock(deal_id, amount, seller, start)
        self.ledger.update(deal_id, status="locked", escrow_ref=res.ref)
        return PayOutcome("already_paid" if res.already else "locked", "", res.ref)

    async def release(self, deal_id: str) -> None:
        await self._payments.release(deal_id)

    async def refund(self, deal_id: str) -> None:
        await self._payments.refund(deal_id)

    async def balances(self) -> dict[str, float]:
        return await self._payments.balances()
