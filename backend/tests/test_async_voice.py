"""Speech is bounded background work and never holds up visible dialogue."""

import asyncio
from types import SimpleNamespace

import pytest

from app.buyer.events import EventBus
from app.buyer.ledger import Ledger
from app.buyer.orchestrator import AUDIO_CONCURRENCY, MAX_AUDIO_TASKS, Orchestrator


@pytest.fixture
def anyio_backend():
    return "asyncio"


def orchestrator(speak, timeout=1):
    ledger = Ledger(":memory:")
    bus = EventBus(ledger, simulated=True)
    return Orchestrator(SimpleNamespace(tts_mode="elevenlabs", tts_timeout_seconds=timeout),
                        ledger, bus, None, None, None, SimpleNamespace(speak=speak), None)


async def say(orch, text="First"):
    await orch._say("task", "deal", "max", text, 70, "counter", False, backend="mock")


@pytest.mark.anyio
async def test_text_is_visible_before_slow_speech_and_updates_keep_identity():
    gates = {text: asyncio.Event() for text in ("First", "Second")}

    async def speak(text, speaker):
        await gates[text].wait()
        return f"/audio/{text}.mp3"

    orch = orchestrator(speak)
    await say(orch)
    await say(orch, "Second")
    originals = list(orch.bus.history)
    assert [e.data["text"] for e in originals] == ["First", "Second"]
    assert all(e.data["audio_status"] == "pending" for e in originals)
    gates["Second"].set()
    await asyncio.sleep(0)
    update = orch.bus.history[-1]
    assert update.type == "audio_ready"
    assert (update.data["message_id"], update.data["message_ts"], update.deal_id) == (
        originals[1].id, originals[1].ts, originals[1].deal_id)
    gates["First"].set()
    await asyncio.gather(*orch.audio_tasks)
    assert orch.bus.history[-1].data["message_id"] == originals[0].id
    await orch.shutdown()


@pytest.mark.anyio
async def test_shutdown_cancels_and_drains_speech_including_not_started_tasks():
    running = 0

    async def speak(*args):
        nonlocal running
        running += 1
        try:
            await asyncio.Event().wait()
        finally:
            running -= 1

    orch = orchestrator(speak)
    await say(orch)
    await asyncio.sleep(0)
    await say(orch, "Not yet started")
    await orch.shutdown()
    assert running == 0
    assert not orch.audio_tasks
    updates = [e for e in orch.bus.history if e.type == "audio_ready"]
    assert len(updates) == 2
    assert all(e.data["audio_status"] == "unavailable" for e in updates)
    assert all(e.data["reason"] == "buyer_stopped" for e in updates)


@pytest.mark.anyio
async def test_capacity_bounds_pending_and_running_synthesis():
    peak = active = 0

    async def speak(*args):
        nonlocal peak, active
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.Event().wait()
        finally:
            active -= 1

    orch = orchestrator(speak)
    for n in range(MAX_AUDIO_TASKS + 3):
        await say(orch, str(n))
    assert len(orch.audio_tasks) == MAX_AUDIO_TASKS
    assert orch.bus.history[-1].data["audio_status"] == "unavailable"
    await asyncio.sleep(0)
    assert peak == AUDIO_CONCURRENCY
    await orch.shutdown()
    assert active == 0


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["exception", "timeout", "none"])
async def test_failure_closes_pending_without_private_diagnostics(failure):
    async def speak(*args):
        if failure == "exception":
            raise RuntimeError("private-provider-secret")
        if failure == "timeout":
            await asyncio.Event().wait()
        return None

    orch = orchestrator(speak, timeout=0.01)
    await say(orch)
    await asyncio.gather(*orch.audio_tasks)
    assert orch.bus.history[-1].data["audio_status"] == "unavailable"
    assert orch.bus.history[-1].data["reason"] == "synthesis_unavailable"
    assert "private-provider-secret" not in str(orch.bus.history)
    await orch.shutdown()


@pytest.mark.anyio
async def test_restart_closes_only_unresolved_originals_without_resynthesis():
    async def forbidden(*args):
        pytest.fail("Recovery must never synthesize historic dialogue")

    orch = orchestrator(forbidden)
    one = orch.bus.emit("negotiation", "task", "deal", audio_status="pending", text="One")
    two = orch.bus.emit("negotiation", "task", "deal", audio_status="pending", text="Two")
    orch._audio_result(one, "/audio/one.mp3")
    # An ID match with a different timestamp is unrelated.
    orch.bus.emit("audio_ready", "task", "deal", message_id=two.id, message_ts=two.ts - 1,
                  audio_status="ready", audio_url="/audio/wrong.mp3")
    await orch.resume_unfinished()
    updates = [e for e in orch.bus.history if e.type == "audio_ready"]
    assert len(updates) == 3
    assert updates[-1].data["message_id"] == two.id
    assert updates[-1].data["message_ts"] == two.ts
    assert updates[-1].data["audio_status"] == "unavailable"
    assert updates[-1].data["reason"] == "buyer_restarted"
    assert "reason" not in updates[0].data  # successful original stays successful
    await orch.resume_unfinished()
    assert len([e for e in orch.bus.history if e.type == "audio_ready"]) == 3


@pytest.mark.anyio
async def test_disabled_speech_is_immediately_text_only():
    async def forbidden(*args):
        pytest.fail("Disabled voice must not schedule synthesis")

    orch = orchestrator(forbidden)
    orch.s.tts_mode = "off"
    await say(orch)
    assert not orch.audio_tasks
    assert orch.bus.history[-1].data["audio_status"] == "unavailable"


@pytest.mark.anyio
async def test_full_simulated_deal_settles_while_speech_is_still_pending(tmp_path, monkeypatch):
    from app.core.config import Settings
    from app.voice.tts import TTS
    from tests.test_acts import run_task

    started = cancelled = 0

    async def slow_speech(*args):
        nonlocal started, cancelled
        started += 1
        try:
            await asyncio.Event().wait()
        finally:
            cancelled += 1

    monkeypatch.setattr(TTS, "speak", slow_speech)
    settings = Settings(tts_mode="elevenlabs", ledger_path=str(tmp_path / "buyer.db"),
                        audio_dir=str(tmp_path / "audio"), seller_url="http://seller")
    events, balances = await asyncio.wait_for(run_task(tmp_path, "honest", settings=settings), timeout=3)
    released = next(e for e in events if e.type == "released")
    originals = [e for e in events if e.type == "negotiation"]
    updates = [e for e in events if e.type == "audio_ready"]
    assert originals and len(updates) == len(originals)
    assert all(e.id > released.id for e in updates)  # only shutdown ends the slow voices
    assert all(e.data["audio_status"] == "unavailable" for e in updates)
    assert all(e.data["reason"] == "buyer_stopped" for e in updates)
    assert started == cancelled == AUDIO_CONCURRENCY
    assert (balances["buyer"], balances["seller"], balances["escrow"]) == (930, 70, 0)
