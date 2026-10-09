"""Seller agent "Viktor" (owner: murad; Masumi wiring: ziya). Port 8001.

MIP-003 endpoints (/availability, /input_schema, /start_job, /status) + custom POST /negotiate.
Run from backend/: uv run uvicorn app.seller.app:app --port 8001
"""

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException

from app.core.auth import TokenAuth, open_paths
from app.core.config import BACKEND_ROOT, LiveProviderUnavailable, Settings, get_settings
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
from app.seller.persona import NegotiationConflict, make_viktor
from app.seller.store import PersistentDeals, SellerStore

log = logging.getLogger("astra.seller")
JOB_SECONDS = float(os.getenv("JOB_SECONDS", 2))
SUBMIT_TRIES = 3


def create_app(settings: Settings | None = None, masumi_http: httpx.AsyncClient | None = None) -> FastAPI:
    s = settings or get_settings()
    s.require_live()  # STRICT_LIVE refuses to start on a configuration that would simulate providers
    store = SellerStore(s.seller_store_path or str(BACKEND_ROOT / "data" / "seller.db"))  # blank = default
    viktor = make_viktor(s)
    # Jobs, start acknowledgements and agreements survive a seller restart (write-through to SQLite).
    viktor.deals = PersistentDeals(store)
    jobs: dict[str, StatusResponse] = store.statuses()
    by_purchaser: dict[str, StartJobResponse] = {r.purchaser: r.response for r in store.starts()}
    running: set[asyncio.Task] = set()
    masumi = None if s.simulated else MasumiClient(s.masumi_payment_url, s.masumi_api_key, s.masumi_network,
                                                   masumi_http)

    def set_status(job_id: str, status: str, result: JobResult | None = None) -> None:
        jobs[job_id] = StatusResponse(job_id=job_id, status=status, result=result)
        store.put_status(jobs[job_id])

    def spawn(coro) -> None:
        t = asyncio.create_task(coro)
        running.add(t)
        t.add_done_callback(running.discard)

    async def work(job_id: str, job: JobSpec, mode: DemoMode) -> JobResult | None:
        set_status(job_id, "running")
        await asyncio.sleep(JOB_SECONDS)
        try:
            result: JobResult = await run_job(job, mode, s)
            set_status(job_id, "completed", result)
            return result
        except Exception:
            log.exception("job %s failed", job_id)
            set_status(job_id, "failed")
            return None

    async def work_when_paid(job_id: str, blockchain_id: str, purchaser_id: str, job: JobSpec,
                             mode: DemoMode, deadline: float) -> None:
        """Masumi mode: wait until the buyer's funds are locked on-chain, work, submit the result hash."""
        try:
            await _work_when_paid(job_id, blockchain_id, purchaser_id, job, mode, deadline)
        except Exception:
            log.exception("job %s: Masumi step failed", job_id)
            if jobs[job_id].status != "completed":  # delivered work stays delivered
                set_status(job_id, "failed")

    async def _work_when_paid(job_id, blockchain_id, purchaser_id, job, mode, deadline) -> None:
        while time.time() < deadline:
            payment = await masumi.resolve_payment(blockchain_id)
            if payment and payment.get("onChainState") in LOCKED_STATES:
                break
            await asyncio.sleep(s.masumi_poll_seconds)
        else:
            set_status(job_id, "failed")
            log.warning("job %s: buyer never paid", job_id)
            return
        await _deliver_paid(job_id, blockchain_id, purchaser_id, job, mode)

    async def deliver_paid(job_id: str, blockchain_id: str, purchaser_id: str, job: JobSpec, mode: DemoMode) -> None:
        """Masumi resume: funds were confirmed locked before the restart; work and submit the result."""
        try:
            await _deliver_paid(job_id, blockchain_id, purchaser_id, job, mode)
        except Exception:
            log.exception("job %s: Masumi step failed", job_id)
            if jobs[job_id].status != "completed":
                set_status(job_id, "failed")

    async def _deliver_paid(job_id, blockchain_id, purchaser_id, job, mode) -> None:
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

    def resume() -> None:
        """Restart recovery: re-spawn work that was in flight when the seller stopped."""
        for record in store.starts():
            status = jobs.get(record.job_id)
            state = status.status if status else None
            if masumi is None:
                if record.blockchain_id is not None:
                    if state in {"running", "awaiting_payment"}:
                        log.warning("job %s belongs to Masumi payments; not resumed in SIMULATED mode",
                                    record.job_id)
                elif state == "running":
                    log.info("resuming SIMULATED job %s after restart", record.job_id)
                    spawn(work(record.job_id, record.job, record.demo_mode))
            elif record.blockchain_id is None:
                if state in {"running", "awaiting_payment"}:
                    log.warning("job %s is SIMULATED; not resumed in Masumi mode", record.job_id)
            elif state == "awaiting_payment":
                log.info("resuming Masumi payment watch for job %s after restart", record.job_id)
                spawn(work_when_paid(record.job_id, record.blockchain_id, record.purchaser, record.job,
                                     record.demo_mode, record.deadline or 0.0))
            elif state == "running":
                log.info("resuming paid Masumi job %s after restart", record.job_id)
                spawn(deliver_paid(record.job_id, record.blockchain_id, record.purchaser, record.job,
                                   record.demo_mode))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resume()
        try:
            yield
        finally:
            # Unfinished work stays persisted as running/awaiting_payment and resumes on the next start.
            for task in list(running):
                task.cancel()
            await asyncio.gather(*running, return_exceptions=True)

    app = FastAPI(title="Astra seller (Viktor)", lifespan=lifespan)
    app.add_middleware(TokenAuth, token=s.seller_api_token, is_open=open_paths("/health", "/availability"))
    app.state.store = store
    app.state.viktor = viktor

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
        try:
            return await viktor.respond_async(req)
        except NegotiationConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except LiveProviderUnavailable as exc:  # STRICT_LIVE: no scripted substitute for a failed live turn
            raise HTTPException(503, str(exc)) from exc

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
            store.put_start(purchaser, resp, job, mode)
            set_status(job_id, "running")
            by_purchaser[purchaser] = resp
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
            deadline = time.time() + s.masumi_pay_by_minutes * 60
            store.put_start(purchaser, resp, job, mode, pay["blockchainIdentifier"], deadline)
            set_status(job_id, "awaiting_payment")
            by_purchaser[purchaser] = resp
            spawn(work_when_paid(job_id, pay["blockchainIdentifier"], purchaser, job, mode, deadline))
        return resp

    @app.get("/status", response_model=StatusResponse)
    async def status(job_id: str):
        if job_id not in jobs:
            raise HTTPException(404, f"unknown job {job_id}")
        return jobs[job_id]

    return app


app = create_app()
