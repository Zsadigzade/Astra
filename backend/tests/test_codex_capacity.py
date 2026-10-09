"""Service-wide subscription backpressure/recovery; no live provider calls."""

import asyncio
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from app.buyer import codex_runtime as runtime
from app.buyer.negotiator import CodexMax
from app.core.config import Settings
from app.core.models import NegotiateRequest, NegotiateResponse
from app.seller.persona import CodexViktor


@pytest.fixture
def anyio_backend():
    return "asyncio"


def settings(**kwargs):
    return Settings(codex_max_concurrent=kwargs.pop("codex_max_concurrent", 2),
                    codex_queue_timeout_seconds=kwargs.pop("codex_queue_timeout_seconds", 1),
                    codex_failure_threshold=kwargs.pop("codex_failure_threshold", 3),
                    codex_cooldown_seconds=kwargs.pop("codex_cooldown_seconds", 15), **kwargs)


MOVE = {"action": "counter", "price": 10, "message": "Ten for verified listings."}


async def tick_until(predicate):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(0)


@pytest.mark.anyio
async def test_concurrent_deals_share_capacity_even_with_distinct_settings(monkeypatch):
    config = settings()
    active = peak = started = 0
    finish = asyncio.Event()

    async def turn(*args):
        nonlocal active, peak, started
        active += 1
        started += 1
        peak = max(peak, active)
        try:
            await finish.wait()
            return MOVE
        finally:
            active -= 1

    monkeypatch.setattr(runtime, "_run_turn", turn)
    tasks = [asyncio.create_task(runtime.run_codex(str(i), {}, replace(config))) for i in range(8)]
    await tick_until(lambda: started == 2)
    await asyncio.sleep(0.01)
    assert started == 2
    finish.set()
    assert await asyncio.gather(*tasks) == [MOVE] * 8
    assert peak == 2 and active == 0 and runtime._capacity(config).active == 0


@pytest.mark.anyio
@pytest.mark.parametrize("cancel", [False, True])
async def test_queued_timeout_or_cancellation_never_starts_child(monkeypatch, cancel):
    config = settings(codex_max_concurrent=1, codex_queue_timeout_seconds=0.03)
    finish = asyncio.Event()
    calls = []

    async def turn(prompt, *_):
        calls.append(prompt)
        await finish.wait()
        return MOVE

    monkeypatch.setattr(runtime, "_run_turn", turn)
    first = asyncio.create_task(runtime.run_codex("first", {}, config))
    await tick_until(lambda: calls)
    queued = asyncio.create_task(runtime.run_codex("queued", {}, config))
    await asyncio.sleep(0)
    if cancel:
        queued.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else runtime.CodexQueueTimeout):
        await queued
    assert calls == ["first"]
    assert runtime._capacity(config).failures == 0
    finish.set()
    await first
    assert await runtime.run_codex("later", {}, config) == MOVE
    assert runtime._capacity(config).active == 0


@pytest.mark.anyio
async def test_repeated_failures_fast_fallback_and_single_successful_recovery_probe(monkeypatch):
    config = settings(codex_failure_threshold=2)
    clock = [100.0]
    calls = 0
    recovery = asyncio.Event()
    monkeypatch.setattr(runtime, "monotonic", lambda: clock[0])

    async def turn(*_):
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise runtime.CodexRuntimeError("private provider diagnostics")
        await recovery.wait()
        return MOVE

    monkeypatch.setattr(runtime, "_run_turn", turn)
    for _ in range(2):
        with pytest.raises(runtime.CodexRuntimeError):
            await runtime.run_codex("fail", {}, config)
    for _ in range(4):
        with pytest.raises(runtime.CodexCooldownError):
            await runtime.run_codex("cooling down", {}, config)
    assert calls == 2
    clock[0] += 16
    probe = asyncio.create_task(runtime.run_codex("probe", {}, config))
    await tick_until(lambda: calls == 3)
    with pytest.raises(runtime.CodexCooldownError):
        await runtime.run_codex("second probe", {}, config)
    recovery.set()
    assert await probe == MOVE
    assert await runtime.run_codex("restored", {}, config) == MOVE
    assert runtime._capacity(config).retry_at is None


