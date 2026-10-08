"""Buyer flow: haggle -> guard -> start_job -> guard.pay (escrow) -> poll -> verify -> release | refund."""

import asyncio
import logging
import math
import os
import uuid
from collections.abc import Callable

import httpx
from pydantic import ValidationError

from app.buyer.controls import Controls
from app.buyer.events import EventBus
from app.buyer.guard import Verdict, WalletGuard
from app.buyer.ledger import Ledger
from app.buyer.negotiator import MockMax, Negotiator
from app.buyer.verifier import verify
from app.core.config import Settings
from app.core.models import (
    DemoMode,
    NegotiateRequest,
    NegotiateResponse,
    StartJobRequest,
    StartJobResponse,
    StatusResponse,
    TaskCreate,
    TaskCreated,
)
from app.voice.tts import TTS

log = logging.getLogger("astra.buyer")
APPROVAL_TIMEOUT = 300  # seconds the dashboard has to approve
JOB_TIMEOUT = 45 * 60  # seconds to wait for delivery
SETTLED = ("released", "refunded", "blocked", "walked")


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        ledger: Ledger,
        bus: EventBus,
        guard: WalletGuard,
        http: httpx.AsyncClient,
        make_max: Callable[[float, int], Negotiator],
        tts: TTS,
        controls: Controls,
    ):
        self.s = settings
        self.ledger = ledger
        self.bus = bus
        self.guard = guard
        self.http = http
        self.make_max = make_max
        self.tts = tts
        self.controls = controls
        self.approvals: dict[str, asyncio.Future[bool]] = {}
        self.tasks: set[asyncio.Task] = set()

    # ---------- entry points ----------

    async def create_task(self, task: TaskCreate) -> TaskCreated:
        # deal_id doubles as Masumi identifierFromPurchaser: hex, 14-26 chars
        task_id, deal_id = f"t-{uuid.uuid4().hex[:8]}", uuid.uuid4().hex[:20]
        self.ledger.create_deal(deal_id, task_id, task.model_dump_json(), self.s.seller_url)
        # Persist the deliberate crash label so dashboard replay retains it after
        # the buyer restarts with CRASH_AFTER_LOCK disabled.
        self.bus.emit("task_created", task_id, deal_id,
                      staged=self.s.crash_after_lock or self._staged(task), text=task.text,
                      budget=task.budget, demo_mode=task.demo_mode)
        self._spawn(self.run(task_id, deal_id, task))
        return TaskCreated(task_id=task_id, deal_id=deal_id)

    def approve(self, deal_id: str, ok: bool) -> bool:
        fut = self.approvals.get(deal_id)
        if not fut or fut.done():
            return False
        fut.set_result(ok)
        return True

    async def shutdown(self) -> None:
        # Cancel owned work before closing HTTP resources. Payment intent and approval
        # state remain in SQLite for the next startup; cancellation is not a deal failure.
        pending = tuple(self.tasks)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    async def resume_unfinished(self) -> None:
        """Act 3: after a crash, finish open deals. guard.pay sees them paid and does not pay twice."""
        for deal in self.ledger.unfinished():
            try:
                task = TaskCreate.model_validate_json(deal["task_json"])
            except ValidationError:
                # Older versions admitted jobs that current validation rejects.
                # Preserve the original record and any escrow for manual review;
                # one invalid saved task must not prevent other deals recovering.
                log.warning("saved task for deal %s needs review before recovery", deal["deal_id"])
                self.bus.emit("error", deal["task_id"], deal["deal_id"],
                              message="Saved task no longer passes validation; recovery needs manual review. "
                                      "The deal and any escrow are unchanged.")
                continue
            log.info("resuming deal %s (status %s)", deal["deal_id"], deal["status"])
            self._spawn(self._safe(deal["task_id"], deal["deal_id"], self.pay_and_deliver(
                deal["task_id"], deal["deal_id"], task, deal["price"], approved=bool(deal["approved"]))))

    async def run(self, task_id: str, deal_id: str, task: TaskCreate) -> None:
        price = await self._safe(task_id, deal_id, self.haggle(task_id, deal_id, task))
        if price is not None:
            await self._safe(task_id, deal_id, self.pay_and_deliver(task_id, deal_id, task, price))

    async def _safe(self, task_id: str, deal_id: str, coro):
        try:
            return await coro
        except Exception as e:
            log.exception("deal %s failed", deal_id)
            # A settled deal stays settled; a funded one stays resumable (Ledger.unfinished).
            # A failed lock response can mean the provider accepted the payment but its
            # reply was lost. Keep the persisted intent so restart resolves it idempotently.
            if self.ledger.get(deal_id)["status"] not in (*SETTLED, "paying"):
                self.ledger.update(deal_id, status="error")
            self.bus.emit("error", task_id, deal_id, message=str(e) or type(e).__name__)  # e.g. ReadTimeout has no text

    # ---------- haggle ----------

    async def haggle(self, task_id: str, deal_id: str, task: TaskCreate) -> float | None:
        staged = self._staged(task)
        ceiling = min(self.guard.cap, task.budget)
        # A runtime update affects the next deal; this deal's prompt and loop agree.
        max_rounds = self.controls.max_rounds
        # The advertised con is a STAGED test of the guard, with deliberately gullible dialogue.
        max_ = MockMax(ceiling) if task.demo_mode == DemoMode.con else self.make_max(ceiling, max_rounds)
        req = NegotiateRequest(deal_id=deal_id, round=0, action="open", job=task.job, demo_mode=task.demo_mode)
        my_last: float | None = None
        for rnd in range(max_rounds):
            resp = await self._negotiate(req)
            await self._say(task_id, deal_id, "viktor", resp.message, resp.price, resp.action, staged,
                            backend=resp.backend, fallback_reason=resp.fallback_reason)
            if resp.action == "walk":
                return self._walked(task_id, deal_id, "seller walked away")
            if resp.action == "accept":
                return self._agreed(task_id, deal_id, resp.price, staged)
            move = await max_.next_move(resp, my_last)
            await self._say(task_id, deal_id, "max", move.message, move.price, move.action, staged,
                            backend=getattr(max_, "last_backend", "mock"),
                            fallback_reason=getattr(max_, "fallback_reason", None))
            if move.action in ("accept", "walk"):
                acknowledgement = await self._negotiate(req.model_copy(update={
                    "round": rnd + 1, "action": move.action,
                    "offer": resp.price, "message": move.message}))
                if move.action == "walk":
                    return self._walked(task_id, deal_id, "buyer walked away")
                await self._say(task_id, deal_id, "viktor", acknowledgement.message,
                                acknowledgement.price, acknowledgement.action, staged,
                                backend=acknowledgement.backend,
                                fallback_reason=acknowledgement.fallback_reason)
                return self._agreed(task_id, deal_id, resp.price, staged)
            my_last = move.price
            req = req.model_copy(update={"round": rnd + 1, "action": "counter", "offer": move.price,
                                         "message": move.message})
        return self._walked(task_id, deal_id, f"no deal after {max_rounds} rounds")

    # ---------- pay, deliver, settle ----------

    async def pay_and_deliver(self, task_id: str, deal_id: str, task: TaskCreate, price: float,
                              approved: bool = False) -> None:
        staged = self._staged(task)
        deal = self.ledger.get(deal_id)
        seller = deal["seller_url"]

        if not deal["escrow_ref"]:
            # Guard runs BEFORE the seller is even asked to start: a blocked deal costs nothing.
            d = self.guard.evaluate(price, task_id, task.budget, deal_id)
            if d.verdict is Verdict.block:
                return await self._blocked(task_id, deal_id, task, price, d.reason, staged)
            if d.verdict is Verdict.needs_approval and not approved:
                approved = await self._wait_for_approval(task_id, deal_id, price, d.reason, staged)
                if not approved:
                    return await self._blocked(task_id, deal_id, task, price, "human declined", staged)

        # Reuse the stored start: a restarted seller would issue a new job and blockchainIdentifier,
        # and the escrow already locked against the old one would never match.
        if deal["start_json"]:
            start = StartJobResponse.model_validate_json(deal["start_json"])
            self._validate_start(start, price)
        else:
            start = await self._start_job(seller, deal_id, price, task)
            self.ledger.update(deal_id, job_id=start.job_id, start_json=start.model_dump_json())
        out = await self.guard.pay(deal_id, price, task_id, task.budget, seller, start, approved=approved)
        if out.kind == "blocked":
            return await self._blocked(task_id, deal_id, task, price, out.reason, staged)
        if out.kind == "needs_approval":  # should not happen: approval handled above
            return await self._blocked(task_id, deal_id, task, price, out.reason, staged)
        if out.kind == "already_paid":
            self.bus.emit("already_paid", task_id, deal_id, staged, ref=out.ref, price=price,
                          message=f"deal {deal_id} already paid, not paying again", **out.info)
        else:
            self.bus.emit("escrow_locked", task_id, deal_id, staged, ref=out.ref, price=price, **out.info)
        await self._emit_balances(task_id, deal_id)

        if self.s.crash_after_lock and out.kind == "locked":
            log.warning("[STAGED] CRASH_AFTER_LOCK=1: killing buyer mid-deal (Act 3)")
            os._exit(1)

        await self._deliver_and_settle(task_id, deal_id, task, start.job_id, staged)

    async def _deliver_and_settle(self, task_id: str, deal_id: str, task: TaskCreate, job_id: str,
                                  staged: bool) -> None:
        deal = self.ledger.get(deal_id)
        status = await self._poll(deal["seller_url"], job_id)
        self.ledger.update(deal_id, status="delivered")
        # A failed job cannot turn into successful delivery by including stale results.
        result = status.result if status.status == "completed" else None
        n = len(result.flats) if result else 0
        self.bus.emit("delivered", task_id, deal_id, staged, job_status=status.status, items=n,
                      source=result.source if result else None,
                      result=result.model_dump() if result else None)
        ok, checks = verify(result, task.job)
        self.bus.emit("verified", task_id, deal_id, staged, ok=ok, checks=checks)
        if ok:
            info = await self.guard.release(deal_id)
            self.ledger.update(deal_id, status="released")
            self.bus.emit("released", task_id, deal_id, staged, price=deal["price"], **info)
        else:
            info = await self.guard.refund(deal_id)
            self.ledger.update(deal_id, status="refunded")
            self.bus.emit("refunded", task_id, deal_id, staged, price=deal["price"],
                          failed=[k for k, v in checks.items() if not v], **info)
        await self._emit_balances(task_id, deal_id)

    # ---------- helpers ----------

    async def _negotiate(self, req: NegotiateRequest) -> NegotiateResponse:
        # Leave time for the seller's CLI deadline, cleanup and scripted fallback.
        read_timeout = 30.0
        if (self.s.seller_llm_mode == "codex" and math.isfinite(self.s.codex_timeout_seconds)
                and self.s.codex_timeout_seconds > 0):
            read_timeout = max(read_timeout, self.s.codex_timeout_seconds + 15)
        r = await self.http.post(f"{self.s.seller_url}/negotiate", json=req.model_dump(),
                                 timeout=httpx.Timeout(15, read=read_timeout))
        r.raise_for_status()
        response = NegotiateResponse.model_validate(r.json())
        if response.deal_id != req.deal_id or response.round != req.round:
            raise ValueError("seller negotiation response does not match this deal and round")
        if response.action == "accept" and req.offer is None:
            raise ValueError("seller accepted without an outstanding buyer offer")
        if req.action == "accept" and (response.action != "accept" or response.price != req.offer):
            raise ValueError("seller did not confirm the agreed offer")
        if req.action == "counter" and response.action == "accept" and response.price != req.offer:
            raise ValueError("seller accepted a different amount than the buyer offered")
        return response

    async def _start_job(self, seller: str, deal_id: str, price: float, task: TaskCreate) -> StartJobResponse:
        body = StartJobRequest(identifier_from_purchaser=deal_id, input_data={
            "deal_id": deal_id, "agreed_price": price, "job": task.job.model_dump(), "demo_mode": task.demo_mode})
        r = await self.http.post(f"{seller}/start_job", json=body.model_dump())
        r.raise_for_status()
        start = StartJobResponse.model_validate(r.json())
        self._validate_start(start, price)
        return start

    @staticmethod
    def _validate_start(start: StartJobResponse, price: float) -> None:
        if start.status != "success" or not start.job_id.strip() or start.price != price:
            raise ValueError("seller did not start a valid job at the agreed price")

    async def _poll(self, seller: str, job_id: str) -> StatusResponse:
        # Masumi mode waits for on-chain confirmation (minutes), so the limit is generous.
        deadline = asyncio.get_running_loop().time() + JOB_TIMEOUT
        while asyncio.get_running_loop().time() < deadline:
            r = await self.http.get(f"{seller}/status", params={"job_id": job_id})
            r.raise_for_status()
            st = StatusResponse.model_validate(r.json())
            if st.job_id != job_id:
                raise ValueError("seller status response does not match the funded job")
            if st.status in ("completed", "failed"):
                return st
            await asyncio.sleep(self.s.poll_seconds)
        return StatusResponse(job_id=job_id, status="failed")

    async def _wait_for_approval(self, task_id, deal_id, price, reason, staged) -> bool:
        fut = asyncio.get_running_loop().create_future()
        self.approvals[deal_id] = fut
        self.bus.emit("needs_approval", task_id, deal_id, staged, price=price, reason=reason,
                      approve_url=f"/approvals/{deal_id}")
        try:
            ok = await asyncio.wait_for(fut, APPROVAL_TIMEOUT)
        except TimeoutError:
            ok = False
        finally:
            self.approvals.pop(deal_id, None)
        self.bus.emit("approved" if ok else "blocked", task_id, deal_id, staged, price=price,
                      **({} if ok else {"reason": "approval declined or timed out"}))
        return ok

    async def _blocked(self, task_id, deal_id, task, price, reason, staged) -> None:
        self.ledger.update(deal_id, status="blocked")
        self.bus.emit("blocked", task_id, deal_id, staged, price=price, reason=reason)
        line = f"My wallet says no: {reason}. I'm walking away."
        await self._say(task_id, deal_id, "max", line, price, "walk", staged, backend="guard")
        req = NegotiateRequest(deal_id=deal_id, round=99, action="walk", offer=price, message=line,
                               job=task.job, demo_mode=task.demo_mode)
        try:
            await self._negotiate(req)
        except (httpx.HTTPError, ValueError):
            pass  # seller hearing the walk is courtesy, not required
        self.bus.emit("walked_away", task_id, deal_id, staged, reason=reason)

    def _agreed(self, task_id, deal_id, price, staged) -> float:
        self.ledger.update(deal_id, status="agreed", price=price)
        self.bus.emit("quote", task_id, deal_id, staged, price=price)
        return price

    def _walked(self, task_id, deal_id, reason) -> None:
        self.ledger.update(deal_id, status="walked")
        self.bus.emit("walked_away", task_id, deal_id, reason=reason)
        return None

    async def _say(self, task_id, deal_id, speaker, text, price, action, staged, **provenance) -> None:
        audio = await self.tts.speak(text, speaker)
        self.bus.emit("negotiation", task_id, deal_id, staged, speaker=speaker, text=text, price=price,
                      action=action, audio_url=audio, **provenance)

    async def _emit_balances(self, task_id, deal_id) -> None:
        try:
            self.bus.emit("balances", task_id, deal_id, **await self.guard.balances())
        except NotImplementedError:
            pass

    @staticmethod
    def _staged(task: TaskCreate) -> bool:
        return task.demo_mode != DemoMode.honest

    def _spawn(self, coro) -> None:
        t = asyncio.create_task(coro)
        self.tasks.add(t)
        t.add_done_callback(self.tasks.discard)
