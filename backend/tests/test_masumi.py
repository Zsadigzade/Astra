"""PAYMENTS_MODE=masumi against an in-memory fake of the Masumi payment service."""

import asyncio

import httpx
import pytest

from app.buyer.app import create_app as create_buyer
from app.buyer.guard import WalletGuard
from app.buyer.ledger import Ledger
from app.buyer.payments import MasumiPayments
from app.core.config import Settings
from app.core.masumi import input_hash, output_hash
from app.core.models import StartJobResponse
from app.seller.app import create_app as create_seller
from tests.fake_masumi import create_fake_masumi


@pytest.fixture
def anyio_backend():
    return "asyncio"


def masumi_settings(tmp_path) -> Settings:
    return Settings(payments_mode="masumi", masumi_payment_url="http://masumi", masumi_api_key="test-key",
                    masumi_agent_id="agent-" + "a" * 60, seller_vkey="b" * 56, masumi_poll_seconds=0.01,
                    ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                    seller_url="http://seller")


def test_hashes_match_mip004_shape():
    assert input_hash({"b": 1, "a": "x"}, "abc") == input_hash({"a": "x", "b": 1}, "abc")
    assert len(output_hash("result", "abc")) == 64


@pytest.mark.anyio
async def test_act1_real_flow_on_fake_masumi(tmp_path):
    s = masumi_settings(tmp_path)
    fake = create_fake_masumi()
    masumi_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=fake))
    seller = create_seller(s, masumi_http=masumi_http)
    seller_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=seller), base_url="http://seller")
    buyer = create_buyer(s, http=seller_http, masumi_http=masumi_http)
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            await c.post("/tasks", json={"demo_mode": "honest"})
            for _ in range(500):
                if {"released", "refunded", "error"} & {e.type for e in buyer.state.bus.history}:
                    break
                await asyncio.sleep(0.01)
    events = {e.type: e for e in buyer.state.bus.history}
    assert "error" not in events, events.get("error")
    assert not events["escrow_locked"].simulated
    assert events["escrow_locked"].data["tx_url"].startswith("https://preprod.cardanoscan.io/transaction/")
    assert events["released"].data["release"] == "scheduled"
    assert events["released"].data["on_chain_state"] == "ResultSubmitted"
    (purchase,) = fake.state.purchases.values()
    assert purchase["Amounts"] == [{"amount": "7000000", "unit": ""}]
    await masumi_http.aclose()
    await seller_http.aclose()


@pytest.mark.anyio
async def test_act3_lock_twice_pays_once(tmp_path):
    s = masumi_settings(tmp_path)
    fake = create_fake_masumi()
    masumi_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=fake))
    payments = MasumiPayments(s, Ledger(":memory:"), masumi_http)
    deal_id = "0123456789abcdef0123"
    pay = await payments.client.create_payment(s.masumi_agent_id, "c" * 64, deal_id, 7, 20, 40)
    start = StartJobResponse(status="success", job_id="j-1", price=7, agentIdentifier=s.masumi_agent_id,
                             sellerVKey=s.seller_vkey, inputHash="c" * 64,
                             **{k: pay[k] for k in ("blockchainIdentifier", "payByTime", "submitResultTime",
                                                    "unlockTime", "externalDisputeUnlockTime")})
    first = await payments.lock(deal_id, 7, "seller", start)
    second = await payments.lock(deal_id, 7, "seller", start)  # buyer restarted mid-deal
    assert (first.already, second.already) == (False, True)
    assert len(fake.state.purchases) == 1
    await masumi_http.aclose()


@pytest.mark.anyio
async def test_lost_purchase_reply_is_recorded_under_a_lower_cap(tmp_path):
    s = masumi_settings(tmp_path)
    fake = create_fake_masumi()
    masumi_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=fake))
    ledger = Ledger(":memory:")
    payments = MasumiPayments(s, ledger, masumi_http)
    deal_id = "0123456789abcdef0123"
    ledger.create_deal(deal_id, "t-1", "{}", "http://seller")
    pay = await payments.client.create_payment(s.masumi_agent_id, "c" * 64, deal_id, 7, 20, 40)
    start = StartJobResponse(status="success", job_id="j-1", price=7, agentIdentifier=s.masumi_agent_id,
                             sellerVKey=s.seller_vkey, inputHash="c" * 64,
                             **{k: pay[k] for k in ("blockchainIdentifier", "payByTime", "submitResultTime",
                                                    "unlockTime", "externalDisputeUnlockTime")})
    await payments.lock(deal_id, 7, "seller", start)  # purchase accepted on chain, reply lost
    ledger.update(deal_id, status="paying", price=7)
    guard = WalletGuard(ledger, payments, cap=5, approval_over=4)  # limits lowered before restart
    out = await guard.pay(deal_id, 7, "t-1", 20, "seller", start)
    assert (out.kind, out.ref) == ("already_paid", pay["blockchainIdentifier"])
    assert out.info["on_chain_state"] == "FundsLocked"
    assert ledger.get(deal_id)["escrow_ref"] == pay["blockchainIdentifier"]
    assert len(fake.state.purchases) == 1
    await masumi_http.aclose()
