"""Public, bounded judge access around isolated instances of the existing buyer.

No API tokens enter the browser. Each random HttpOnly session owns its buyer ledger,
events, controls and audio. The seller stays on a private loopback port. Run one worker.
"""
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import replace
import json
from pathlib import Path
import re
import secrets
import sqlite3

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.buyer.app import create_app as create_buyer
from app.core.config import Settings
from app.core.models import TaskCreate

COOKIE = "astra_judge"
SAFE_GET = re.compile(r"^(health|events|deals|balances|controls|audio/[A-Za-z0-9_.-]+\.mp3)$")
SAFE_POST = re.compile(r"^(tasks|requests/parse|approvals/[a-f0-9]{20})$")


class Forward(Response):
    """Forward ASGI directly so SSE is streamed, never buffered in a proxy client."""
    def __init__(self, child, path, body, finish=None):
        super().__init__()
        self.child, self.path, self.body, self.finish = child, path, body, finish

    async def __call__(self, scope, receive, send):
        original = receive
        if self.body is not None:
            body = self.body
            first = True

            async def replay():
                nonlocal first
                if first:
                    first = False
                    return {"type": "http.request", "body": body, "more_body": False}
                return await original()
            receive = replay
        child_scope = {**scope, "path": "/" + self.path, "raw_path": ("/" + self.path).encode(),
                       "root_path": "", "app": self.child}
        try:
            await self.child(child_scope, receive, send)
        finally:
            if self.finish:
                self.finish()


