"""Local-production hardening: access tokens, rate limits, durable seller state and STRICT_LIVE errors."""

import asyncio

import httpx
import pytest

import app.seller.app as seller_module
from app.buyer.app import create_app as create_buyer
from app.core.auth import RateLimiter
from app.core.config import Settings
from app.core.models import BoundedJobSpec, DemoMode, StartJobResponse, StatusResponse
from app.seller.app import create_app as create_seller
from app.seller.store import SellerStore
from tests.fake_masumi import create_fake_masumi
from tests.test_acts import run_task

TOKEN = "buyer-test-token"
SELLER_TOKEN = "seller-test-token"
DEAL = "0123456789abcdef0123"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def settings(tmp_path, **kw) -> Settings:
    return Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                    seller_url="http://seller", **kw)


def client(app, base="http://test", **kw) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=base, **kw)


async def asgi_status(app, path: str, query: str = "", headers: dict | None = None) -> int:
    """Status of a GET without reading the body: works for the never-ending SSE stream."""
    messages = iter([{"type": "http.request", "body": b"", "more_body": False}])
    status = []

    async def receive():
        try:
            return next(messages)
        except StopIteration:
            await asyncio.sleep(0.01)
            return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            status.append(message["status"])

    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET",
             "scheme": "http", "path": path, "raw_path": path.encode(), "root_path": "",
             "query_string": query.encode(), "server": ("test", 80), "client": ("127.0.0.1", 5000),
             "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]}
    await asyncio.wait_for(app(scope, receive, send), 5)
    return status[0]


# ---------- buyer auth ----------

@pytest.mark.anyio
async def test_buyer_requires_token_except_health(tmp_path):
    buyer = create_buyer(settings(tmp_path, api_token=TOKEN))
    async with client(buyer) as c:
        assert (await c.get("/health")).status_code == 200
        for path in ("/controls", "/deals", "/balances"):
            r = await c.get(path)
            assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
        assert (await c.get("/controls", headers={"X-API-Token": "wrong"})).status_code == 401
        assert (await c.get("/controls", headers={"Authorization": "Bearer wrong"})).status_code == 401
        assert (await c.get("/controls", headers={"Authorization": f"Basic {TOKEN}"})).status_code == 401
        assert (await c.get("/controls", headers={"Authorization": f"Bearer {TOKEN}"})).status_code == 200
        assert (await c.get("/controls", headers={"X-API-Token": TOKEN})).status_code == 200
        # Query tokens are only for EventSource and <audio>, never for control endpoints.
        assert (await c.get("/controls", params={"token": TOKEN})).status_code == 401
        assert (await c.post("/tasks", json={})).status_code == 401
        assert (await c.post("/requests/parse", json={"text": "flats"})).status_code == 401
        assert (await c.put("/controls", json={"paused": True})).status_code == 401
        assert (await c.post(f"/approvals/{DEAL}", json={"approve": True})).status_code == 401
        assert (await c.post("/requests/parse", json={"text": "5 flats in Praha 7"},
                             headers={"X-API-Token": TOKEN})).status_code == 200


@pytest.mark.anyio
async def test_buyer_events_and_audio_accept_query_token(tmp_path):
    buyer = create_buyer(settings(tmp_path, api_token=TOKEN))
    (tmp_path / "audio" / "line.mp3").write_bytes(b"ID3" + b"\0" * 200)
    assert await asgi_status(buyer, "/events") == 401
    assert await asgi_status(buyer, "/events", "token=wrong") == 401
    assert await asgi_status(buyer, "/events", f"token={TOKEN}") == 200
    assert await asgi_status(buyer, "/events", headers={"X-API-Token": TOKEN}) == 200
    async with client(buyer) as c:
        assert (await c.get("/audio/line.mp3")).status_code == 401
        assert (await c.get("/audio/line.mp3", params={"token": "nope"})).status_code == 401
        assert (await c.get("/audio/line.mp3", params={"token": TOKEN})).status_code == 200
        assert (await c.get("/audio/line.mp3", headers={"X-API-Token": TOKEN})).status_code == 200


@pytest.mark.anyio
async def test_buyer_without_token_stays_open(tmp_path):
    buyer = create_buyer(settings(tmp_path))
    async with client(buyer) as c:
        assert (await c.get("/controls")).status_code == 200
    assert await asgi_status(buyer, "/events") == 200


