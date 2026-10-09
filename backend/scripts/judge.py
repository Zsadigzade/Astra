"""Serve an isolated judge gateway and private seller; never touch recording services.

From backend: uv run --locked python scripts/judge.py --live --build
Expose only the gateway port with ngrok. Keep the laptop awake during judging.
"""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Use configured live providers; default is no-credit sample")
    parser.add_argument("--build", action="store_true", help="Build separate token-free production assets")
    parser.add_argument("--port", type=int, default=9200)
    parser.add_argument("--seller-port", type=int, default=9201)
    parser.add_argument("--max-runs", type=int, default=12)
    parser.add_argument("--session-runs", type=int, default=3)
    parser.add_argument("--state-dir", type=Path, default=ROOT / "data/judge-live")
    parser.add_argument("--local-cookie", action="store_true", help="Only for local HTTP browser checks")
    args = parser.parse_args()
    state = args.state_dir.resolve()
    state.mkdir(parents=True, exist_ok=True)
    for port in (args.port, args.seller_port):
        with socket.socket() as sock:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", port))
    # Set private paths before importing modules whose default ASGI app is created at import.
    os.environ.update(LEDGER_PATH=str(state / "bootstrap.db"), AUDIO_DIR=str(state / "bootstrap-audio"),
                      SELLER_STORE_PATH=str(state / "seller.db"), PAYMENTS_MODE="simulated", CRASH_AFTER_LOCK="0")
    from app.core.config import get_settings
    original = get_settings()
    seller_token_path = state / "seller-token.txt"
    if not seller_token_path.exists():
        seller_token_path.write_text(secrets.token_hex(32), encoding="utf-8")
    seller_token = seller_token_path.read_text(encoding="utf-8").strip()
    profile = {"LLM_MODE": "codex" if args.live else "mock",
               "SELLER_LLM_MODE": "codex" if args.live else "mock",
               "APIFY_MODE": "apify" if args.live else "sample",
               "TTS_MODE": "elevenlabs" if args.live else "off", "STRICT_LIVE": "1" if args.live else "0",
               "SELLER_API_TOKEN": seller_token, "API_TOKEN": "", "MAX_ROUNDS": "6",
               "SELLER_FLOOR": "7", "SELLER_OPENING_ASK": "18", "GUARD_CAP": "10", "GUARD_APPROVAL_OVER": "8",
               "SELLER_URL": f"http://127.0.0.1:{args.seller_port}"}
    os.environ.update(profile)
    settings = replace(original, llm_mode=profile["LLM_MODE"], seller_llm_mode=profile["SELLER_LLM_MODE"],
                       apify_mode=profile["APIFY_MODE"], tts_mode=profile["TTS_MODE"], strict_live=args.live,
                       seller_api_token=seller_token, api_token="", seller_url=profile["SELLER_URL"],
                       payments_mode="simulated", crash_after_lock=False)
    settings.require_live()
    web = state / "web"
    if args.build:
        env = {**os.environ, "VITE_API_TOKEN": "", "VITE_BUYER_URL": "/buyer", "VITE_SELLER_URL": "/seller"}
        subprocess.run([shutil.which("node"), "node_modules/vite/bin/vite.js", "build", "--outDir", str(web)],
                       cwd=ROOT.parent / "frontend", env=env, check=True)
        # Refuse to ship credentials or a loopback API URL in the judge bundle.
        from dotenv import dotenv_values
        candidates = {**os.environ, **vars(original), **dotenv_values(ROOT.parent / ".env")}
        private = [v.encode() for k,v in candidates.items()
                   if isinstance(v, str) and len(v) >= 8 and any(x in k.upper() for x in ("TOKEN", "KEY", "PASSWORD", "SECRET"))
                   and k.upper() != "SELLER_VKEY"]
        for path in web.rglob("*"):
            if path.is_file() and any(value in path.read_bytes() for value in private):
                raise RuntimeError("Private value found in public build; refusing startup")
    if not (web / "index.html").exists():
        raise RuntimeError("Build judge assets first with --build")
    import httpx
    import uvicorn
    from app.judge import create_app
    log = (state / "seller.log").open("a", encoding="utf-8")
    seller = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.seller.app:app", "--host", "127.0.0.1",
                               "--port", str(args.seller_port), "--no-access-log"], cwd=ROOT, env=os.environ.copy(),
                              stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)  # stay awake while serving judges
        with httpx.Client(timeout=1, trust_env=False) as client:
            for _ in range(100):
                if seller.poll() is not None:
                    raise RuntimeError("Private seller exited; inspect local seller.log")
                try:
                    if client.get(settings.seller_url + "/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError("Private seller readiness timed out")
        app = create_app(settings, state, web, max_runs=args.max_runs, session_runs=args.session_runs,
                         secure_cookie=not args.local_cookie)
        (state / "runtime.json").write_text(json.dumps({"gateway_pid":os.getpid(), "seller_pid":seller.pid,
             "port":args.port, "seller_port":args.seller_port, "live":args.live,
             "max_runs":args.max_runs,"session_runs":args.session_runs}), encoding="utf-8")
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
    finally:
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        seller.terminate()
        try:
            seller.wait(timeout=10)
        except subprocess.TimeoutExpired:
            seller.kill()
            seller.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
