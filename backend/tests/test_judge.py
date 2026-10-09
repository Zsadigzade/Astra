"""Public boundary checks: provider execution is replaced, isolation/quota are real."""
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient
import pytest

from app.buyer.app import create_app as buyer_app
from app.core.config import Settings
from app.core.models import TaskCreated
from app.judge import COOKIE, create_app


def test_buyer(settings):
    app = buyer_app(settings)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def life(a):
        async with original(a):
            async def launch(task):
                did = uuid.uuid4().hex[:20]
                a.state.ledger.create_deal(did, "test", task.model_dump_json(), "private-seller")
                a.state.ledger.update(did, status="walked")
                a.state.bus.emit("task_created", "test", did, text=task.text)
                return TaskCreated(task_id="test", deal_id=did)
            a.state.orch.create_task = launch
            yield
    app.router.lifespan_context = life
    return app


test_buyer.__test__ = False


@pytest.fixture
def setup(tmp_path):
    web = tmp_path / "web"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<html><body><main>Demo</main></body></html>")
    s = Settings(payments_mode="simulated", strict_live=False, crash_after_lock=False,
                 llm_mode="mock", seller_llm_mode="mock", tts_mode="off", apify_mode="sample")
    def make(**kwargs):
        return create_app(s, tmp_path / "state", web, secure_cookie=False, buyer_factory=test_buyer, **kwargs)
    return make


ORIGIN = {"Origin": "http://testserver"}


def test_session_cookie_and_no_open_buyer_or_admin(setup):
    with TestClient(setup()) as c:
        assert c.get("/buyer/deals").status_code == 401
        r = c.get("/")
        assert r.status_code == 200 and "SIMULATED money" in r.text
        assert "httponly" in r.headers["set-cookie"].lower()
        assert "samesite=strict" in r.headers["set-cookie"].lower()
        assert c.get("/buyer/deals").json() == []
        for path in ("/docs", "/openapi.json", "/buyer/openapi.json", "/seller/status", "/.env"):
            assert c.get(path).status_code == 404


def test_foreign_origin_and_missing_origin_cannot_spend_or_change_controls(setup):
    with TestClient(setup()) as c:
        c.get("/")
        for headers in ({}, {"Origin":"https://evil.example"}):
            assert c.post("/buyer/tasks", json={}, headers=headers).status_code == 403
            assert c.put("/buyer/controls", json={"paused":True}, headers=headers).status_code == 403
        assert c.app.state.quota.execute("SELECT SUM(used) FROM sessions").fetchone()[0] == 0


def test_sessions_cannot_read_other_history_control_or_audio(setup):
    with TestClient(setup()) as c:
        c.get("/")
        first = c.cookies.get(COOKIE)
        deal = c.post("/buyer/tasks", json={"text":"First judge private request"}, headers=ORIGIN).json()["deal_id"]
        child = c.app.state.children[first]
        Path(child.state.orch.s.audio_dir, "private.mp3").write_bytes(b"example-audio")
        assert c.get("/buyer/audio/private.mp3").status_code == 200
        c.put("/buyer/controls", json={"paused":True}, headers=ORIGIN)
        c.cookies.clear()
        c.get("/")
        assert c.cookies.get(COOKIE) != first
        assert c.get("/buyer/deals").json() == []
        assert c.get("/buyer/controls").json()["paused"] is False
        assert c.get("/buyer/audio/private.mp3").status_code == 404
        assert c.post("/buyer/approvals/"+deal, json={"approve":True}, headers=ORIGIN).status_code == 404


def test_run_limits_survive_restart_and_fresh_cookies(setup):
    with TestClient(setup(max_runs=2, session_runs=1)) as c:
        c.get("/")
        assert c.post("/buyer/tasks", json={}, headers=ORIGIN).status_code == 200
        assert c.post("/buyer/tasks", json={}, headers=ORIGIN).status_code == 429
        c.cookies.clear(); c.get("/")
        assert c.post("/buyer/tasks", json={}, headers=ORIGIN).status_code == 200
    with TestClient(setup(max_runs=2, session_runs=1)) as c:
        c.get("/")
        assert c.post("/buyer/tasks", json={}, headers=ORIGIN).status_code == 429
        assert c.app.state.quota.execute("SELECT SUM(used) FROM sessions").fetchone()[0] == 2


def test_active_run_blocks_admission_without_charging(setup):
    with TestClient(setup()) as c:
        c.get("/")
        child = next(iter(c.app.state.children.values()))
        original = child.state.orch.tasks
        child.state.orch.tasks = {"provider-still-running"}
        try:
            assert c.post("/buyer/tasks", json={}, headers=ORIGIN).status_code == 429
            assert c.app.state.quota.execute("SELECT SUM(used) FROM sessions").fetchone()[0] == 0
        finally:
            child.state.orch.tasks = original


def test_limits_cannot_be_expanded_and_invalid_tasks_do_not_use_quota(setup):
    with TestClient(setup()) as c:
        c.get("/")
        assert c.get("/buyer/controls").json()["max_rounds_ceiling"] == 6
        for body in ({"max_rounds":12}, {"guard_cap":1000}, {"guard_approval_over":1000}):
            assert c.put("/buyer/controls", json=body, headers=ORIGIN).status_code == 422
        assert c.post("/buyer/tasks", json={"job":{"count":100}}, headers=ORIGIN).status_code == 422
        assert c.post("/buyer/tasks", json={"demo_mode":"crash"}, headers=ORIGIN).status_code == 422
        assert c.post("/buyer/tasks", json={"text":"x"*10000}, headers=ORIGIN).status_code == 413
        assert c.app.state.quota.execute("SELECT SUM(used) FROM sessions").fetchone()[0] == 0


def test_session_capacity_and_invented_cookie(setup):
    with TestClient(setup(max_sessions=1)) as c:
        c.get("/")
        c.cookies.clear()
        c.cookies.set(COOKIE,"a"*48)
        assert c.get("/buyer/controls").status_code == 401
        assert c.get("/").status_code == 503


def test_real_payments_and_crash_switch_are_refused(tmp_path):
    for settings in (Settings(payments_mode="masumi"), Settings(crash_after_lock=True)):
        with pytest.raises(ValueError, match="requires simulated"):
            create_app(settings,tmp_path,tmp_path)


def test_judge_sessions_use_fresh_usd_ledgers(tmp_path):
    # A judge state dir from the tADA era must not stop sessions: they get their own USD ledger file.
    web = tmp_path / "web"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<html><body><main>Demo</main></body></html>")
    seen = []

    def factory(settings):
        seen.append(settings.ledger_path)
        return test_buyer(settings)

    s = Settings(payments_mode="simulated", strict_live=False, crash_after_lock=False,
                 llm_mode="mock", seller_llm_mode="mock", tts_mode="off", apify_mode="sample")
    with TestClient(create_app(s, tmp_path / "state", web, secure_cookie=False, buyer_factory=factory)) as c:
        c.get("/")
        assert c.get("/buyer/deals").json() == []
    assert seen and all(Path(p).name == "buyer-usd.db" for p in seen)
