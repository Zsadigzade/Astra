"""Seller agent "Viktor" (owner: murad). Port 8001.

MIP-003 endpoints (/availability, /input_schema, /start_job, /status) + custom POST /negotiate.
Run: uv run uvicorn seller.app:app --port 8001
"""

import asyncio
import logging
import os
import uuid

from fastapi import FastAPI, HTTPException

from seller.job import run_job
from seller.persona import Viktor
from shared.config import Settings, get_settings
from shared.models import (
    DemoMode,
    JobResult,
    JobSpec,
    NegotiateRequest,
    NegotiateResponse,
    StartJobRequest,
    StartJobResponse,
    StatusResponse,
)

log = logging.getLogger("astra.seller")
JOB_SECONDS = float(os.getenv("JOB_SECONDS", 2))


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or get_settings()
    app = FastAPI(title="Astra seller (Viktor)")
    viktor = Viktor()
    jobs: dict[str, StatusResponse] = {}
    by_purchaser: dict[str, StartJobResponse] = {}
    running: set[asyncio.Task] = set()

    async def work(job_id: str, job: JobSpec, mode: DemoMode) -> None:
        jobs[job_id] = StatusResponse(job_id=job_id, status="running")
        await asyncio.sleep(JOB_SECONDS)
        try:
            result: JobResult = await run_job(job, mode, s)
            jobs[job_id] = StatusResponse(job_id=job_id, status="completed", result=result)
        except Exception:
            log.exception("job %s failed", job_id)
            jobs[job_id] = StatusResponse(job_id=job_id, status="failed")

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
        if req.identifier_from_purchaser in by_purchaser:
            return by_purchaser[req.identifier_from_purchaser]
        data = req.input_data
        deal = viktor.deals.get(data.get("deal_id", ""))
        price = float(data.get("agreed_price", 0))
        if deal is None or deal.agreed is None or deal.agreed != price:
            raise HTTPException(409, f"no agreed deal at {price} for {data.get('deal_id')}")
        job_id = f"j-{uuid.uuid4().hex[:8]}"
        # TODO(murad/ziya): masumi mode -> create payment request, status awaiting_payment until funds lock.
        # SIMULATED mode starts work immediately and trusts the buyer's simulated escrow.
        resp = StartJobResponse(status="success", job_id=job_id, price=price,
                                message="SIMULATED: work starts without on-chain payment check" if s.simulated else "")
        by_purchaser[req.identifier_from_purchaser] = resp
        jobs[job_id] = StatusResponse(job_id=job_id, status="running")
        t = asyncio.create_task(work(job_id, JobSpec(**data["job"]), DemoMode(data.get("demo_mode", "honest"))))
        running.add(t)
        t.add_done_callback(running.discard)
        return resp

    @app.get("/status", response_model=StatusResponse)
    async def status(job_id: str):
        if job_id not in jobs:
            raise HTTPException(404, f"unknown job {job_id}")
        return jobs[job_id]

    return app


app = create_app()
