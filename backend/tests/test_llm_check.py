import pytest

import app.buyer.negotiator as neg
from app.buyer.guard import Decision, Verdict, WalletGuard
from app.core.config import Settings
from scripts import llm_check


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def runner(monkeypatch):
    calls = []
    outputs = []

    async def run(prompt, schema, settings):
        calls.append({"prompt": prompt, "schema": schema, "settings": settings})
        out = outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(neg, "run_codex", run)
    return calls, outputs


@pytest.mark.anyio
async def test_subscription_check_needs_no_api_key(runner, capsys):
    calls, outputs = runner
    outputs.append({"action": "accept", "price": 150, "message": "Deal."})
    assert await llm_check.check(Settings()) == 0
    assert len(calls) == 1
    assert "real subscription Codex Max" in capsys.readouterr().out


@pytest.mark.anyio
async def test_real_backend_required_even_when_demo_mode_is_mock(runner, capsys):
    calls, outputs = runner
    outputs.extend([{"action": "counter", "price": 50, "message": "Fifty."},
                    {"action": "accept", "price": 70, "message": "Deal."}])
    assert await llm_check.check(Settings(llm_mode="mock")) == 0
    assert len(calls) == 2
    assert all(c["settings"].llm_mode == "mock" for c in calls)
    assert "PASS:" in capsys.readouterr().out


@pytest.mark.anyio
@pytest.mark.parametrize("failure", [RuntimeError("secret-provider-body"),
                                      FileNotFoundError("secret-provider-body"),
                                      PermissionError("secret-provider-body"),
                                      TimeoutError("secret-provider-body"), None])
async def test_fallback_can_never_pass_live_check(runner, failure, capsys, caplog):
    _, outputs = runner
    outputs.append(failure)
    assert await llm_check.check(Settings()) == 1
    captured = capsys.readouterr().out
    assert "scripted fallback" in captured
    assert "signed in with ChatGPT" in captured
    assert "PASS:" not in captured
    assert "secret-provider-body" not in captured + caplog.text


@pytest.mark.anyio
async def test_guard_failure_cannot_be_hidden_by_valid_llm(runner, monkeypatch, capsys):
    _, outputs = runner
    outputs.extend([{"action": "accept", "price": 150, "message": "Deal."}])
    monkeypatch.setattr(WalletGuard, "evaluate", lambda *a, **kw: Decision(Verdict.allow, "broken"))
    assert await llm_check.check(Settings()) == 1
    assert "FAIL: SIMULATED in-memory guard hard cap" in capsys.readouterr().out


def test_guard_uses_actual_rules_without_payment_calls(monkeypatch):
    async def forbidden(*args, **kwargs):
        pytest.fail("Readiness check must never call a payment method")

    for method in ("find", "lock", "release", "refund"):
        monkeypatch.setattr(llm_check.SimulatedPayments, method, forbidden)
    assert llm_check.check_guard()


@pytest.mark.anyio
@pytest.mark.parametrize("fail", [False, True])
async def test_viktor_check_requires_real_opening_and_agreement(monkeypatch, capsys, fail):
    import app.seller.persona as persona

    outputs = [{"action": "counter", "price": 180, "message": "One eighty for the data."},
               {"action": "accept", "price": 70, "message": "Seventy. Deal."}]

    async def run(*args):
        if fail:
            raise TimeoutError("private provider diagnostics")
        return outputs.pop(0)

    monkeypatch.setattr(persona, "run_codex", run)
    assert await llm_check.check_viktor(Settings()) == int(fail)
    output = capsys.readouterr().out
    assert "private provider diagnostics" not in output
    assert ("scripted fallback" if fail else "real Viktor opening and agreement") in output
