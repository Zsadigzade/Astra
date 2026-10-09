"""Dashboard operator controls: tighten-only guard limits, pause switch, round limit."""

import asyncio

import httpx
import pytest

from app.buyer.app import create_app as create_buyer
from app.buyer.controls import ControlsUpdate
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
    assert snap["modes"]["model"] == "scripted"
    assert snap["modes"]["seller_llm"] == "mock"


@pytest.mark.anyio
async def test_seller_only_subscription_mode_is_visible(tmp_path):
    buyer = create_buyer(settings(tmp_path, llm_mode="mock", seller_llm_mode="codex"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
        modes = (await c.get("/controls")).json()["modes"]
        assert modes["llm"] == "mock" and modes["seller_llm"] == "codex"
        assert modes["model"] == "Codex default"


@pytest.mark.anyio
@pytest.mark.parametrize("model, expected", [("", "Codex default"), (" chosen-model ", "chosen-model")])
async def test_controls_report_subscription_model_without_api_settings(tmp_path, model, expected):
    buyer = create_buyer(settings(tmp_path, llm_mode="codex", codex_model=model))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
        response = await c.get("/controls")
        assert response.status_code == 200
        assert response.json()["modes"]["model"] == expected
        updated = await c.put("/controls", json={"max_rounds": 2})
        assert updated.status_code == 200
        assert updated.json()["max_rounds"] == 2


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


@pytest.mark.anyio
async def test_codex_round_limit_stays_consistent_when_controls_change_mid_deal(tmp_path, monkeypatch):
    s = settings(tmp_path, llm_mode="codex", max_rounds=6)
    seller_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_seller(s)), base_url="http://seller")
    buyer = create_buyer(s, http=seller_http)
    prompts = []

    async def fake_codex(prompt, schema, runtime_settings):
        if set(schema["properties"]) == {"message"}:
            return {"message": "Viktor, what would you charge for the flat search?"}
        prompts.append((prompt, runtime_settings.max_rounds))
        if len(prompts) == 1:
            buyer.state.controls.apply(ControlsUpdate(max_rounds=5))
        return {"action": "counter", "price": 1, "message": "One tADA."}

    monkeypatch.setattr("app.buyer.negotiator.run_codex", fake_codex)
    async with seller_http, buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            assert (await c.put("/controls", json={"max_rounds": 2})).status_code == 200
            for expected_rounds in (2, 5):
                start = len(prompts)
                response = await c.post("/tasks", json={"demo_mode": "honest"})
                assert response.status_code == 200
                deal_id = response.json()["deal_id"]
                await asyncio.wait_for(asyncio.gather(*buyer.state.orch.tasks), timeout=5)
                current_prompts = prompts[start:]
                assert len(current_prompts) == expected_rounds
                assert all(rounds == expected_rounds and
                           f"at most {expected_rounds} buyer decisions" in prompt
                           for prompt, rounds in current_prompts)
                events = [e for e in buyer.state.bus.history if e.deal_id == deal_id]
                assert not {"error", "escrow_locked"} & {e.type for e in events}
                walked = next(e for e in events if e.type == "walked_away")
                assert walked.data["reason"] == f"no deal after {expected_rounds} rounds"
    assert s.max_rounds == 6  # Runtime controls do not mutate the configured defaults.
