"""Start seller (:8001) and buyer (:8000) together; Ctrl+C stops both. Works on Windows, macOS, Linux.

Run: uv run python scripts/up.py            then in another terminal: uv run python scripts/act.py honest
     uv run python scripts/up.py --crash    buyer exits right after escrow lock (STAGED Act 3)
     uv run python scripts/up.py --reset    delete data/buyer.db first (fresh balances and history)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
SERVICES = {"seller": ("seller.app:app", 8001), "buyer": ("buyer.app:app", 8000)}


def start(name: str, env: dict[str, str]) -> subprocess.Popen:
    app, port = SERVICES[name]
    return subprocess.Popen([sys.executable, "-m", "uvicorn", app, "--port", str(port)], cwd=ROOT, env=env)


def wait_healthy(port: int, timeout: float = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(f"http://localhost:{port}/health", timeout=1).status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crash", action="store_true", help="CRASH_AFTER_LOCK=1 for the buyer (Act 3)")
    ap.add_argument("--reset", action="store_true", help="delete data/buyer.db before starting")
    a = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # show status lines immediately, even when piped

    if a.reset:
        (ROOT / "data" / "buyer.db").unlink(missing_ok=True)
        print("reset: data/buyer.db deleted")
    buyer_env = {**os.environ, **({"CRASH_AFTER_LOCK": "1"} if a.crash else {})}
    procs = {"seller": start("seller", dict(os.environ)), "buyer": start("buyer", buyer_env)}
    try:
        for name, (_, port) in SERVICES.items():
            if not wait_healthy(port):
                print(f"{name} did not answer /health on :{port}; see its log above")
                return 1
        health = httpx.get("http://localhost:8000/health").json()
        print(f"\nUP  buyer :8000  seller :8001  payments={health['payments_mode']}  llm={health['llm_mode']}"
              f"  tts={health['tts_mode']}{'  CRASH_AFTER_LOCK=1 (STAGED)' if a.crash else ''}")
        print("next: uv run python scripts/act.py honest   (or open the dashboard)\n")
        while procs["seller"].poll() is None:
            if procs["buyer"].poll() is not None:
                # Act 3: only the buyer restarts. The seller keeps its jobs in memory and must stay up.
                print("\n[STAGED] BUYER DIED mid-deal. Restarting buyer in 3s (no crash flag)...")
                time.sleep(3)
                procs["buyer"] = start("buyer", dict(os.environ))
                wait_healthy(8000)
                print("buyer back. It resumes open deals itself; watch: uv run python scripts/act.py --watch\n")
            time.sleep(0.5)
        print("seller stopped; shutting down.")
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for p in procs.values():
            if p.poll() is None:
                p.terminate()
        for p in procs.values():
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
