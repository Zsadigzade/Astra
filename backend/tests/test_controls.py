"""Dashboard operator controls: tighten-only guard limits, pause switch, round limit."""

import asyncio

import httpx
import pytest

from app.buyer.app import create_app as create_buyer
from app.core.config import Settings
from app.seller.app import create_app as create_seller


@pytest.fixture
def anyio_backend():
    return "asyncio"


def settings(tmp_path, **kw):
    return Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                    seller_url="http://seller", **kw)


async def client(tmp_path):
    buyer = create_buyer(settings(tmp_path), http=httpx.AsyncClient())
    return buyer, httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer")


@pytest.mark.anyio
async def test_snapshot_reports_limits_and_modes(tmp_path):
    buyer, c = await client(tmp_path)
    async with buyer.router.lifespan_context(buyer), c:
        snap = (await c.get("/controls")).json()
    assert snap["guard"] == {"cap": 10, "approval_over": 8, "cap_ceiling": 10}
    assert snap["paused"] is False and snap["modes"]["simulated"] is True


@pytest.mark.anyio
async def test_guard_can_be_tightened_but_never_loosened_past_env_cap(tmp_path):
    buyer, c = await client(tmp_path)
    async with buyer.router.lifespan_context(buyer), c:
        ok = await c.put("/controls", json={"guard_cap": 6, "guard_approval_over": 5})
        assert ok.status_code == 200 and buyer.state.guard.cap == 6 and buyer.state.guard.approval_over == 5
        assert (await c.put("/controls", json={"guard_cap": 50})).status_code == 422
        assert (await c.put("/controls", json={"guard_approval_over": 7})).status_code == 422  # above cap 6
        assert (await c.put("/controls", json={})).status_code == 422
        assert buyer.state.guard.cap == 6  # rejected updates change nothing
        assert any(e.type == "controls_updated" for e in buyer.state.bus.history)


@pytest.mark.anyio
async def test_pause_blocks_new_tasks_until_resumed(tmp_path):
    buyer, c = await client(tmp_path)
    async with buyer.router.lifespan_context(buyer), c:
        await c.put("/controls", json={"paused": True})
        assert (await c.post("/tasks", json={})).status_code == 423
        await c.put("/controls", json={"paused": False})
        assert buyer.state.controls.paused is False


@pytest.mark.anyio
async def test_lowered_cap_moves_no_money_on_an_otherwise_honest_deal(tmp_path):
    s = settings(tmp_path)
    seller_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_seller(s)), base_url="http://seller")
    buyer = create_buyer(s, http=seller_http)
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            await c.put("/controls", json={"guard_cap": 6, "guard_approval_over": 5})
            await c.post("/tasks", json={"demo_mode": "honest"})
            for _ in range(500):
                if {"walked_away", "blocked", "released", "error"} & {e.type for e in buyer.state.bus.history}:
                    break
                await asyncio.sleep(0.01)
    await seller_http.aclose()
    types = [e.type for e in buyer.state.bus.history]
    # Max's own ceiling follows the cap, so he walks; either way no escrow is locked.
    assert "walked_away" in types and not {"escrow_locked", "released"} & set(types)
