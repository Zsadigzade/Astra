"""General requests end to end: parse preview, agents follow the real job, other districts deliver and verify."""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from app.buyer.app import create_app as create_buyer
from app.buyer.negotiator import CodexMax
from app.buyer.verifier import verify
from app.core.config import Settings
from app.core.models import DemoMode, JobSpec, describe_job
from app.seller import apify
from app.seller.app import create_app as create_seller
from app.seller.job import run_job, sample_flats


@pytest.fixture
def anyio_backend():
    return "asyncio"


def settings(tmp_path, **kw):
    return Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                    seller_url="http://seller", apify_cache_path=str(tmp_path / "flats.json"), **kw)


@pytest.mark.anyio
async def test_parse_endpoint_previews_without_creating_anything(tmp_path):
    buyer = create_buyer(settings(tmp_path), http=httpx.AsyncClient())
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            ok = (await c.post("/requests/parse", json={"text": "10 apartments in Prague 2, max 30k"})).json()
            assert ok["ok"] and ok["job"] == {"count": 10, "district": "Praha 2", "max_price_czk": 30_000}
            no = (await c.post("/requests/parse", json={"text": "buy me a car"})).json()
            assert not no["ok"] and no["job"] is None and no["examples"]
            assert (await c.post("/requests/parse", json={"text": "x" * 601})).status_code == 422
            assert buyer.state.ledger.all_deals() == []
            assert [e for e in buyer.state.bus.history if e.type == "task_created"] == []


def test_max_prompt_describes_the_actual_job():
    job = JobSpec(count=7, district="Praha 3", max_price_czk=18_000)
    text = CodexMax(Settings(llm_mode="codex"), 10, job).instructions
    assert "7 flats in Praha 3 under 18,000 CZK per month" in text and "Prague 7" not in text
    assert describe_job(JobSpec(count=1)) == "1 flat in Praha 7 under 25,000 CZK per month"


@pytest.mark.anyio
async def test_viktor_opens_with_the_requested_count_and_district(tmp_path):
    seller = create_seller(settings(tmp_path))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=seller), base_url="http://seller") as c:
        r = await c.post("/negotiate", json={"deal_id": "b" * 20, "round": 0, "action": "open",
                                             "job": {"count": 12, "district": "Praha 2", "max_price_czk": 30000}})
        msg = r.json()["message"]
        assert "12 flats in Praha 2" in msg and "Twenty" not in msg


@pytest.mark.parametrize("district", ["Praha 1", "Praha 2", "Praha 5", "Praha 8", "Praha 10", "Praha 14"])
@pytest.mark.anyio
async def test_sample_delivery_for_any_district_passes_the_verifier(district):
    job = JobSpec(count=8, district=district, max_price_czk=30_000)
    result = await run_job(job, DemoMode.honest, Settings(apify_mode="sample"))
    ok, checks = verify(result, job)
    assert ok, checks
    assert len(result.flats) == 8 and all(district in f.district for f in result.flats)


@pytest.mark.anyio
async def test_junk_still_fails_verification_for_other_districts():
    job = JobSpec(count=8, district="Praha 2", max_price_czk=30_000)
    result = await run_job(job, DemoMode.junk, Settings(apify_mode="sample"))
    assert verify(result, job)[0] is False


@pytest.mark.anyio
async def test_a_deal_for_another_district_runs_end_to_end(tmp_path):
    s = settings(tmp_path)
    seller_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_seller(s)), base_url="http://seller")
    buyer = create_buyer(s, http=seller_http)
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            r = await c.post("/tasks", json={"job": {"count": 6, "district": "Praha 2", "max_price_czk": 30000}})
            assert r.status_code == 200
            for _ in range(600):
                if {"released", "error", "blocked"} & {e.type for e in buyer.state.bus.history}:
                    break
                await asyncio.sleep(0.01)
    await seller_http.aclose()
    types = [e.type for e in buyer.state.bus.history]
    assert "released" in types and "error" not in types
    delivered = next(e for e in buyer.state.bus.history if e.type == "delivered")
    assert delivered.data["items"] == 6 and all("Praha 2" in f["district"] for f in delivered.data["result"]["flats"])


def _row(n, area):
    return {"title": "Rent apartment", "dealType": "rent", "propertyType": "apartment", "city": f"Praha {area}",
            "locality": f"Ulice, Praha {area}", "district": "X", "price": 20000, "currency": "CZK", "priceUnit": "per month",
            "url": f"https://www.sreality.cz/detail/pronajem/byt/2+kk/praha/{n}"}


@pytest.mark.anyio
async def test_live_scrape_for_another_request_does_not_clobber_the_saved_demo_cache(tmp_path, monkeypatch):
    s = settings(tmp_path, apify_mode="apify", apify_token="t")
    demo = JobSpec(count=1, district="Praha 7", max_price_czk=25000)
    constructor = httpx.AsyncClient

    def handler(request):
        if request.url.path.endswith("/runs"):
            return httpx.Response(201, json={"data": {"id": "r1", "status": "SUCCEEDED", "defaultDatasetId": "d1"}})
        return httpx.Response(200, json=[_row(1, 7), _row(2, 2)])

    monkeypatch.setattr(apify.httpx, "AsyncClient", lambda **kw: constructor(**kw, transport=httpx.MockTransport(handler)))
    await run_job(demo, DemoMode.honest, s)  # saves the Praha 7 cache
    before = json.loads(apify.cache_path(demo, s).read_text(encoding="utf-8"))["job"]
    other = JobSpec(count=1, district="Praha 2", max_price_czk=25000)
    result = await run_job(other, DemoMode.honest, s)  # live Praha 2 run succeeds...
    assert result.source == "apify" and "Praha 2" in result.flats[0].district
    after = json.loads(apify.cache_path(demo, s).read_text(encoding="utf-8"))["job"]
    assert after == before == demo.model_dump()  # ...but the demo cache is untouched
    assert apify.load_cache(other, s).flats == result.flats