@pytest.mark.anyio
async def test_cors_preflight_allows_token_headers_and_401_keeps_cors(tmp_path):
    buyer = create_buyer(settings(tmp_path, api_token=TOKEN))
    origin = "http://localhost:5173"
    async with client(buyer) as c:
        pre = await c.options("/tasks", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                 "Access-Control-Request-Headers": "content-type,x-api-token"})
        assert pre.status_code == 200
        allowed = pre.headers["access-control-allow-headers"].lower()
        assert "x-api-token" in allowed and "authorization" in allowed
        denied = await c.get("/controls", headers={"Origin": origin})
        assert denied.status_code == 401 and denied.headers["access-control-allow-origin"] == origin


# ---------- seller auth ----------

@pytest.mark.anyio
async def test_seller_requires_token_except_health_and_availability(tmp_path):
    seller = create_seller(settings(tmp_path, seller_api_token=SELLER_TOKEN))
    async with client(seller) as c:
        assert (await c.get("/health")).status_code == 200
        assert (await c.get("/availability")).status_code == 200
        assert (await c.get("/input_schema")).status_code == 401
        assert (await c.get("/status", params={"job_id": "x"})).status_code == 401
        assert (await c.post("/start_job", json={})).status_code == 401
        assert (await c.post("/negotiate", json={})).status_code == 401
        assert (await c.get("/input_schema", params={"token": SELLER_TOKEN})).status_code == 401
        assert (await c.get("/input_schema", headers={"X-API-Token": SELLER_TOKEN})).status_code == 200
        assert (await c.get("/input_schema",
                            headers={"Authorization": f"Bearer {SELLER_TOKEN}"})).status_code == 200


@pytest.mark.anyio
async def test_buyer_sends_seller_token_and_settles(tmp_path, monkeypatch):
    s = settings(tmp_path, api_token=TOKEN, seller_api_token=SELLER_TOKEN)
    seller = create_seller(s)
    real_client = httpx.AsyncClient
    created = []

    def seller_client(**kw):  # the buyer's own lifespan client, routed to the in-process seller
        created.append(kw)
        return real_client(transport=httpx.ASGITransport(app=seller), **kw)

    buyer = create_buyer(s)
    monkeypatch.setattr("app.buyer.app.httpx.AsyncClient", seller_client)
    async with buyer.router.lifespan_context(buyer):
        async with real_client(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer",
                               headers={"X-API-Token": TOKEN}) as c:
            r = await c.post("/tasks", json={"demo_mode": "honest"})
            assert r.status_code == 200
            for _ in range(500):
                if {"released", "error", "refunded", "walked_away"} & {e.type for e in buyer.state.bus.history}:
                    break
                await asyncio.sleep(0.01)
            types = {e.type for e in buyer.state.bus.history}
            assert "released" in types and "error" not in types
    assert created and created[0]["headers"] == {"X-API-Token": SELLER_TOKEN}


# ---------- rate limit ----------

@pytest.mark.anyio
async def test_parse_and_tasks_are_rate_limited_per_client(tmp_path):
    buyer = create_buyer(settings(tmp_path, rate_limit_per_minute=2))
    async with client(buyer) as c:
        for _ in range(2):
            assert (await c.post("/requests/parse", json={"text": "5 flats"})).status_code == 200
        limited = await c.post("/requests/parse", json={"text": "5 flats"})
        assert limited.status_code == 429 and 1 <= int(limited.headers["retry-after"]) <= 60
        # Separate bucket: previews never use up the allowance for starting a task.
        await c.put("/controls", json={"paused": True})
        assert [(await c.post("/tasks", json={})).status_code for _ in range(3)] == [423, 423, 429]


@pytest.mark.anyio
async def test_zero_rate_limit_disables_throttling(tmp_path):
    buyer = create_buyer(settings(tmp_path, rate_limit_per_minute=0))
    async with client(buyer) as c:
        codes = {(await c.post("/requests/parse", json={"text": "5 flats"})).status_code for _ in range(50)}
    assert codes == {200}


def test_sliding_window_frees_slots_as_hits_age_out():
    now = [0.0]
    limiter = RateLimiter(2, window=60, clock=lambda: now[0])
    assert limiter.check("tasks", "a") is None
    now[0] = 30
    assert limiter.check("tasks", "a") is None
    assert limiter.check("tasks", "a") == pytest.approx(30)
    assert limiter.check("tasks", "b") is None  # per client
    now[0] = 60.5
    assert limiter.check("tasks", "a") is None  # first hit left the window
    assert limiter.check("tasks", "a") is not None


# ---------- durable seller ----------

