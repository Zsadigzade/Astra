from types import SimpleNamespace

import pytest
from agents.exceptions import ModelBehaviorError

import app.buyer.negotiator as neg
from app.buyer.guard import Decision, Verdict, WalletGuard
from app.buyer.negotiator import MaxMove
from app.core.config import Settings
from scripts import llm_check


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def runner(monkeypatch):
    calls = []
    outputs = []

    async def run(agent, input, **kwargs):
        calls.append(kwargs)
        out = outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return SimpleNamespace(final_output=out)

    monkeypatch.setenv("OPENAI_API_KEY", "fake-unit-test-key")
    monkeypatch.setattr(neg.Runner, "run", run)
    return calls, outputs


@pytest.mark.anyio
async def test_missing_key_makes_no_provider_request(monkeypatch, runner, capsys):
    calls, _ = runner
    monkeypatch.delenv("OPENAI_API_KEY")
    assert await llm_check.check(Settings()) == 1
    assert calls == []
    assert "OPENAI_API_KEY is missing" in capsys.readouterr().out


@pytest.mark.anyio
async def test_real_backend_required_even_when_demo_mode_is_mock(runner, capsys):
    calls, outputs = runner
    outputs.extend([MaxMove(action="counter", price=5, message="Five."),
                    MaxMove(action="accept", price=7, message="Deal.")])
    assert await llm_check.check(Settings(llm_mode="mock")) == 0
    assert len(calls) == 2
    assert all(c["run_config"].tracing_disabled for c in calls)
    assert "PASS:" in capsys.readouterr().out


@pytest.mark.anyio
@pytest.mark.parametrize("failure", [RuntimeError("secret-provider-body"),
                                      ModelBehaviorError("secret-provider-body"),
                                      TimeoutError("secret-provider-body"), None])
async def test_fallback_can_never_pass_live_check(runner, failure, capsys, caplog):
    _, outputs = runner
    outputs.append(failure)
    assert await llm_check.check(Settings()) == 1
    captured = capsys.readouterr().out
    assert "scripted fallback" in captured
    assert "PASS:" not in captured
    assert "secret-provider-body" not in captured + caplog.text


@pytest.mark.anyio
async def test_guard_failure_cannot_be_hidden_by_valid_llm(runner, monkeypatch, capsys):
    _, outputs = runner
    outputs.extend([MaxMove(action="accept", price=15, message="Deal.")])
    monkeypatch.setattr(WalletGuard, "evaluate", lambda *a, **kw: Decision(Verdict.allow, "broken"))
    assert await llm_check.check(Settings()) == 1
    assert "FAIL: SIMULATED in-memory guard hard cap" in capsys.readouterr().out


def test_guard_uses_actual_rules_without_payment_calls(monkeypatch):
    async def forbidden(*args, **kwargs):
        pytest.fail("Readiness check must never call a payment method")

    for method in ("lock", "release", "refund"):
        monkeypatch.setattr(llm_check.SimulatedPayments, method, forbidden)
    assert llm_check.check_guard()
