"""Seller agent "Viktor" (owner: murad; Masumi wiring: ziya). Port 8001.

MIP-003 endpoints (/availability, /input_schema, /start_job, /status) + custom POST /negotiate.
Run from backend/: uv run uvicorn app.seller.app:app --port 8001
"""

import asyncio
import logging
import os
import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException

from app.core.config import Settings, get_settings
from app.core.masumi import LOCKED_STATES, MasumiClient, input_hash, output_hash
from app.core.models import (
    DemoMode,
    JobResult,
    BoundedJobSpec,
    JobSpec,
    NegotiateRequest,
    NegotiateResponse,
    StartJobRequest,
    StartJobResponse,
    StatusResponse,
)
from app.seller.job import run_job
from app.seller.persona import Viktor

log = logging.getLogger("astra.seller")
JOB_SECONDS = float(os.getenv("JOB_SECONDS", 2))
SUBMIT_TRIES = 3


def create_app(settings: Settings | None = None, masumi_http: httpx.AsyncClient | None = None) -> FastAPI:
    s = settings or get_settings()
    app = FastAPI(title="Astra seller (Viktor)")
    viktor = Viktor()
    jobs: dict[str, StatusResponse] = {}
    by_purchaser: dict[str, StartJobResponse] = {}
    running: set[asyncio.Task] = set()
    masumi = None if s.simulated else MasumiClient(s.masumi_payment_url, s.masumi_api_key, s.masumi_network,
                                                   masumi_http)

    def spawn(coro) -> None:
        t = asyncio.create_task(coro)
        running.add(t)
        t.add_done_callback(running.discard)

    async def work(job_id: str, job: JobSpec, mode: DemoMode) -> JobResult | None:
        jobs[job_id] = StatusResponse(job_id=job_id, status="running")
        await asyncio.sleep(JOB_SECONDS)
        try:
            result: JobResult = await run_job(job, mode, s)
            jobs[job_id] = StatusResponse(job_id=job_id, status="completed", result=result)
            return result
        except Exception:
            log.exception("job %s failed", job_id)
            jobs[job_id] = StatusResponse(job_id=job_id, status="failed")
            return None

    async def work_when_paid(job_id: str, blockchain_id: str, purchaser_id: str, job: JobSpec,
                             mode: DemoMode, deadline: float) -> None:
        """Masumi mode: wait until the buyer's funds are locked on-chain, work, submit the result hash."""
        try:
            await _work_when_paid(job_id, blockchain_id, purchaser_id, job, mode, deadline)
        except Exception:
            log.exception("job %s: Masumi step failed", job_id)
            if jobs[job_id].status != "completed":  # delivered work stays delivered
                jobs[job_id] = StatusResponse(job_id=job_id, status="failed")

    async def _work_when_paid(job_id, blockchain_id, purchaser_id, job, mode, deadline) -> None:
        while time.time() < deadline:
            payment = await masumi.resolve_payment(blockchain_id)
            if payment and payment.get("onChainState") in LOCKED_STATES:
                break
            await asyncio.sleep(s.masumi_poll_seconds)
        else:
            jobs[job_id] = StatusResponse(job_id=job_id, status="failed")
            log.warning("job %s: buyer never paid", job_id)
            return
        result = await work(job_id, job, mode)
        if result is None:
            return
        out_hash = output_hash(result.model_dump_json(), purchaser_id)
        for attempt in range(1, SUBMIT_TRIES + 1):
            try:
                await masumi.submit_result(blockchain_id, out_hash)
                return
            except Exception:
                if attempt == SUBMIT_TRIES:
                    log.exception("job %s: submit_result failed %d times; funds stay locked", job_id, attempt)
                    return
                await asyncio.sleep(s.masumi_poll_seconds * attempt)

    @app.get("/health")
    async def health():
        return {"ok": True, "agent": "viktor", "simulated": s.simulated, "apify_mode": s.apify_mode}

    @app.get("/availability")
    async def availability():
        return {"status": "available", "type": "masumi-agent", "message": "Viktor's Data Emporium is open"}

    @app.get("/input_schema")
    async def input_schema():
        return {"input_data": [
            {"id": "deal_id", "type": "string", "name": "Deal id agreed in /negotiate"},
            {"id": "agreed_price", "type": "number", "name": "Price agreed in /negotiate (tADA)"},
            {"id": "job", "type": "object", "name": "count, district, max_price_czk"},
        ]}

    @app.post("/negotiate", response_model=NegotiateResponse)
    async def negotiate(req: NegotiateRequest):
        return viktor.respond(req)

    @app.post("/start_job", response_model=StartJobResponse)
    async def start_job(req: StartJobRequest):
        # Idempotent per purchaser identifier: a buyer retry after a crash gets the same job back.
        purchaser = req.identifier_from_purchaser
        if purchaser in by_purchaser:
            return by_purchaser[purchaser]
        data = req.input_data
        deal = viktor.deals.get(data.get("deal_id", ""))
        price = float(data.get("agreed_price", 0))
        if deal is None or deal.agreed is None or deal.agreed != price:
            raise HTTPException(409, f"no agreed deal at {price} for {data.get('deal_id')}")
        job_id = f"j-{uuid.uuid4().hex[:8]}"
        try:
            job, mode = BoundedJobSpec(**data["job"]), DemoMode(data.get("demo_mode", "honest"))
        except (KeyError, TypeError, ValueError) as e:  # pydantic ValidationError is a ValueError
            raise HTTPException(422, "invalid job spec or demo_mode") from e

        if masumi is None:
            # SIMULATED: work starts immediately and trusts the buyer's simulated escrow.
            resp = StartJobResponse(status="success", job_id=job_id, price=price,
                                    message="SIMULATED: work starts without on-chain payment check")
            jobs[job_id] = StatusResponse(job_id=job_id, status="running")
            spawn(work(job_id, job, mode))
        else:
            in_hash = input_hash(data, purchaser)
            pay = await masumi.create_payment(s.masumi_agent_id, in_hash, purchaser, price,
                                              s.masumi_pay_by_minutes, s.masumi_submit_minutes)
            resp = StartJobResponse(
                status="success", job_id=job_id, price=price, message="awaiting Masumi payment",
                blockchainIdentifier=pay["blockchainIdentifier"], payByTime=str(pay["payByTime"]),
                submitResultTime=str(pay["submitResultTime"]), unlockTime=str(pay["unlockTime"]),
                externalDisputeUnlockTime=str(pay["externalDisputeUnlockTime"]),
                agentIdentifier=s.masumi_agent_id, sellerVKey=s.seller_vkey, inputHash=in_hash)
            jobs[job_id] = StatusResponse(job_id=job_id, status="awaiting_payment")
            deadline = time.time() + s.masumi_pay_by_minutes * 60
            spawn(work_when_paid(job_id, pay["blockchainIdentifier"], purchaser, job, mode, deadline))
        by_purchaser[purchaser] = resp
        return resp

    @app.get("/status", response_model=StatusResponse)
    async def status(job_id: str):
        if job_id not in jobs:
            raise HTTPException(404, f"unknown job {job_id}")
        return jobs[job_id]

    return app


app = create_app()