@pytest.mark.anyio
async def test_failed_probe_reopens_cooldown_and_cancelled_probe_does_not_strand_gate(monkeypatch):
    config = settings(codex_failure_threshold=1)
    clock = [100.0]
    calls = 0
    monkeypatch.setattr(runtime, "monotonic", lambda: clock[0])

    async def turn(*_):
        nonlocal calls
        calls += 1
        if calls == 2:
            await asyncio.Future()
        raise runtime.CodexRuntimeError("unavailable")

    monkeypatch.setattr(runtime, "_run_turn", turn)
    with pytest.raises(runtime.CodexRuntimeError):
        await runtime.run_codex("first", {}, config)
    clock[0] = 116
    probe = asyncio.create_task(runtime.run_codex("cancelled probe", {}, config))
    await tick_until(lambda: calls == 2)
    probe.cancel()
    with pytest.raises(asyncio.CancelledError):
        await probe
    with pytest.raises(runtime.CodexRuntimeError):
        await runtime.run_codex("failed probe", {}, config)
    assert calls == 3 and runtime._capacity(config).retry_at == 131
    with pytest.raises(runtime.CodexCooldownError):
        await runtime.run_codex("cooldown", {}, config)


@pytest.mark.anyio
async def test_breaker_wakes_queued_deals_and_ignores_old_inflight_success(monkeypatch):
    config = settings(codex_failure_threshold=1)
    fail, succeed = asyncio.Event(), asyncio.Event()
    calls = []

    async def turn(prompt, *_):
        calls.append(prompt)
        if prompt == "fail":
            await fail.wait()
            raise runtime.CodexRuntimeError("unavailable")
        await succeed.wait()
        return MOVE

    monkeypatch.setattr(runtime, "_run_turn", turn)
    bad = asyncio.create_task(runtime.run_codex("fail", {}, config))
    old = asyncio.create_task(runtime.run_codex("old", {}, config))
    await tick_until(lambda: len(calls) == 2)
    queued = asyncio.create_task(runtime.run_codex("queued", {}, config))
    await asyncio.sleep(0)
    fail.set()
    with pytest.raises(runtime.CodexRuntimeError):
        await bad
    with pytest.raises(runtime.CodexCooldownError):
        await asyncio.wait_for(queued, 0.2)
    succeed.set()
    await old
    with pytest.raises(runtime.CodexCooldownError):
        await runtime.run_codex("still cooling", {}, config)
    assert calls == ["fail", "old"]


@pytest.mark.anyio
async def test_success_resets_consecutive_failures(monkeypatch):
    config = settings(codex_failure_threshold=2)
    outcomes = [False, True, False, True]

    async def turn(*_):
        if not outcomes.pop(0):
            raise runtime.CodexRuntimeError("unavailable")
        return MOVE

    monkeypatch.setattr(runtime, "_run_turn", turn)
    for _ in range(2):
        with pytest.raises(runtime.CodexRuntimeError):
            await runtime.run_codex("fail", {}, config)
        assert await runtime.run_codex("success", {}, config) == MOVE
    assert runtime._capacity(config).retry_at is None


@pytest.mark.anyio
async def test_total_deadline_includes_queue_and_runtime_timeout_counts_as_failure(monkeypatch):
    config = settings(codex_max_concurrent=1, codex_timeout_seconds=0.12,
                      codex_failure_threshold=1)
    gate = runtime._capacity(config)
    ticket = await gate.acquire()
    started = asyncio.Event()

    async def turn(*_):
        started.set()
        await asyncio.Future()

    monkeypatch.setattr(runtime, "_run_turn", turn)
    task = asyncio.create_task(runtime.run_codex("queued", {}, config))
    await asyncio.sleep(0.07)
    gate.release(ticket, True)
    await started.wait()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(asyncio.shield(task), 0.09)
    assert task.done(), "execution incorrectly received a fresh full turn budget after queueing"
    assert gate.active == 0 and gate.retry_at is not None


@pytest.mark.anyio
async def test_caller_cancellation_is_not_a_provider_failure(monkeypatch):
    config = settings(codex_failure_threshold=1)
    started = asyncio.Event()

    async def turn(*_):
        started.set()
        await asyncio.Future()

    monkeypatch.setattr(runtime, "_run_turn", turn)
    task = asyncio.create_task(runtime.run_codex("cancel", {}, config))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    gate = runtime._capacity(config)
    assert gate.active == gate.failures == 0 and gate.retry_at is None


