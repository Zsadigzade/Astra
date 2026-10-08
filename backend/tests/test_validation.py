"""Network-facing input bounds (found by the end-to-end audit: count=1e9 stalled the seller for every deal)."""

import httpx
import pytest

from app.buyer.app import create_app as create_buyer
from app.core.config import Settings
from app.seller.app import create_app as create_seller


@pytest.fixture
def anyio_backend():
    return "asyncio"


def settings(tmp_path):
    return Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"), seller_url="http://seller")


@pytest.mark.anyio
@pytest.mark.parametrize("job", [{"count": 0}, {"count": -3}, {"count": 101}, {"count": 10**9}, {"max_price_czk": 0},
                                 {"max_price_czk": -1}, {"max_price_czk": 10**9}, {"district": ""}, {"district": "x" * 65}])
async def test_tasks_reject_out_of_range_jobs(tmp_path, job):
    buyer = create_buyer(settings(tmp_path), http=httpx.AsyncClient())
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            assert (await c.post("/tasks", json={"job": job})).status_code == 422
            assert buyer.state.ledger.all_deals() == []  # nothing was created


@pytest.mark.anyio
async def test_tasks_reject_huge_budget_and_text(tmp_path):
    buyer = create_buyer(settings(tmp_path), http=httpx.AsyncClient())
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            assert (await c.post("/tasks", json={"budget": 10**6})).status_code == 422
            assert (await c.post("/tasks", json={"text": "x" * 501})).status_code == 422


@pytest.mark.anyio
async def test_seller_negotiate_rejects_out_of_range_job(tmp_path):
    seller = create_seller(settings(tmp_path))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=seller), base_url="http://seller") as c:
        r = await c.post("/negotiate", json={"deal_id": "d" * 20, "round": 0, "action": "open", "job": {"count": 10**9}})
        assert r.status_code == 422


@pytest.mark.anyio
async def test_seller_start_job_rejects_bad_job_with_422_not_500(tmp_path):
    seller = create_seller(settings(tmp_path))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=seller), base_url="http://seller") as c:
        deal = "a" * 20
        r = await c.post("/negotiate", json={"deal_id": deal, "round": 0, "action": "open"})
        assert r.status_code == 200
        price = r.json()["price"]
        r = await c.post("/negotiate", json={"deal_id": deal, "round": 1, "action": "accept", "offer": price})
        assert r.status_code == 200 and r.json()["action"] == "accept"
        body = {"identifier_from_purchaser": deal, "input_data": {"deal_id": deal, "agreed_price": price, "job": {"count": 10**9}}}
        assert (await c.post("/start_job", json=body)).status_code == 422


@pytest.mark.anyio
async def test_error_event_always_has_a_message(tmp_path):
    from app.buyer.orchestrator import Orchestrator

    s = settings(tmp_path)
    buyer = create_buyer(s, http=httpx.AsyncClient())
    async with buyer.router.lifespan_context(buyer):
        orch: Orchestrator = buyer.state.orch
        deal = orch.ledger.create_deal("e" * 20, "t-x", "{}", s.seller_url)  # noqa: F841

        async def boom():
            raise httpx.ReadTimeout("")  # str() is empty, as in the real stalled-seller case

        await orch._safe("t-x", "e" * 20, boom())
        err = [e for e in buyer.state.bus.history if e.type == "error"][-1]
        assert err.data["message"] == "ReadTimeout"


@pytest.mark.anyio
@pytest.mark.parametrize("origin,allowed", [
    ("http://localhost:5173", True), ("http://localhost:5174", True), ("http://127.0.0.1:5173", True),
    ("https://evil.example", False), ("http://localhost.evil.example", False), ("http://evil.example:5173", False),
])
async def test_cors_allows_only_local_dashboards(tmp_path, origin, allowed):
    buyer = create_buyer(settings(tmp_path), http=httpx.AsyncClient())
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            r = await c.options("/approvals/x", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                         "Access-Control-Request-Headers": "content-type"})
            assert ("access-control-allow-origin" in r.headers) is allowed


@pytest.mark.anyio
async def test_cors_extra_origins_from_settings(tmp_path):
    s = Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"), seller_url="http://seller",
                 cors_origins=("https://demo.example",))
    buyer = create_buyer(s, http=httpx.AsyncClient())
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            r = await c.options("/controls", headers={"Origin": "https://demo.example", "Access-Control-Request-Method": "PUT"})
            assert r.headers.get("access-control-allow-origin") == "https://demo.example"
