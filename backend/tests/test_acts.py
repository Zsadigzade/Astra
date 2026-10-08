"""The four demo acts, end to end over HTTP (seller mounted in-process), SIMULATED money."""

import asyncio

import httpx
import pytest

from app.buyer.app import create_app as create_buyer
from app.buyer.events import EventBus
from app.buyer.ledger import Ledger
from app.core.config import Settings
from app.core.models import TaskCreate
from app.seller.app import create_app as create_seller


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def run_task(tmp_path, demo_mode, approve=None, settings=None):
    s = settings or Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                             seller_url="http://seller")
    seller_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_seller(s)), base_url="http://seller")
    buyer = create_buyer(s, http=seller_http)
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            r = await c.post("/tasks", json={"demo_mode": demo_mode})
            deal_id = r.json()["deal_id"]
            final = {"released", "refunded", "walked_away", "error"}
            for _ in range(500):
                types = [e.type for e in buyer.state.bus.history]
                if "needs_approval" in types and approve is not None and "approved" not in types:
                    await c.post(f"/approvals/{deal_id}", json={"approve": approve})
                if final & set(types):
                    break
                await asyncio.sleep(0.01)
            bal = (await c.get("/balances")).json()
    await seller_http.aclose()
    return buyer.state.bus.history, bal


@pytest.mark.anyio
async def test_act1_deal_settles_at_7_and_releases(tmp_path):
    events, bal = await run_task(tmp_path, "honest")
    types = [e.type for e in events]
    assert "quote" in types and "released" in types and "error" not in types
    assert next(e for e in events if e.type == "quote").data["price"] == 7
    assert (bal["buyer"], bal["seller"], bal["escrow"]) == (93, 7, 0)
    assert all(e.simulated for e in events)


@pytest.mark.anyio
@pytest.mark.parametrize("crash", [False, True])
async def test_crash_rehearsal_label_survives_replay(tmp_path, monkeypatch, crash):
    s = Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                 crash_after_lock=crash)
    buyer = create_buyer(s)
    async with buyer.router.lifespan_context(buyer):
        # Record the task without executing os._exit or calling external services.
        monkeypatch.setattr(buyer.state.orch, "_spawn", lambda coro: coro.close())
        created = await buyer.state.orch.create_task(TaskCreate())
    replay_ledger = Ledger(s.ledger_path)
    try:
        replay = EventBus(replay_ledger, simulated=True)
        event = next(e for e in replay.history if e.deal_id == created.deal_id)
        assert event.type == "task_created"
        assert event.staged is crash
        assert event.data["demo_mode"] == "honest"
    finally:
        replay_ledger.db.close()
        buyer.state.ledger.db.close()


@pytest.mark.anyio
async def test_act2_con_is_blocked_by_cap(tmp_path):
    events, bal = await run_task(tmp_path, "con")
    types = [e.type for e in events]
    assert next(e for e in events if e.type == "quote").data["price"] == 25  # Max fell for it
    assert "blocked" in types and "escrow_locked" not in types
    assert bal["buyer"] == 100
    assert all(e.staged for e in events if e.type != "balances")


@pytest.mark.anyio
async def test_act4_junk_is_refunded(tmp_path):
    events, bal = await run_task(tmp_path, "junk")
    types = [e.type for e in events]
    assert "refunded" in types and "released" not in types
    assert bal["buyer"] == 100


@pytest.mark.anyio
async def test_approval_path(tmp_path, monkeypatch):
    s = Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                 seller_url="http://seller", guard_approval_over=6)
    events, bal = await run_task(tmp_path, "honest", approve=True, settings=s)
    types = [e.type for e in events]
    assert types.index("needs_approval") < types.index("approved") < types.index("released")
    assert bal["seller"] == 7