async def agree(c: httpx.AsyncClient, deal_id: str = DEAL, price: float = 70) -> None:
    job = {"count": 3, "district": "Praha 7", "max_price_czk": 25000}
    base = {"deal_id": deal_id, "job": job, "demo_mode": "honest", "message": "hi"}
    assert (await c.post("/negotiate", json={**base, "round": 0, "action": "open"})).json()["action"] == "counter"
    r = await c.post("/negotiate", json={**base, "round": 1, "action": "counter", "offer": price})
    assert r.json()["action"] == "accept" and r.json()["price"] == price


def start_body(deal_id: str = DEAL, price: float = 70) -> dict:
    return {"identifier_from_purchaser": deal_id, "input_data": {
        "deal_id": deal_id, "agreed_price": price, "demo_mode": "honest",
        "job": {"count": 3, "district": "Praha 7", "max_price_czk": 25000}}}


async def wait_status(c: httpx.AsyncClient, job_id: str, want: str) -> dict:
    for _ in range(300):
        body = (await c.get("/status", params={"job_id": job_id})).json()
        if body["status"] == want:
            return body
        await asyncio.sleep(0.01)
    raise AssertionError(f"job {job_id} never reached {want}: {body}")


@pytest.mark.anyio
async def test_agreement_survives_seller_restart(tmp_path):
    s = settings(tmp_path, seller_store_path=str(tmp_path / "seller.db"))
    first = create_seller(s)
    async with first.router.lifespan_context(first), client(first) as c:
        await agree(c)
    first.state.store.close()

    second = create_seller(s)
    async with second.router.lifespan_context(second), client(second) as c:
        assert (await c.post("/start_job", json=start_body(price=80))).status_code == 409  # still exact
        started = (await c.post("/start_job", json=start_body())).json()
        assert started["status"] == "success" and started["price"] == 70
        done = await wait_status(c, started["job_id"], "completed")
        assert len(done["result"]["flats"]) == 3
    second.state.store.close()

    third = create_seller(s)  # idempotent retry and finished status both survive another restart
    async with third.router.lifespan_context(third), client(third) as c:
        assert (await c.post("/start_job", json=start_body())).json()["job_id"] == started["job_id"]
        assert (await c.get("/status", params={"job_id": started["job_id"]})).json()["status"] == "completed"
    third.state.store.close()


@pytest.mark.anyio
async def test_running_job_is_respawned_after_restart(tmp_path, monkeypatch):
    s = settings(tmp_path, seller_store_path=str(tmp_path / "seller.db"))
    monkeypatch.setattr(seller_module, "JOB_SECONDS", 60)  # the first seller stops mid-job
    first = create_seller(s)
    async with first.router.lifespan_context(first), client(first) as c:
        await agree(c)
        job_id = (await c.post("/start_job", json=start_body())).json()["job_id"]
        assert (await c.get("/status", params={"job_id": job_id})).json()["status"] == "running"
    first.state.store.close()

    monkeypatch.setattr(seller_module, "JOB_SECONDS", 0)
    second = create_seller(s)
    async with second.router.lifespan_context(second), client(second) as c:
        done = await wait_status(c, job_id, "completed")
        assert len(done["result"]["flats"]) == 3 and done["result"]["source"] == "sample"
    second.state.store.close()


@pytest.mark.skip(reason="Masumi payments dormant since 2026-10-09; SIMULATED only")
@pytest.mark.anyio
async def test_awaiting_masumi_payment_is_watched_again_after_restart(tmp_path):
    path = str(tmp_path / "seller.db")
    s = Settings(payments_mode="masumi", masumi_payment_url="http://masumi", masumi_api_key="test-key",
                 masumi_agent_id="agent-" + "a" * 60, seller_vkey="b" * 56, masumi_poll_seconds=0.01,
                 seller_store_path=path, ledger_path=str(tmp_path / "buyer.db"),
                 audio_dir=str(tmp_path / "audio"))
    fake = create_fake_masumi()
    masumi_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=fake))
    first = create_seller(s, masumi_http=masumi_http)
    async with first.router.lifespan_context(first), client(first) as c:
        await agree(c)
        started = (await c.post("/start_job", json=start_body())).json()
        assert (await c.get("/status", params={"job_id": started["job_id"]})).json()["status"] == "awaiting_payment"
    first.state.store.close()

    bid = started["blockchainIdentifier"]
    fake.state.payments[bid]["onChainState"] = "FundsLocked"  # the buyer paid while the seller was down
    fake.state.purchases[bid] = {"onChainState": "FundsLocked"}
    second = create_seller(s, masumi_http=masumi_http)
    async with second.router.lifespan_context(second), client(second) as c:
        await wait_status(c, started["job_id"], "completed")
        for _ in range(300):
            if fake.state.payments[bid]["onChainState"] == "ResultSubmitted":
                break
            await asyncio.sleep(0.01)
        assert fake.state.payments[bid]["onChainState"] == "ResultSubmitted"
    second.state.store.close()
    await masumi_http.aclose()


