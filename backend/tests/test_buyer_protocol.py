"""Buyer binds remote messages to the exact negotiation and funded job."""

import asyncio
import json

import httpx
import pytest

from app.buyer.app import create_app
from app.core.config import Settings
from app.core.models import JobResult, JobSpec
from app.seller.job import sample_flats


@pytest.mark.anyio
@pytest.mark.parametrize("fault", ["deal", "round", "open_accept", "accept_price", "ack", "start_error", "start_price", "empty_job", "status_job", "failed_with_result"])
async def test_mismatched_seller_messages_cannot_release_money(tmp_path, fault):
    def seller(request):
        if request.url.path == "/negotiate":
            body = json.loads(request.content)
            response = {"deal_id": body["deal_id"], "round": body["round"],
                        "action": "counter", "price": 7, "message": "Seven."}
            if fault == "deal":
                response["deal_id"] = "another-deal"
            elif fault == "round":
                response["round"] += 1
            elif fault == "open_accept":
                response["action"] = "accept"
            elif fault == "accept_price" and body["action"] == "counter":
                response.update(action="accept", price=9)
            elif body["action"] == "accept":
                response["action"] = "counter" if fault == "ack" else "accept"
            return httpx.Response(200, json=response)
        if request.url.path == "/start_job":
            return httpx.Response(200, json={
                "status": "error" if fault == "start_error" else "success",
                "job_id": " " if fault == "empty_job" else "this-job",
                "price": 8 if fault == "start_price" else 7})
        assert request.url.path == "/status"
        return httpx.Response(200, json={
            "job_id": "different-job" if fault == "status_job" else "this-job",
            "status": "failed" if fault == "failed_with_result" else "completed",
            "result": JobResult(flats=sample_flats(JobSpec()), source="sample").model_dump()})

    settings = Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                        seller_url="http://seller")
    async with httpx.AsyncClient(transport=httpx.MockTransport(seller)) as seller_http:
        buyer = create_app(settings, http=seller_http)
        async with buyer.router.lifespan_context(buyer):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as client:
                response = await client.post("/tasks", json={})
                assert response.status_code == 200
                await asyncio.wait_for(asyncio.gather(*buyer.state.orch.tasks), timeout=2)
                balances = (await client.get("/balances")).json()
        events = buyer.state.bus.history
        assert "released" not in {event.type for event in events}
        assert balances["seller"] == 0
        if fault == "status_job":
            assert balances["escrow"] == 7
            assert buyer.state.ledger.unfinished()  # Keep the original funded job recoverable.
        else:
            assert balances["buyer"] == 100 and balances["escrow"] == 0
        if fault == "failed_with_result":
            assert "refunded" in {event.type for event in events}
        else:
            assert "error" in {event.type for event in events}


@pytest.mark.anyio
@pytest.mark.parametrize("job", [{"count": 0}, {"count": -1}, {"count": 201},
                                 {"district": "   "}, {"district": "x" * 101},
                                 {"max_price_czk": 0}, {"max_price_czk": -1}])
async def test_invalid_jobs_are_rejected_before_negotiation(tmp_path, job):
    def unexpected(request):
        pytest.fail("invalid jobs must not contact the seller")

    settings = Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as seller_http:
        buyer = create_app(settings, http=seller_http)
        async with buyer.router.lifespan_context(buyer):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as client:
                assert (await client.post("/tasks", json={"job": job})).status_code == 422
                assert (await client.get("/deals")).json() == []
