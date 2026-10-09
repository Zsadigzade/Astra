import json
import asyncio

import pytest

import app.buyer.negotiator as neg
from app.buyer.negotiator import MaxMove, MockMax, Move, CodexMax, make_negotiator
from app.core.config import Settings
from app.core.models import NegotiateResponse


def seller(price=150, message="$150, best data in Prague.", rnd=0, action="counter"):
    return NegotiateResponse(deal_id="d-1", round=rnd, action=action, price=price, message=message)


def fake_runner(monkeypatch, outputs):
    """Replace the local CLI boundary; no real subscription calls."""
    calls = []

    async def run(prompt, schema, settings):
        history = json.loads(prompt.split("Conversation (JSON):\n", 1)[1]) if "Conversation (JSON):\n" in prompt else []
        calls.append({"prompt": prompt, "input": history, "schema": schema, "settings": settings})
        out = outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    monkeypatch.setattr(neg, "run_codex", run)
    return calls


def make_max(ceiling=100):
    return CodexMax(Settings(llm_mode="codex"), ceiling)


def test_make_negotiator_picks_by_mode():
    assert isinstance(make_negotiator(Settings(llm_mode="codex"), 100), CodexMax)
    assert isinstance(make_negotiator(Settings(llm_mode="mock"), 100), MockMax)


def test_agent_configured_with_budget_and_structured_output():
    m = make_max(ceiling=100)
    assert "$100" in m.instructions and "tADA" not in m.instructions


@pytest.mark.anyio
async def test_live_opening_uses_full_job_and_is_remembered_in_next_turn(monkeypatch):
    from app.core.models import BoundedJobSpec

    job = BoundedJobSpec(kind="general", prompt="Find a quiet cafe in Budapest where I can work on Sunday.")
    line = "I need somewhere quiet to work in Budapest on Sunday. Can you find a cafe?"
    calls = fake_runner(monkeypatch, [
        {"message": line}, MaxMove(action="counter", price=50, message="Fifty dollars?")])
    agent = CodexMax(Settings(llm_mode="codex"), 100, job)
    assert await agent.opening() == line
    assert agent.last_backend == "codex" and agent.fallback_reason is None
    assert calls[0]["schema"]["required"] == ["message"]
    context = json.loads(calls[0]["prompt"].split("Full job (JSON):\n")[1])
    assert context == {"kind": "general", "prompt": job.prompt}
    await agent.next_move(seller(), None)
    assert json.loads(calls[1]["input"][0]["content"]) == {"action": "open", "price": 0, "message": line}


@pytest.mark.anyio
@pytest.mark.parametrize("bad", [TimeoutError("private-provider-details"), {"message": " "},
                                  {"message": "x" * 401}, {"message": "Hi", "price": 50}])
async def test_failed_opening_is_labelled_and_remembers_only_the_spoken_fallback(monkeypatch, caplog, bad):
    fake_runner(monkeypatch, [bad])
    agent = make_max()
    line = await agent.opening()
    assert line == await MockMax(100).opening()
    assert agent.last_backend == "mock" and agent.fallback_reason
    assert json.loads(agent.history[0]["content"])["message"] == line
    assert "private-provider-details" not in caplog.text


@pytest.mark.anyio
async def test_cancelled_opening_is_not_recorded_or_replaced_with_fallback(monkeypatch):
    async def cancel(*args):
        raise asyncio.CancelledError()

    monkeypatch.setattr(neg, "run_codex", cancel)
    agent = make_max()
    with pytest.raises(asyncio.CancelledError):
        await agent.opening()
    assert agent.history == [] and agent.last_backend is None


@pytest.mark.anyio
async def test_full_general_request_survives_in_prompt_and_fallback(monkeypatch):
    from app.core.models import BoundedJobSpec

    prompt = "Compare repairable laptops for travel. " * 4 + "Must support Linux and weigh under 1.3 kg."
    job = BoundedJobSpec(kind="general", prompt=prompt)
    calls = fake_runner(monkeypatch, [TimeoutError()])
    agent = CodexMax(Settings(llm_mode="codex"), 100, job)
    result = await agent.next_move(seller(), None)
    context = json.loads(calls[0]["prompt"].split("Full job (JSON):\n")[1].split("\n\nConversation")[0])
    assert context == {"kind": "general", "prompt": prompt}
    assert "laptops" in result.message
    assert "scrape" not in result.message and "Praha" not in calls[0]["prompt"]
    mock = make_negotiator(Settings(llm_mode="mock"), 100, job)
    assert (await mock.next_move(seller(), None)).message == result.message