def test_store_round_trips_and_completed_jobs_are_not_respawned(tmp_path):
    store = SellerStore(str(tmp_path / "seller.db"))
    job = BoundedJobSpec(count=2)
    resp = StartJobResponse(status="success", job_id="j-done", price=70)
    store.put_start("p1", resp, job, DemoMode.junk)
    store.put_status(StatusResponse(job_id="j-done", status="failed"))
    (record,) = store.starts()
    assert (record.job, record.demo_mode, record.response, record.blockchain_id) == (job, DemoMode.junk, resp, None)
    assert store.statuses()["j-done"].status == "failed"
    store.close()


# ---------- STRICT_LIVE ----------

@pytest.mark.anyio
async def test_strict_live_seller_failure_is_503_and_errors_the_buyer_deal(tmp_path, monkeypatch):
    import app.seller.persona as persona

    async def fail(*args, **kwargs):
        raise RuntimeError("private-provider-diagnostics")

    monkeypatch.setattr(persona, "run_codex", fail)
    monkeypatch.setattr(Settings, "require_live", lambda self: None)
    s = settings(tmp_path, seller_llm_mode="codex", strict_live=True)

    seller = create_seller(s)
    async with client(seller) as c:
        r = await c.post("/negotiate", json={"deal_id": DEAL, "round": 0, "action": "open", "message": "hi",
                                             "job": {"count": 3}, "demo_mode": "honest"})
        assert r.status_code == 503
        assert "STRICT_LIVE" in r.json()["detail"] and "private-provider-diagnostics" not in r.text

    events, balances = await run_task(tmp_path, "honest", settings=s)
    errors = [e for e in events if e.type == "error"]
    assert errors and "STRICT_LIVE" in errors[0].data["message"]
    assert {"escrow_locked", "released"}.isdisjoint({e.type for e in events})
    assert balances["buyer"] == 1000


def test_strict_live_refuses_non_live_service_startup(tmp_path):
    s = settings(tmp_path, strict_live=True)  # mock agents, sample data, no voice
    with pytest.raises(ValueError, match="STRICT_LIVE"):
        create_buyer(s)
    with pytest.raises(ValueError, match="STRICT_LIVE"):
        create_seller(s)


# ---------- scripts send the token ----------

def test_act_sends_buyer_token_from_settings(monkeypatch):
    from scripts import act
    monkeypatch.setenv("API_TOKEN", "")
    assert act.buyer_headers() == {}
    monkeypatch.setenv("API_TOKEN", TOKEN)
    assert act.buyer_headers() == {"X-API-Token": TOKEN}


def test_launcher_reads_tokens_isolates_seller_state_and_sends_header(tmp_path, monkeypatch):
    import http.server
    import threading

    from tests.test_desktop_launcher import launcher

    for key in ("API_TOKEN", "SELLER_API_TOKEN", "STRICT_LIVE"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text('STRICT_LIVE=1\nAPI_TOKEN="from-env-file" # buyer\n'
                                   "export SELLER_API_TOKEN=seller-file\nOTHER=x\n", encoding="utf-8")
    artifact = tmp_path / "run"
    env = launcher.environment(tmp_path, artifact, "sample")
    assert (env["API_TOKEN"], env["SELLER_API_TOKEN"]) == ("from-env-file", "seller-file")
    assert env["STRICT_LIVE"] == "0" and "OTHER" not in env
    assert env["SELLER_STORE_PATH"] == str(artifact / "seller-usd.db")
    assert "STRICT_LIVE" not in launcher.environment(tmp_path, artifact, "configured")  # services read .env
    monkeypatch.setenv("API_TOKEN", "explicit")
    assert launcher.environment(tmp_path, artifact, "sample")["API_TOKEN"] == "explicit"

    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.headers.get("X-API-Token"))
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/deals"
        assert launcher.request(url, token="abc") == {}
        launcher.request(url)
    finally:
        server.shutdown()
        server.server_close()
    assert seen == ["abc", None]
