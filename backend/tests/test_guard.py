import pytest

from app.buyer.guard import Verdict, WalletGuard
from app.buyer.ledger import Ledger
from app.buyer.payments import SimulatedPayments
from app.core.models import StartJobResponse

START = StartJobResponse(status="success", job_id="j-1", price=7)


def make_guard():
    ledger = Ledger(":memory:")
    ledger.create_deal("d-1", "t-1", "{}", "http://seller")
    payments = SimulatedPayments(ledger)
    return WalletGuard(ledger, payments, cap=10, approval_over=8), ledger, payments


@pytest.mark.parametrize("amount,verdict", [(7, Verdict.allow), (9, Verdict.needs_approval),
                                            (25, Verdict.block), (0, Verdict.block)])
def test_evaluate(amount, verdict):
    guard, _, _ = make_guard()
    assert guard.evaluate(amount, "t-1", budget=20).verdict is verdict


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["amount", "budget", "cap", "approval_over"])
def test_nonfinite_money_or_limits_cannot_bypass_guard(field, value):
    guard, _, _ = make_guard()
    amount, budget = 7, 20
    if field == "amount":
        amount = value
    elif field == "budget":
        budget = value
    else:
        setattr(guard, field, value)
    assert guard.evaluate(amount, "t-1", budget).verdict is Verdict.block


@pytest.mark.anyio
async def test_cap_blocks_even_when_asked_to_pay():
    guard, _, payments = make_guard()
    out = await guard.pay("d-1", 25, "t-1", 20, "seller", START)
    assert out.kind == "blocked"
    assert (await payments.balances())["buyer"] == 100


@pytest.mark.anyio
async def test_never_pays_twice():
    guard, _, payments = make_guard()
    first = await guard.pay("d-1", 7, "t-1", 20, "seller", START)
    second = await guard.pay("d-1", 7, "t-1", 20, "seller", START)
    assert (first.kind, second.kind) == ("locked", "already_paid")
    assert (await payments.balances())["buyer"] == 93


@pytest.mark.anyio
async def test_crash_between_intent_and_record_does_not_double_pay():
    guard, ledger, payments = make_guard()
    await payments.lock("d-1", 7, "seller", START)  # money moved, then process died before ledger update
    ledger.update("d-1", status="paying", price=7)
    out = await guard.pay("d-1", 7, "t-1", 20, "seller", START)
    assert out.kind == "already_paid"
    assert (await payments.balances())["buyer"] == 93


@pytest.mark.anyio
async def test_funded_paying_deal_is_recorded_even_under_a_lower_cap():
    # The lock moved money under the old limits, then its reply was lost. A lower cap now must
    # not block the deal: that would strand escrow the ledger no longer knows about.
    guard, ledger, payments = make_guard()
    await payments.lock("d-1", 7, "seller", START)
    ledger.update("d-1", status="paying", price=7)
    guard.cap = 5
    out = await guard.pay("d-1", 7, "t-1", 20, "seller", START)
    assert (out.kind, out.ref) == ("already_paid", "SIM-d-1")
    deal = ledger.get("d-1")
    assert (deal["status"], deal["escrow_ref"]) == ("locked", "SIM-d-1")
    assert ledger.spent("t-1") == 7
    assert (await payments.balances())["buyer"] == 93


@pytest.mark.anyio
async def test_unfunded_paying_deal_obeys_the_current_cap():
    guard, ledger, payments = make_guard()
    ledger.update("d-1", status="paying", price=7)  # intent recorded, lock never reached the wallet
    guard.cap = 5
    out = await guard.pay("d-1", 7, "t-1", 20, "seller", START)
    assert out.kind == "blocked"
    assert (await payments.balances())["buyer"] == 100


@pytest.fixture
def anyio_backend():
    return "asyncio"
