"""Buyer agent "Max" (owner: ziya). Port 8000.

Run from backend/: uv run uvicorn app.buyer.app:app --port 8000
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import replace

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.buyer.controls import Controls, ControlsUpdate
from app.buyer.events import EventBus
from app.buyer.guard import WalletGuard
from app.buyer.ledger import Ledger
from app.buyer.negotiator import make_negotiator
from app.buyer.orchestrator import Orchestrator
from app.buyer.payments import make_payments
from app.core.config import Settings, get_settings
from app.core.models import ApprovalDecision, TaskCreate, TaskCreated
from app.voice.tts import TTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # status polling would drown the event log


def create_app(settings: Settings | None = None, http: httpx.AsyncClient | None = None,
               masumi_http: httpx.AsyncClient | None = None) -> FastAPI:
    s = settings or get_settings()
    ledger = Ledger(s.ledger_path)
    bus = EventBus(ledger, simulated=s.simulated)
    guard = WalletGuard(ledger, make_payments(s, ledger, masumi_http), s.guard_cap, s.guard_approval_over)
    tts = TTS(s)
    controls = Controls(s, guard)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = http or httpx.AsyncClient(timeout=30)
        app.state.orch = Orchestrator(
            s, ledger, bus, guard, client,
            lambda ceiling, rounds: make_negotiator(replace(s, max_rounds=rounds), ceiling),
            tts, controls)
        try:
            await app.state.orch.resume_unfinished()
            yield
        finally:
            await app.state.orch.shutdown()
            if http is None:
                await client.aclose()

    app = FastAPI(title="Astra buyer (Max)", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=list(s.cors_origins),
                       allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
                       allow_methods=["GET", "POST", "PUT", "OPTIONS"], allow_headers=["content-type"])
    app.mount("/audio", StaticFiles(directory=s.audio_dir), name="audio")
    app.state.bus = bus
    app.state.ledger = ledger
    app.state.guard = guard
    app.state.controls = controls

    @app.get("/health")
    async def health():
        return {"ok": True, "payments_mode": s.payments_mode, "simulated": s.simulated, "llm_mode": s.llm_mode,
                "seller_llm_mode": s.seller_llm_mode,
                "tts_mode": s.tts_mode, "guard": {"cap": guard.cap, "approval_over": guard.approval_over}}

    @app.post("/tasks", response_model=TaskCreated)
    async def create_task(task: TaskCreate, request: Request):
        if controls.paused:
            raise HTTPException(423, "agents are paused; resume them to start a new task")
        return await request.app.state.orch.create_task(task)

    @app.get("/controls")
    async def get_controls():
        return controls.snapshot()

    @app.put("/controls")
    async def put_controls(update: ControlsUpdate):
        try:
            snap = controls.apply(update)
        except ValueError as e:
            raise HTTPException(422, str(e))
        bus.emit("controls_updated", **update.model_dump(exclude_none=True))
        return snap

    @app.post("/approvals/{deal_id}")
    async def approve(deal_id: str, decision: ApprovalDecision, request: Request):
        if not request.app.state.orch.approve(deal_id, decision.approve):
            raise HTTPException(404, f"no pending approval for {deal_id}")
        return {"ok": True}

    @app.get("/deals")
    async def deals():
        return ledger.all_deals()

    @app.get("/balances")
    async def balances():
        try:
            return {"simulated": s.simulated, **await guard.balances()}
        except NotImplementedError as e:
            raise HTTPException(501, str(e))

    @app.get("/events")
    async def events(request: Request):
        async def gen():
            async for ev in bus.stream():
                if await request.is_disconnected():
                    break
                yield ": ping\n\n" if ev is None else f"id: {ev.id}\ndata: {ev.model_dump_json()}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


app = create_app()
