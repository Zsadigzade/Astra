"""Start seller (:8001) and buyer (:8000) together; Ctrl+C stops both. Works on Windows, macOS, Linux.

Run: uv run python scripts/up.py            then in another terminal: uv run python scripts/act.py honest
     uv run python scripts/up.py --crash    buyer exits right after escrow lock (STAGED Act 3)
     uv run python scripts/up.py --reset    archive a completed simulated ledger first
"""

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import Settings, get_settings  # noqa: E402
from app.buyer.ledger import payment_mode  # noqa: E402

SERVICES = {"seller": ("app.seller.app:app", 8001), "buyer": ("app.buyer.app:app", 8000)}


def check_ports() -> None:
    """Fail before touching data if another session owns either service port."""
    for name, (_, port) in SERVICES.items():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(f"{name} port :{port} is unavailable; leave the existing session running") from exc


def reset_ledger(settings: Settings) -> Path | None:
    """Archive only a quiescent, completed simulated ledger; preserve the original bytes."""
    if settings.payments_mode != "simulated":
        raise RuntimeError("--reset is only available with PAYMENTS_MODE=simulated")
    if settings.ledger_path == ":memory:":
        return None
    path = Path(settings.ledger_path)
    if not path.is_absolute():
        path = ROOT / path  # same working directory as the child buyer
    path = path.resolve()
    if not path.exists():
        return None
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise RuntimeError("ledger has SQLite sidecar files; stop its owner and recover it before resetting")
    try:
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
        try:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "deals" not in tables:
                raise RuntimeError("ledger schema is unrecognized; refusing reset")
            if db.execute("SELECT 1 FROM deals WHERE status NOT IN ('released','refunded','blocked','walked') LIMIT 1").fetchone():
                raise RuntimeError("ledger contains unfinished deals; refusing reset")
            if payment_mode(db) == "masumi":
                raise RuntimeError("ledger belongs to real payments; refusing reset")
            if "sim_escrows" in tables and db.execute("SELECT 1 FROM sim_escrows WHERE status NOT IN ('released','refunded') LIMIT 1").fetchone():
                raise RuntimeError("ledger still holds escrow; refusing reset")
            if "events" in tables:
                for (body,) in db.execute("SELECT body FROM events"):
                    if json.loads(body).get("simulated") is not True:
                        raise RuntimeError("ledger contains events not proven simulated; refusing reset")
        finally:
            db.close()
    except (sqlite3.Error, ValueError, AttributeError) as exc:
        raise RuntimeError("ledger could not be safely inspected; refusing reset") from exc
    backup = path.with_name(f"{path.name}.reset-{time.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}.bak")
    path.rename(backup)
    return backup


def start(name: str, env: dict[str, str]) -> subprocess.Popen:
    app, port = SERVICES[name]
    return subprocess.Popen([sys.executable, "-m", "uvicorn", app, "--port", str(port)], cwd=ROOT, env=env)


def wait_healthy(port: int, process: subprocess.Popen, timeout: float = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=1, trust_env=False).status_code == 200:
                return process.poll() is None
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crash", action="store_true", help="CRASH_AFTER_LOCK=1 for the buyer (Act 3)")
    ap.add_argument("--reset", action="store_true", help="archive the configured ledger (completed simulated deals only)")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    procs = {}
    try:
        s = get_settings()
        check_ports()
        if a.reset:
            backup = reset_ledger(s)
            print(f"reset: previous ledger preserved at {backup}" if backup else "reset: no disk ledger to archive")
        staged_crash = a.crash or s.crash_after_lock
        buyer_env = {**os.environ, "CRASH_AFTER_LOCK": "1" if staged_crash else "0"}
        for name in SERVICES:
            procs[name] = start(name, buyer_env if name == "buyer" else dict(os.environ))
        for name, (_, port) in SERVICES.items():
            if not wait_healthy(port, procs[name]):
                print(f"{name} did not answer /health on :{port}; see its log above")
                return 1
        buyer_port = SERVICES["buyer"][1]
        seller_port = SERVICES["seller"][1]
        health = httpx.get(f"http://127.0.0.1:{buyer_port}/health", timeout=2, trust_env=False).json()
        print(f"\nUP  buyer :{buyer_port}  seller :{seller_port}  payments={health['payments_mode']}  llm={health['llm_mode']}"
              f"  tts={health['tts_mode']}{'  CRASH_AFTER_LOCK=1 (STAGED)' if staged_crash else ''}")
        print("next: uv run python scripts/act.py honest   (or open the dashboard)\n")
        while procs["seller"].poll() is None:
            if procs["buyer"].poll() is not None:
                if not staged_crash or procs["buyer"].returncode != 1:
                    print("buyer stopped unexpectedly; shutting down (see its log above).")
                    return 1
                staged_crash = False  # exactly one restart per staged rehearsal
                # Act 3: only the buyer restarts. The seller keeps its jobs in memory and must stay up.
                print("\n[STAGED] BUYER DIED mid-deal. Restarting buyer in 3s (no crash flag)...")
                time.sleep(3)
                if procs["seller"].poll() is not None:
                    print("seller stopped during recovery; restart both (seller jobs persist in SELLER_STORE_PATH).")
                    return 1
                procs["buyer"] = start("buyer", {**os.environ, "CRASH_AFTER_LOCK": "0"})
                if not wait_healthy(buyer_port, procs["buyer"]):
                    print("buyer restart failed; ledger preserved for recovery.")
                    return 1
                print("buyer back. It resumes open deals itself; watch: uv run python scripts/act.py --watch\n")
            time.sleep(0.5)
        print("seller stopped; shutting down.")
        return 1
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, httpx.HTTPError) as exc:
        # Do not echo HTTP response bodies, environment values or provider secrets.
        print(f"startup failed: {exc}" if isinstance(exc, RuntimeError) else f"startup failed ({type(exc).__name__}); see service logs")
        return 1
    finally:
        for p in procs.values():
            if p.poll() is None:
                p.terminate()
        for p in procs.values():
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
