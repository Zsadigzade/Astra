"""Astra.exe: double-click from the repository root to launch the project (npm start).

Runs scripts/dev.mjs (seller + buyer + dashboard, browser opens) in this console window;
closing the window or Ctrl+C stops everything. Before starting it:
- uses the root .env as the source of truth: inherited terminal variables for the same keys
  (left over from offline profiles or test runs) are dropped, so they cannot make STRICT_LIVE refuse;
- finds an earlier Astra session on the demo ports (it keeps the code it started with) and offers
  to restart it; a port held by another program is reported and left alone;
- installs the backend environment if it is missing (dev.mjs installs the frontend's).
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser

PORTS = (8000, 8001, 5173)  # buyer, seller, dashboard (scripts/dev.mjs)
DASHBOARD = "http://localhost:5173/"
ALWAYS_DROP = ("VIRTUAL_ENV",)  # another venv's activation only makes uv warn
_DOTENV_KEY = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def find_root(candidates) -> Path:
    for candidate in candidates:
        candidate = Path(candidate).resolve()
        for root in (candidate, *candidate.parents):
            if (root / "backend/pyproject.toml").is_file() and (root / "scripts/dev.mjs").is_file():
                return root
    raise ValueError("Put Astra.exe in the Astra repository folder (the one containing backend and scripts).")


def dotenv_keys(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return {m.group(1) for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if (m := _DOTENV_KEY.match(line))}


def clean_env(environ, keys) -> tuple[dict[str, str], list[str]]:
    """Copy of environ without variables that would override .env; returns the dropped names."""
    dropped = sorted(k for k in environ if k in keys)
    drop = set(dropped) | set(ALWAYS_DROP)
    return {k: v for k, v in environ.items() if k not in drop}, dropped


def listeners(netstat_text: str, ports) -> dict[int, set[int]]:
    found: dict[int, set[int]] = {}
    for line in netstat_text.splitlines():
        parts = line.split()
        if len(parts) == 5 and parts[0] == "TCP" and parts[3] == "LISTENING":
            port = int(parts[1].rsplit(":", 1)[1])
            if port in ports:
                found.setdefault(port, set()).add(int(parts[4]))
    return found


def fetch(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:  # noqa: S310 - fixed localhost URLs
            return r.read(4096).decode("utf-8", errors="replace")
    except Exception:
        return None


def is_astra(port: int, get=fetch) -> bool:
    """Identify an Astra service by its own endpoint, so another program's port is never touched."""
    if port == 5173:
        body = get(DASHBOARD)
        return bool(body) and "<title>Astra" in body
    body = get(f"http://127.0.0.1:{port}/health")
    return bool(body) and ('"payments_mode"' in body or '"agent":"viktor"' in body)


def busy_ports(ports=PORTS) -> dict[int, set[int]]:
    # No "-p TCP": that lists IPv4 only, and Vite listens on [::1].
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    return listeners(out, ports)


def tool(name: str) -> str | None:
    found = shutil.which(name)
    if not found and name == "uv":
        fallback = Path.home() / ".local/bin/uv.exe"
        found = str(fallback) if fallback.is_file() else None
    return found


def say(line: str = "") -> None:
    print(line, flush=True)


def ask(prompt: str, default: str) -> str:
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        answer = ""
    return answer[:1] or default


def stop_old_session(busy: dict[int, set[int]]) -> bool:
    for pids in busy.values():
        for pid in pids:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    for _ in range(40):
        if not busy_ports():
            return True
        time.sleep(0.25)
    return False


def run(root: Path) -> int:
    say(f"Astra: {root}")
    node, uv = tool("node"), tool("uv")
    missing = [n for n, p in (("Node.js (node)", node), ("uv", uv)) if not p]
    if missing:
        say("Missing: " + ", ".join(missing) + ". Install it, then run Astra.exe again.")
        return 1
    if not (root / ".env").is_file():
        say("No .env in the repository root: services use their defaults (see .env.example).")

    busy = busy_ports()
    if busy:
        others = sorted(p for p in busy if not is_astra(p))
        if others:
            say("Port(s) " + ", ".join(f":{p}" for p in others) + " are used by another program. "
                "Close it, then run Astra.exe again.")
            return 1
        say("Astra is already running (" + ", ".join(f":{p}" for p in sorted(busy)) + "). "
            "It keeps the code it started with; restart it after pulling changes.")
        choice = ask("[R]estart with current code, [O]pen the dashboard, [Q]uit? [R] ", "r")
        if choice == "o":
            webbrowser.open(DASHBOARD)
            return 0
        if choice != "r":
            return 0
        say("Stopping the running session...")
        if not stop_old_session(busy):
            say("The old session did not release its ports. Close its window, then try again.")
            return 1

    if not (root / "backend/.venv").is_dir():
        say("Installing the backend environment (uv sync)...")
        if subprocess.call([uv, "sync", "--directory", str(root / "backend")]) != 0:
            return 1

    env, dropped = clean_env(os.environ, dotenv_keys(root / ".env"))
    if dropped:
        say("Using .env, not terminal values, for: " + ", ".join(dropped))
    say("Starting. Close this window or press Ctrl+C to stop everything.\n")
    child = subprocess.Popen([node, str(root / "scripts/dev.mjs")], cwd=root, env=env)
    while True:
        try:
            return child.wait()
        except KeyboardInterrupt:
            continue  # dev.mjs got the same Ctrl+C and is stopping its services; wait for it


def main() -> int:
    try:
        code = run(find_root([Path(sys.executable).parent, Path.cwd(), Path(__file__).parent]))
    except ValueError as exc:
        say(str(exc))
        code = 1
    if code:
        ask("\nAstra stopped with an error (see above). Press Enter to close.", "")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
