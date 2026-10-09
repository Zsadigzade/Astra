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
from app.buyer.payments import MASUMI_DISABLED
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
from app.seller.job import answer_result, run_job
from app.seller.persona import NegotiationConflict, make_viktor
from app.seller.research import Progress
from app.seller.store import PersistentDeals, SellerStore

log = logging.getLogger("astra.seller")
JOB_SECONDS = float(os.getenv("JOB_SECONDS", 2))
SUBMIT_TRIES = 3


def create_app(settings: Settings | None = None, masumi_http: httpx.AsyncClient | None = None) -> FastAPI:
    s = settings or get_settings()
    s.require_live()  # STRICT_LIVE refuses to start on a configuration that would simulate providers
    if s.payments_mode != "simulated":  # Masumi is dormant: see app.buyer.payments.make_payments
        raise ValueError(MASUMI_DISABLED)
    store = SellerStore(s.seller_store_path or str(BACKEND_ROOT / "data" / "seller-usd.db"))  # blank = default
    viktor = make_viktor(s)
    # Jobs, start acknowledgements and agreements survive a seller restart (write-through to SQLite).
    viktor.deals = PersistentDeals(store)
    jobs: dict[str, StatusResponse] = store.statuses()
    by_purchaser: dict[str, StartJobResponse] = {r.purchaser: r.response for r in store.starts()}
    running: set[asyncio.Task] = set()
    masumi = None if s.simulated else MasumiClient(s.masumi_payment_url, s.masumi_api_key, s.masumi_network,
                                                   masumi_http)

    scouts: dict[str, asyncio.Task] = {}  # deal_id -> early work on the job, reused as the delivery
    scout_progress: dict[str, Progress] = {}
    job_progress: dict[str, Progress] = {}  # job_id -> what its research has done so far (only while running)
    MAX_SCOUTS = 3

    def scout_facts(deal_id: str) -> dict | None:
        """What Viktor really knows so far, safe to say out loud. Nothing here is made up."""
        task = scouts.get(deal_id)
        if task is None:
            return None
        progress = scout_progress.get(deal_id)
        if progress is not None:
            return progress.facts()
        if not task.done() or task.cancelled() or task.exception() is not None:
            return None  # nothing is claimed until the work has really finished
        flats = task.result().flats
        if not flats:
            return None
        return {"flats_ready": len(flats), "cheapest_czk": min(f.price_czk for f in flats)}

    def start_scout(req: NegotiateRequest) -> None:
        general = req.job.kind == "general"
        if (not s.answer_scout or req.action != "open" or req.demo_mode == DemoMode.junk or req.deal_id in scouts
                or (general and not s.answers_enabled)
                or (not general and s.apify_mode not in {"cached", "sample"})):  # never pay for a live scrape the buyer may walk from
            return
        if len([t for t in scouts.values() if not t.done()]) >= MAX_SCOUTS:
            return
        if general:
            progress = Progress()
            scout_progress[req.deal_id] = progress
            task = asyncio.create_task(answer_result(req.job, s, progress))
        else:
            task = asyncio.create_task(run_job(req.job, DemoMode.honest, s))
        def note_failure(t: asyncio.Task) -> None:
            if not t.cancelled() and t.exception() is not None:  # a failed scout is simply not used, but never silently
                log.warning("early work for deal %s failed: %s: %s", req.deal_id, type(t.exception()).__name__, t.exception())

        task.add_done_callback(note_failure)
        scouts[req.deal_id] = task
        running.add(task)
        task.add_done_callback(running.discard)

    def set_status(job_id: str, status: str, result: JobResult | None = None) -> None:
        jobs[job_id] = StatusResponse(job_id=job_id, status=status, result=result)
        store.put_status(jobs[job_id])

    def spawn(coro) -> None:
        t = asyncio.create_task(coro)
        running.add(t)
        t.add_done_callback(running.discard)

    async def work(job_id: str, job: JobSpec, mode: DemoMode, deal_id: str = "") -> JobResult | None:
        set_status(job_id, "running")
        scout = scouts.pop(deal_id, None) if mode != DemoMode.junk else None
        progress = scout_progress.pop(deal_id, None)
        general = getattr(job, "kind", "rental") == "general"
        if general and progress is None and mode != DemoMode.junk:
            progress = Progress()
        if progress is not None:
            job_progress[job_id] = progress
        if not general and scout is None:
            await asyncio.sleep(JOB_SECONDS)  # simulated work time for rentals only; real research has its own duration
        try:
            result: JobResult | None = None
            if scout is not None:  # the search that ran during the haggle is the delivery: no second model call
                try:
                    result = await scout
                except ValueError:
                    raise  # it ran to the end and found nothing usable: repeating it would only double the wait and the cost
                except Exception:
                    log.warning("job %s: early search failed, searching again", job_id)
            if result is None:
                result = await run_job(job, mode, s, progress)
            set_status(job_id, "completed", result)
            return result
        except Exception:
            log.exception("job %s failed", job_id)
            set_status(job_id, "failed")
            return None
        finally:
            job_progress.pop(job_id, None)

    async def work_when_paid(job_id: str, blockchain_id: str, purchaser_id: str, job: JobSpec,
                             mode: DemoMode, deadline: float, deal_id: str = "") -> None:
        """Masumi mode: wait until the buyer's funds are locked on-chain, work, submit the result hash."""
        try:
            await _work_when_paid(job_id, blockchain_id, purchaser_id, job, mode, deadline, deal_id)
        except Exception:
            log.exception("job %s: Masumi step failed", job_id)
            if jobs[job_id].status != "completed":  # delivered work stays delivered
                set_status(job_id, "failed")

    async def _work_when_paid(job_id, blockchain_id, purchaser_id, job, mode, deadline, deal_id="") -> None:
        while time.time() < deadline:
            payment = await masumi.resolve_payment(blockchain_id)
            if payment and payment.get("onChainState") in LOCKED_STATES:
                break
            await asyncio.sleep(s.masumi_poll_seconds)
        else:
            set_status(job_id, "failed")
            log.warning("job %s: buyer never paid", job_id)
            return
        await _deliver_paid(job_id, blockchain_id, purchaser_id, job, mode, deal_id)

    async def deliver_paid(job_id: str, blockchain_id: str, purchaser_id: str, job: JobSpec, mode: DemoMode,
                           deal_id: str = "") -> None:
        """Masumi resume: funds were confirmed locked before the restart; work and submit the result."""
        try:
            await _deliver_paid(job_id, blockchain_id, purchaser_id, job, mode, deal_id)
        except Exception:
            log.exception("job %s: Masumi step failed", job_id)
            if jobs[job_id].status != "completed":
                set_status(job_id, "failed")

    async def _deliver_paid(job_id, blockchain_id, purchaser_id, job, mode, deal_id="") -> None:
        result = await work(job_id, job, mode, deal_id)
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
            {"id": "agreed_price", "type": "number", "name": "Price agreed in /negotiate (USD)"},
            {"id": "job", "type": "object", "name": "count, district, max_price_czk"},
        ]}

    @app.post("/negotiate", response_model=NegotiateResponse)
    async def negotiate(req: NegotiateRequest):
        try:
            start_scout(req)
            response = await viktor.respond_async(req, scout_facts(req.deal_id))
            if response.action == "walk":  # no deal, no work: stop the early search
                dropped = scouts.pop(req.deal_id, None)
                scout_progress.pop(req.deal_id, None)
                if dropped is not None:
                    dropped.cancel()
            return response
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
            spawn(work(job_id, job, mode, data.get("deal_id", "")))
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
            spawn(work_when_paid(job_id, pay["blockchainIdentifier"], purchaser, job, mode, deadline, data.get("deal_id", "")))
        return resp

    @app.get("/status", response_model=StatusResponse)
    async def status(job_id: str):
        if job_id not in jobs:
            raise HTTPException(404, f"unknown job {job_id}")
        state, progress = jobs[job_id], job_progress.get(job_id)
        if state.status == "running" and progress is not None:
            return state.model_copy(update={"progress": progress.public()})
        return state

    return app


app = create_app()
