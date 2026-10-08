"""R02/R05 acceptance with real Codex/ElevenLabs and SIMULATED payments only.

Run from backend: python scripts/rehearse.py [--browser]
Browser checks require Playwright, installed Edge and frontend npm dependencies.
Each run uses fresh artifacts and private ports. Never resets an existing ledger.
Calls live subscription Codex and ElevenLabs; Apify uses the saved real cache only.
"""

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.config import get_settings  # noqa: E402


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class Rehearsal:
    def __init__(self, browser=False):
        self.browser = browser
        self.artifact = ROOT / "data" / f"r-rehearsal-{uuid4().hex[:8]}"
        self.artifact.mkdir(parents=True)
        self.report = {"profile": "codex/cached/elevenlabs/simulated", "seller_llm_mode": "mock", "runs": [],
                       "screenshots": [], "page_errors": [], "passed": False}
        self.processes = {}
        self.logs = []
        self.ports = {}
        for name in ("buyer", "seller", "frontend"):
            while True:
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                if port not in self.ports.values():
                    self.ports[name] = port
                    break
        self.env = {**os.environ, "PAYMENTS_MODE": "simulated", "LLM_MODE": "codex", "SELLER_LLM_MODE": "mock",
                    "APIFY_MODE": "cached", "TTS_MODE": "elevenlabs", "CRASH_AFTER_LOCK": "0",
                    "LEDGER_PATH": str(self.artifact / "buyer.db"),
                    "AUDIO_DIR": str(self.artifact / "audio"),
                    "GUARD_CAP": "10", "GUARD_APPROVAL_OVER": "8", "MAX_ROUNDS": "6",
                    "SELLER_FLOOR": "7", "SELLER_OPENING_ASK": "18"}
        self.env["SELLER_URL"] = self.url("seller")
        self.env["VITE_BUYER_URL"] = self.url("buyer")
        self.env["VITE_SELLER_URL"] = self.url("seller")
        self.page = None

    def url(self, name):
        return f"http://127.0.0.1:{self.ports[name]}"

    def save(self):
        (self.artifact / "report.json").write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def start(self, name):
        require(name not in self.processes, f"{name} is already owned")
        front = name == "frontend"
        command = ([shutil.which("node"), "node_modules/vite/bin/vite.js", "--strictPort"] if front
                   else [sys.executable, "-m", "uvicorn", f"app.{name}.app:app"])
        log = (self.artifact / f"{name}.log").open("a", encoding="utf-8")
        self.logs.append(log)
        process = subprocess.Popen(command + ["--host", "127.0.0.1", "--port", str(self.ports[name])],
                                   cwd=ROOT.parent / "frontend" if front else ROOT, env=self.env,
                                   stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.processes[name] = process
        deadline = time.monotonic() + 30
        with httpx.Client(timeout=1, trust_env=False) as client:
            while time.monotonic() < deadline:
                require(process.poll() is None, f"{name} exited before readiness; inspect local log")
                try:
                    if client.get(self.url(name) + ("" if front else "/health")).status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
        raise RuntimeError(f"{name} readiness timeout")

    def stop(self, name):
        process = self.processes.pop(name)
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    def events(self, deal_id):
        with sqlite3.connect(self.artifact / "buyer.db") as db:
            events = [json.loads(row[0]) for row in db.execute("SELECT body FROM events ORDER BY id")]
        return [event for event in events if event.get("deal_id") == deal_id]

    def capture(self, label, deal_id, approval=False):
        if self.page is None:
            return
        page = self.page
        page.wait_for_function("id => window.rehearsalEvents.some(e => e.deal_id === id)", arg=deal_id)
        page.wait_for_timeout(500)
        require(page.get_by_text("SIMULATED MONEY", exact=True).is_visible(), "simulation label missing")
        require(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "horizontal overflow")
        selectors = [".honesty", ".guard-status", ".feed", ".parties"]
        selectors += [".approval", ".approval .row"] if approval else [".result", ".deal-badges"]
        for selector in selectors:
            box = page.locator(selector).bounding_box()
            require(box and box["y"] >= 0 and box["y"] + box["height"] <= 1080
                    and box["x"] >= 0 and box["x"] + box["width"] <= 1920,
                    f"{label}: {selector} is outside recording frame")
        file = f"{label}-1920x1080.png"
        page.screenshot(path=str(self.artifact / file))
        self.report["screenshots"].append(file)

    def run_act(self, act, repeat, approval=None):
        crash = act == 3
        if crash:
            self.stop("buyer")
            self.env["CRASH_AFTER_LOCK"] = "1"
            self.start("buyer")
        seller_pid = self.processes["seller"].pid
        mode = {1: "honest", 2: "con", 3: "honest", 4: "junk"}[act]
        expected = "blocked" if approval is False else {1: "released", 2: "blocked", 3: "released", 4: "refunded"}[act]
        terminal = "walked_away" if expected == "blocked" else expected
        start = time.monotonic()
        restarted, answered = False, False
        label = f"act-{act}-run-{repeat}" if approval is None else f"approval-{'accept' if approval else 'decline'}"
        print(f"Starting {label}", flush=True)
        with httpx.Client(base_url=self.url("buyer"), timeout=10, trust_env=False) as client:
            if self.page:
                self.page.get_by_role("radio").nth(act - 1).click()
            if self.page and not crash:
                with self.page.expect_response(lambda r: r.url.endswith("/tasks") and r.request.method == "POST") as response:
                    self.page.get_by_role("button", name="Run scenario", exact=True).first.click()
                require(response.value.ok, "dashboard task launch failed")
                deal_id = response.value.json()["deal_id"]
            else:
                deal_id = client.post("/tasks", json={"demo_mode": mode, "budget": 20}).raise_for_status().json()["deal_id"]
            while time.monotonic() - start < 240:
                if self.page:
                    self.page.wait_for_timeout(100)
                else:
                    time.sleep(.1)
                buyer = self.processes["buyer"]
                if buyer.poll() is not None:
                    require(crash and not restarted and buyer.returncode == 1, "unexpected buyer exit")
                    require(self.processes["seller"].poll() is None, "seller died during crash")
                    self.stop("buyer")
                    self.env["CRASH_AFTER_LOCK"] = "0"
                    self.start("buyer")
                    restarted = True
                events = self.events(deal_id)
                types = {e["type"] for e in events}
                require("error" not in types, f"{label}: error event; inspect ledger")
                if "needs_approval" in types and not answered:
                    require(approval is not None, f"{label}: unexpected human approval")
                    if self.page:
                        self.page.get_by_role("alertdialog").wait_for(timeout=15000)
                        self.capture(label + "-pending", deal_id, approval=True)
                        if approval:
                            self.page.locator(".approval .btn-primary").click()
                        else:
                            self.page.get_by_role("button", name="Decline", exact=True).click()
                    else:
                        client.post(f"/approvals/{deal_id}", json={"approve": approval}).raise_for_status()
                    answered = True
                if terminal in types:
                    break
                require(not ({"released", "refunded", "walked_away"} & types), f"{label}: wrong outcome")
            else:
                raise RuntimeError(f"{label}: 240-second deadline exceeded")
            counts = Counter(e["type"] for e in events)
            require(all(e["simulated"] for e in events), "non-simulated event")
            require(expected in types, f"{label}: missing {expected}")
            speech = [e["data"] for e in events if e["type"] == "negotiation"]
            max_lines = [e for e in speech if e["speaker"] == "max" and e.get("backend") != "guard"]
            require(max_lines and all(e.get("backend") == ("mock" if act == 2 else "codex")
                                     and not e.get("fallback_reason") for e in max_lines), "Codex fallback occurred")
            require(all(e.get("backend") == "mock" for e in speech if e["speaker"] == "viktor"), "unexpected seller mode")
            require(speech and all(e.get("audio_url") for e in speech), "ElevenLabs text fallback occurred")
            for line in speech:
                audio = client.get(line["audio_url"]).raise_for_status()
                require(len(audio.content) > 100 and audio.headers.get("content-type", "").startswith("audio/"), "invalid speech clip")
            if expected == "blocked":
                require(counts["escrow_locked"] == 0, "blocked deal was funded")
            else:
                require(counts["escrow_locked"] == 1 and counts[terminal] == 1, "duplicate payment/settlement event")
                delivery = next(e["data"] for e in events if e["type"] == "delivered")
                verified = next(e["data"]["ok"] for e in events if e["type"] == "verified")
                require(verified == (expected == "released"), "wrong verification decision")
                if expected == "released":
                    require(delivery["source"] == "apify_cached" and delivery["items"] == 20, "real cache not used")
            if crash:
                require(restarted and counts["already_paid"] == 1, "crash did not recover exactly once")
                require(self.processes["seller"].pid == seller_pid and self.processes["seller"].poll() is None,
                        "seller did not survive")
            if act in (2, 3, 4):
                require(any(e["staged"] for e in events), "staged scenario label missing")
            with sqlite3.connect(self.artifact / "buyer.db") as db:
                escrows = db.execute("SELECT status FROM sim_escrows WHERE deal_id=?", (deal_id,)).fetchall()
            require(escrows == ([] if expected == "blocked" else [(expected,)]), "unexpected escrow rows")
            balances = client.get("/balances").raise_for_status().json()
            require(balances["escrow"] == 0 and abs(sum(balances[k] for k in ("buyer", "seller", "escrow")) - 100) < .001,
                    "balance conservation failed")
            if self.page:
                self.page.wait_for_function("([id, type]) => window.rehearsalEvents.some(e => e.deal_id === id && e.type === type)",
                                            arg=[deal_id, terminal], timeout=20000)
                if act in (2, 3, 4):
                    require(self.page.get_by_text("STAGED SCENARIO", exact=True).first.is_visible(), "STAGED badge missing")
                self.capture(label, deal_id)
            result = {"label": label, "deal_id": deal_id, "outcome": expected, "codex_turns": sum(e.get("backend") == "codex" for e in max_lines),
                      "speech_clips": len(speech), "text_fallbacks": 0, "buyer_restarts": int(restarted),
                      "event_counts": dict(counts), "balances": balances, "seconds": round(time.monotonic() - start, 1)}
            self.report["runs"].append(result)
            self.save()
            print(json.dumps(result), flush=True)

    def run(self):
        print(f"Artifacts: {self.artifact}", flush=True)
        try:
            with ExitStack() as stack:
                if self.browser:
                    from playwright.sync_api import sync_playwright
                    pw = stack.enter_context(sync_playwright())
                    browser = pw.chromium.launch(channel="msedge", headless=True)
                    stack.callback(browser.close)
                    self.page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
                    self.page.on("pageerror", lambda error: self.report["page_errors"].append(str(error)))
                    self.page.add_init_script("""window.rehearsalEvents=[]; const Native=window.EventSource;
                        window.EventSource=class extends Native {constructor(url){super(url);
                        this.addEventListener('message',e=>window.rehearsalEvents.push(JSON.parse(e.data)));}};""")
                self.start("seller")
                self.start("buyer")
                if self.browser:
                    self.start("frontend")
                    self.page.goto(self.url("frontend"))
                    self.page.wait_for_function("document.querySelector('button[aria-pressed]')?.disabled===false")
                for act in (1, 2, 3, 4):
                    for repeat in range(1, 4):
                        self.run_act(act, repeat)
                # All prior deals are settled before restarting the owned seller.
                self.stop("seller")
                self.env["SELLER_FLOOR"] = "9"
                self.start("seller")
                self.run_act(1, 1, approval=True)
                self.run_act(1, 1, approval=False)
                require(not self.report["page_errors"], "browser page errors")
                self.report["passed"] = True
        except Exception as exc:
            # Keep diagnostics local and avoid provider response bodies in the report.
            self.report["failure_type"] = type(exc).__name__
            raise
        finally:
            for name in list(self.processes):
                self.stop(name)
            for log in self.logs:
                log.close()
            self.report["owned_services_stopped"] = not self.processes
            self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", action="store_true", help="capture/check Edge at 1920x1080")
    args = parser.parse_args()
    settings = get_settings()
    require(settings.elevenlabs_api_key and settings.voice_max and settings.voice_viktor,
            "Configure ElevenLabs credentials and both voice IDs first")
    require(Path(settings.apify_cache_path).is_file(), "Recover the saved real Apify cache first")
    Rehearsal(args.browser).run()


if __name__ == "__main__":
    main()