@pytest.mark.anyio
async def test_both_agents_label_cooldown_fallback_and_viktor_keeps_floor(monkeypatch, caplog):
    config = settings(codex_failure_threshold=1)

    async def turn(*_):
        raise runtime.CodexRuntimeError("private provider diagnostics")

    monkeypatch.setattr(runtime, "_run_turn", turn)
    max_agent = CodexMax(config, ceiling=10)
    response = NegotiateResponse(deal_id="a", round=0, action="counter", price=18, message="Eighteen.")
    await max_agent.next_move(response, None)
    await max_agent.next_move(response.model_copy(update={"round": 1}), 5)
    assert max_agent.last_backend == "mock" and max_agent.fallback_reason == "CodexCooldownError"
    seller = CodexViktor(config, floor=7, opening_ask=18)
    reply = await seller.respond_async(NegotiateRequest(deal_id="b", round=0, action="open"))
    assert reply.backend == "mock" and reply.fallback_reason == "CodexCooldownError"
    assert reply.price >= 7
    assert "private provider diagnostics" not in caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize("overrides", [
    {"codex_max_concurrent": 0}, {"codex_max_concurrent": True}, {"codex_max_concurrent": 33},
    {"codex_failure_threshold": 0}, {"codex_failure_threshold": 101},
    {"codex_queue_timeout_seconds": 0}, {"codex_queue_timeout_seconds": float("inf")},
    {"codex_cooldown_seconds": -1}, {"codex_cooldown_seconds": float("nan")},
])
async def test_invalid_policy_fails_before_starting_child(monkeypatch, overrides):
    async def forbidden(*_):
        pytest.fail("invalid configuration started a CLI")

    monkeypatch.setattr(runtime, "_run_turn", forbidden)
    with pytest.raises(ValueError, match="CODEX_"):
        await runtime.run_codex("invalid", {}, settings(**overrides))


@pytest.mark.anyio
async def test_policy_change_cannot_create_another_pool():
    config = settings()
    runtime._capacity(config)
    with pytest.raises(ValueError, match="restart"):
        runtime._capacity(replace(config, codex_max_concurrent=3))


@pytest.mark.anyio
async def test_real_subprocesses_never_exceed_configured_capacity(monkeypatch, tmp_path):
    script = tmp_path / "capacity_child.py"
    script.write_text("""import json, pathlib, sys, time
started = time.monotonic()
sys.stdin.read()
time.sleep(0.15)
out = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])
out.write_text(json.dumps({'started': started, 'finished': time.monotonic()}))
""", encoding="utf-8")
    monkeypatch.setattr(runtime, "_command", lambda _: [sys.executable, str(script)])
    config = settings(codex_queue_timeout_seconds=5)
    results = await asyncio.gather(*(runtime.run_codex(str(i), {}, config) for i in range(6)))
    points = sorted([(r["started"], 1) for r in results] + [(r["finished"], -1) for r in results])
    active = peak = 0
    for _, change in points:
        active += change
        peak = max(peak, active)
    assert peak == 2 and active == 0 and runtime._capacity(config).active == 0


@pytest.mark.anyio
async def test_slot_stays_held_until_cancelled_child_cleanup_finishes(monkeypatch):
    config = settings(codex_max_concurrent=1)
    entered, stopping, stopped = asyncio.Event(), asyncio.Event(), asyncio.Event()
    directories = []

    class Process:
        returncode = None

        async def communicate(self, *_):
            entered.set()
            await asyncio.Future()

    async def spawn(*args, **kwargs):
        directories.append(Path(kwargs["cwd"]))
        return Process()

    async def terminate(process):
        stopping.set()
        await stopped.wait()
        process.returncode = 1

    monkeypatch.setattr(runtime, "_command", lambda _: ["fake-codex"])
    monkeypatch.setattr(runtime.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(runtime, "_terminate", terminate)
    task = asyncio.create_task(runtime.run_codex("cancel", {}, config))
    await entered.wait()
    task.cancel()
    await stopping.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert runtime._capacity(config).active == 1
    assert directories[0].is_dir()
    queued = asyncio.create_task(runtime.run_codex("wait", {}, config))
    await asyncio.sleep(0.01)
    assert len(directories) == 1, "replacement child started before cancelled child was reaped"
    queued.cancel()
    with pytest.raises(asyncio.CancelledError):
        await queued
    stopped.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert runtime._capacity(config).active == 0
    assert not directories[0].exists()