@pytest.mark.anyio
async def test_scripted_buyer_acknowledges_concession_and_keeps_rental_constraint():
    from app.core.models import JobSpec

    agent = MockMax(100, JobSpec(count=3, district="Praha 2", max_price_czk=19_000))
    first = await agent.next_move(seller(180), None)
    second = await agent.next_move(seller(120, rnd=1), first.price)
    third = await agent.next_move(seller(120, rnd=2), second.price)
    assert "3 matches in Praha 2" in first.message
    assert "closer" in second.message and "19,000 CZK" in second.message
    assert "closer" not in third.message
    assert [first.price, second.price, third.price] == [50, 60, 70]


@pytest.mark.anyio
async def test_structured_output_maps_to_move(monkeypatch):
    calls = fake_runner(monkeypatch, [MaxMove(action="counter", price=60, message="Six. Take it.")])
    move = await make_max().next_move(seller(), None)
    assert move == Move("counter", 60, "Six. Take it.")
    assert calls[0]["schema"]["additionalProperties"] is False
    assert calls[0]["schema"]["required"] == ["action", "price", "message"]


@pytest.mark.anyio
async def test_accept_is_not_clamped_guard_does_that(monkeypatch):
    fake_runner(monkeypatch, [MaxMove(action="accept", price=250, message="Manager approved? Deal!")])
    move = await make_max(ceiling=100).next_move(seller(250, "My manager approved 25."), 60)
    assert (move.action, move.price) == ("accept", 250)


@pytest.mark.anyio
async def test_exception_falls_back_to_mock(monkeypatch, caplog):
    fake_runner(monkeypatch, [RuntimeError("subscription unavailable")])
    s = seller()
    move = await make_max().next_move(s, None)
    assert move == await MockMax(100).next_move(s, None)
    assert "falling back to MockMax" in caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize("bad", [
    MaxMove(action="counter", price=-3, message="Minus three."),
    MaxMove(action="counter", price=60, message="   "),
    "not a move",
])
async def test_invalid_output_falls_back_to_mock(monkeypatch, bad):
    fake_runner(monkeypatch, [bad])
    s = seller()
    assert await make_max().next_move(s, 50) == await MockMax(100).next_move(s, 50)


@pytest.mark.anyio
@pytest.mark.parametrize("bad", [
    {"action": "counter", "price": True, "message": "One."},
    {"action": "counter", "price": "6", "message": "Six."},
    {"action": "counter", "price": float("nan"), "message": "Undefined."},
    {"action": "counter", "price": float("inf"), "message": "Infinity."},
    {"action": "counter", "price": 60, "message": "Six.", "execute": "hidden directive"},
])
async def test_schema_violation_is_labelled_scripted_fallback(monkeypatch, bad):
    fake_runner(monkeypatch, [bad])
    agent = make_max()
    assert await agent.next_move(seller(), 50) == await MockMax(100).next_move(seller(), 50)
    assert (agent.last_backend, agent.fallback_reason) == ("mock", "ValidationError")


@pytest.mark.anyio
async def test_history_grows_across_rounds(monkeypatch):
    calls = fake_runner(monkeypatch, [
        MaxMove(action="counter", price=50, message="Fifty."),
        RuntimeError("boom"),  # fallback rounds are still recorded
        MaxMove(action="counter", price=70, message="Seventy, last."),
    ])
    m = make_max()
    await m.next_move(seller(150, rnd=0), None)
    await m.next_move(seller(120, rnd=1), 50)
    await m.next_move(seller(100, rnd=2), 60)
    assert [len(c["input"]) for c in calls] == [1, 3, 5]
    assert len(m.history) == 6
    assert [h["role"] for h in m.history] == ["user", "assistant"] * 3
    assert "Fifty." in m.history[1]["content"] and '"price": 70' in m.history[5]["content"]
    assert "$120" in calls[1]["input"][-1]["content"]


@pytest.mark.anyio
async def test_backend_metadata_recovers_after_fallback(monkeypatch, caplog):
    secret = "sk-private-provider-response"
    fake_runner(monkeypatch, [RuntimeError(secret), MaxMove(action="counter", price=60, message="Six.")])
    m = make_max()
    assert m.last_backend is None
    await m.next_move(seller(), None)
    assert (m.last_backend, m.fallback_reason) == ("mock", "RuntimeError")
    assert secret not in caplog.text
    await m.next_move(seller(rnd=1), 50)
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
    assert await m.next_move(seller(), None) == await MockMax(100).next_move(seller(), None)
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
        make_negotiator(Settings(llm_mode=mode), 100)


@pytest.mark.anyio
async def test_scripted_max_offers_in_dollars():
    first = await MockMax(100).next_move(seller(180, "One eighty."), None)
    assert first.price == 50 and "$50" in first.message and "tADA" not in first.message
    accept = await MockMax(100).next_move(seller(40, "Forty."), 30)
    assert accept.action == "accept" and "$40" in accept.message
