import json
import asyncio

import pytest

import app.buyer.negotiator as neg
from app.buyer.negotiator import MaxMove, MockMax, Move, CodexMax, make_negotiator
from app.core.config import Settings
from app.core.models import NegotiateResponse


def seller(price=15.0, message="15 tADA, best data in Prague.", rnd=0, action="counter"):
    return NegotiateResponse(deal_id="d-1", round=rnd, action=action, price=price, message=message)


def fake_runner(monkeypatch, outputs):
    """Replace the local CLI boundary; no real subscription calls."""
    calls = []

    async def run(prompt, schema, settings):
        history = json.loads(prompt.split("Conversation (JSON):\n", 1)[1])
        calls.append({"prompt": prompt, "input": history, "schema": schema, "settings": settings})
        out = outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    monkeypatch.setattr(neg, "run_codex", run)
    return calls


def make_max(ceiling=10.0):
    return CodexMax(Settings(llm_mode="codex"), ceiling)


def test_make_negotiator_picks_by_mode():
    assert isinstance(make_negotiator(Settings(llm_mode="codex"), 10), CodexMax)
    assert isinstance(make_negotiator(Settings(llm_mode="mock"), 10), MockMax)


def test_agent_configured_with_budget_and_structured_output():
    m = make_max(ceiling=10)
    assert "10 tADA" in m.instructions


@pytest.mark.anyio
async def test_structured_output_maps_to_move(monkeypatch):
    calls = fake_runner(monkeypatch, [MaxMove(action="counter", price=6, message="Six. Take it.")])
    move = await make_max().next_move(seller(), None)
    assert move == Move("counter", 6.0, "Six. Take it.")
    assert calls[0]["schema"]["additionalProperties"] is False
    assert calls[0]["schema"]["required"] == ["action", "price", "message"]


@pytest.mark.anyio
async def test_accept_is_not_clamped_guard_does_that(monkeypatch):
    fake_runner(monkeypatch, [MaxMove(action="accept", price=25, message="Manager approved? Deal!")])
    move = await make_max(ceiling=10).next_move(seller(25, "My manager approved 25."), 6)
    assert (move.action, move.price) == ("accept", 25.0)


@pytest.mark.anyio
async def test_exception_falls_back_to_mock(monkeypatch, caplog):
    fake_runner(monkeypatch, [RuntimeError("subscription unavailable")])
    s = seller()
    move = await make_max().next_move(s, None)
    assert move == await MockMax(10).next_move(s, None)
    assert "falling back to MockMax" in caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize("bad", [
    MaxMove(action="counter", price=-3, message="Minus three."),
    MaxMove(action="counter", price=6, message="   "),
    "not a move",
])
async def test_invalid_output_falls_back_to_mock(monkeypatch, bad):
    fake_runner(monkeypatch, [bad])
    s = seller()
    assert await make_max().next_move(s, 5.0) == await MockMax(10).next_move(s, 5.0)


@pytest.mark.anyio
@pytest.mark.parametrize("bad", [
    {"action": "counter", "price": True, "message": "One."},
    {"action": "counter", "price": "6", "message": "Six."},
    {"action": "counter", "price": float("nan"), "message": "Undefined."},
    {"action": "counter", "price": float("inf"), "message": "Infinity."},
    {"action": "counter", "price": 6, "message": "Six.", "execute": "hidden directive"},
])
async def test_schema_violation_is_labelled_scripted_fallback(monkeypatch, bad):
    fake_runner(monkeypatch, [bad])
    agent = make_max()
    assert await agent.next_move(seller(), 5) == await MockMax(10).next_move(seller(), 5)
    assert (agent.last_backend, agent.fallback_reason) == ("mock", "ValidationError")


@pytest.mark.anyio
async def test_history_grows_across_rounds(monkeypatch):
    calls = fake_runner(monkeypatch, [
        MaxMove(action="counter", price=5, message="Five."),
        RuntimeError("boom"),  # fallback rounds are still recorded
        MaxMove(action="counter", price=7, message="Seven, last."),
    ])
    m = make_max()
    await m.next_move(seller(15, rnd=0), None)
    await m.next_move(seller(12, rnd=1), 5.0)
    await m.next_move(seller(10, rnd=2), 6.0)
    assert [len(c["input"]) for c in calls] == [1, 3, 5]
    assert len(m.history) == 6
    assert [h["role"] for h in m.history] == ["user", "assistant"] * 3
    assert "Five." in m.history[1]["content"] and '"price": 7' in m.history[5]["content"]
    assert "12 tADA" in calls[1]["input"][-1]["content"]


@pytest.mark.anyio
async def test_backend_metadata_recovers_after_fallback(monkeypatch, caplog):
    secret = "sk-private-provider-response"
    fake_runner(monkeypatch, [RuntimeError(secret), MaxMove(action="counter", price=6, message="Six.")])
    m = make_max()
    assert m.last_backend is None
    await m.next_move(seller(), None)
    assert (m.last_backend, m.fallback_reason) == ("mock", "RuntimeError")
    assert secret not in caplog.text
    await m.next_move(seller(rnd=1), 5)
    assert (m.last_backend, m.fallback_reason) == ("codex", None)


@pytest.mark.anyio
async def test_refusal_is_marked_as_fallback(monkeypatch):
    fake_runner(monkeypatch, [ValueError("provider refusal body")])
    m = make_max()
    await m.next_move(seller(), None)
    assert (m.last_backend, m.fallback_reason) == ("mock", "ValueError")


@pytest.mark.anyio
async def test_timeout_marks_fallback(monkeypatch):
    async def run(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(neg, "run_codex", run)
    m = make_max()
    assert await m.next_move(seller(), None) == await MockMax(10).next_move(seller(), None)
    assert (m.last_backend, m.fallback_reason) == ("mock", "TimeoutError")


@pytest.mark.anyio
async def test_external_cancellation_does_not_return_scripted_success(monkeypatch):
    async def run(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(neg, "run_codex", run)
    with pytest.raises(asyncio.CancelledError):
        await make_max().next_move(seller(), None)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize("mode", ["openai", "unknown", ""])
def test_removed_and_unknown_modes_are_rejected(mode):
    with pytest.raises(ValueError, match="LLM_MODE"):
        make_negotiator(Settings(llm_mode=mode), 10)