def create_app(settings: Settings, state_dir: Path, web_dir: Path, *, max_runs=12,
               session_runs=3, max_sessions=32, secure_cookie=True, buyer_factory=create_buyer):
    if not settings.simulated or settings.crash_after_lock:
        raise ValueError("Judge access requires simulated payments and crash mode disabled")
    if not 1 <= max_runs <= 100 or not 1 <= session_runs <= max_runs:
        raise ValueError("Invalid judge run limits")
    state_dir = Path(state_dir).resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    web_dir = Path(web_dir).resolve()
    db = sqlite3.connect(state_dir / "quota.db", isolation_level=None, check_same_thread=False)
    db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, used INTEGER NOT NULL DEFAULT 0)")
    children, streams = {}, {}
    lock = asyncio.Lock()
    stack = AsyncExitStack()

    async def load(sid):
        if sid not in children:
            directory = state_dir / "sessions" / sid
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "audio").mkdir(exist_ok=True)
            s = replace(settings, api_token="", ledger_path=str(directory / "buyer.db"),
                        audio_dir=str(directory / "audio"), max_rounds=6,
                        guard_cap=10, guard_approval_over=8)
            child = buyer_factory(s)
            stack.callback(child.state.ledger.db.close)
            await stack.enter_async_context(child.router.lifespan_context(child))
            children[sid] = child
        return children[sid]

    @asynccontextmanager
    async def lifespan(app):
        async with stack:
            # Resume only already admitted work. A process restart never resets quota.
            for (sid,) in db.execute("SELECT id FROM sessions").fetchall():
                await load(sid)
            yield
        db.close()

    app = FastAPI(title="Astra judge demo", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.quota = db
    app.state.children = children

    @app.middleware("http")
    async def security(request, call_next):
        # Browser mutations must originate on this same host. Cookie authentication
        # does not turn an arbitrary cross-origin page into a demo controller.
        if request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("origin", "")
            if origin not in {"https://" + request.headers.get("host", ""),
                              "http://" + request.headers.get("host", "")}:
                return JSONResponse({"detail": "Same-origin browser request required"}, status_code=403)
            if not request.headers.get("content-type", "").startswith("application/json"):
                return JSONResponse({"detail": "JSON required"}, status_code=415)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        response.headers["Cache-Control"] = "no-store" if not request.url.path.startswith("/assets/") else "public, max-age=3600"
        return response

    def session(request):
        sid = request.cookies.get(COOKIE, "")
        if not re.fullmatch(r"[a-f0-9]{48}", sid) or sid not in children:
            raise HTTPException(401, "Open the demo homepage to start a private session")
        return sid

    @app.get("/health")
    async def health():
        return {"ok": True, "demo": "judge", "simulated": True}

    @app.get("/")
    async def home(request: Request):
        async with lock:
            sid = request.cookies.get(COOKIE, "")
            if sid not in children:
                if db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] >= max_sessions:
                    raise HTTPException(503, "This limited judge demo has reached its session capacity")
                sid = secrets.token_hex(24)
                db.execute("INSERT INTO sessions(id) VALUES (?)", (sid,))
                await load(sid)
            used = db.execute("SELECT used FROM sessions WHERE id=?", (sid,)).fetchone()[0]
            total = db.execute("SELECT COALESCE(SUM(used),0) FROM sessions").fetchone()[0]
        html = (web_dir / "index.html").read_text(encoding="utf-8")
        providers = "Live agents, data and voices" if settings.strict_live else "Sample test instance"
        notice = (f'<aside role="note" style="padding:10px 20px;background:#172335;color:#e7efff;font:14px/1.5 system-ui;">'
                  f'<strong>Judge demo:</strong> {providers}. SIMULATED money. '
                  f'{session_runs-used} of {session_runs} runs left in this browser; '
                  f'{max_runs-total} of {max_runs} runs left overall. One run at a time; failures count. '
                  'Run request, then Play voices. Recovery is demonstrated in the recorded video. '
                  'Hosted from the team laptop during judging.</aside>')
        response = HTMLResponse(html.replace("<body>", "<body>" + notice, 1))
        response.set_cookie(COOKIE, sid, httponly=True, secure=secure_cookie, samesite="strict", max_age=43200)
        return response

    @app.get("/seller/health")
    async def seller_health(request: Request):
        session(request)
        try:
            async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
                result = await client.get(settings.seller_url + "/health")
                result.raise_for_status()
                return result.json()
        except httpx.HTTPError:
            return JSONResponse({"ok": False}, status_code=503)

    @app.api_route("/buyer/{path:path}", methods=["GET", "POST", "PUT"])
    async def buyer(request: Request, path: str):
        sid = session(request)
        child = children[sid]
        method = request.method
        if not ((method == "GET" and SAFE_GET.fullmatch(path)) or
                (method == "POST" and SAFE_POST.fullmatch(path)) or
                (method == "PUT" and path == "controls")):
            raise HTTPException(404, "Not available in the judge demo")
        if method == "GET" and path == "controls":
            return {**child.state.controls.snapshot(), "max_rounds_ceiling": 6}
        body = None
        if method != "GET":
            body = b""
            try:
                async with asyncio.timeout(10):
                    async for chunk in request.stream():
                        body += chunk
                        if len(body) > 8192:
                            raise HTTPException(413, "Request too large")
            except TimeoutError:
                raise HTTPException(408, "Request timed out")
            try:
                value = json.loads(body)
                if not isinstance(value, dict):
                    raise ValueError()
            except (ValueError, UnicodeError):
                raise HTTPException(422, "JSON object required")
            if path == "controls" and value.get("max_rounds", 6) is not None:
                rounds = value.get("max_rounds", 6)
                if not isinstance(rounds, int) or rounds > 6:
                    raise HTTPException(422, "Judge demo allows at most six negotiation rounds")
        if method == "POST" and path == "tasks":
            try:
                task = TaskCreate.model_validate(value)
            except ValidationError:
                raise HTTPException(422, "Invalid demo request")
            if task.job.count > 20:
                raise HTTPException(422, "Judge demo supports at most 20 rental listings")
            async with lock:
                if child.state.controls.paused:
                    raise HTTPException(423, "Resume your agents before starting a request")
                if any(c.state.orch.tasks or c.state.orch.audio_tasks for c in children.values()):
                    raise HTTPException(429, "Another live run is finishing. Please retry shortly.", headers={"Retry-After": "15"})
                used = db.execute("SELECT used FROM sessions WHERE id=?", (sid,)).fetchone()[0]
                total = db.execute("SELECT SUM(used) FROM sessions").fetchone()[0]
                if used >= session_runs or total >= max_runs:
                    raise HTTPException(429, "Judge demo run limit reached. The recorded demo remains available.")
                # Charge admission before launch; quota survives errors and restarts.
                db.execute("UPDATE sessions SET used=used+1 WHERE id=?", (sid,))
                result = await child.state.orch.create_task(task)
                return result
        finish = None
        if path == "events":
            if streams.get(sid, 0) >= 2:
                raise HTTPException(429, "Close an extra demo tab before reconnecting")
            streams[sid] = streams.get(sid, 0) + 1
            def finish():
                streams[sid] -= 1
        return Forward(child, path, body, finish)

    app.mount("/assets", StaticFiles(directory=web_dir / "assets"), name="assets")
    return app
