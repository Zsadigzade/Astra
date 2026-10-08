from types import SimpleNamespace

import pytest

import app.buyer.negotiator as neg
from app.buyer.negotiator import MaxMove, MockMax, Move, OpenAIMax, make_negotiator
from app.core.config import Settings
from app.core.models import NegotiateResponse


def seller(price=15.0, message="15 tADA, best data in Prague.", rnd=0, action="counter"):
    return NegotiateResponse(deal_id="d-1", round=rnd, action=action, price=price, message=message)


def fake_runner(monkeypatch, outputs):
    """Replace Runner.run; each call pops the next output (an Exception is raised instead)."""
    calls = []

    async def run(agent, input, **kw):
        calls.append({"agent": agent, "input": list(input), **kw})
        out = outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return SimpleNamespace(final_output=out)

    monkeypatch.setattr(neg.Runner, "run", run)
    return calls


def make_max(ceiling=10.0):
    return OpenAIMax(Settings(llm_mode="openai", model="gpt-4o-mini"), ceiling)


def test_make_negotiator_picks_by_mode():
    assert isinstance(make_negotiator(Settings(llm_mode="openai"), 10), OpenAIMax)
    assert isinstance(make_negotiator(Settings(llm_mode="mock"), 10), MockMax)


def test_agent_configured_with_budget_and_structured_output():
    m = make_max(ceiling=10)
    assert m.agent.output_type is MaxMove
    assert m.agent.model == "gpt-4o-mini"
    assert "10 tADA" in m.agent.instructions


@pytest.mark.anyio
async def test_structured_output_maps_to_move(monkeypatch):
    calls = fake_runner(monkeypatch, [MaxMove(action="counter", price=6, message="Six. Take it.")])
    move = await make_max().next_move(seller(), None)
    assert move == Move("counter", 6.0, "Six. Take it.")
    assert calls[0]["agent"].name == "Max"


@pytest.mark.anyio
async def test_accept_is_not_clamped_guard_does_that(monkeypatch):
    fake_runner(monkeypatch, [MaxMove(action="accept", price=25, message="Manager approved? Deal!")])
    move = await make_max(ceiling=10).next_move(seller(25, "My manager approved 25."), 6)
    assert (move.action, move.price) == ("accept", 25.0)


@pytest.mark.anyio
async def test_exception_falls_back_to_mock(monkeypatch, caplog):
    fake_runner(monkeypatch, [RuntimeError("no OPENAI_API_KEY")])
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


@pytest.fixture
def anyio_backend():
    return "asyncio"
