"""R02/R05 acceptance with real Codex/ElevenLabs and SIMULATED payments only.

Run from backend: python scripts/rehearse.py [--browser]
Browser checks require Playwright, installed Edge and frontend npm dependencies.
Each run uses fresh artifacts and private ports. Never resets an existing ledger.
Calls live subscription Codex and ElevenLabs. Defaults use cached Apify data;
--data-mode apify starts paid scrapes and rejects cached fallback as acceptance.
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
from app.core.models import JobSpec  # noqa: E402
from app.seller.apify import load_cache  # noqa: E402


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def speech_lines(events):
    """Resolve additive audio events without confusing reused IDs from another deal."""
    audio = {}
    for event in events:
        if event["type"] == "audio_ready":
            data = event["data"]
            audio[(event.get("deal_id"), data.get("message_id"), data.get("message_ts"))] = data
    lines = []
    for event in events:
        if event["type"] != "negotiation":
            continue
        line = dict(event["data"])
        update = audio.get((event.get("deal_id"), event["id"], event["ts"]))
        if update is not None:
            line.update(audio_url=update.get("audio_url"), audio_status=update.get("audio_status"))
            if update.get("reason"):
                line["audio_reason"] = update["reason"]
        lines.append(line)
    return lines


def check_seller_lines(speech, mode, act):
    lines = [line for line in speech if line["speaker"] == "viktor"]
    require(lines and not any(line.get("fallback_reason") for line in lines), "seller fallback occurred")
    # Codex Viktor speaks every line live (staged con and accept/walk acknowledgements included;
    # code still owns those prices). Scripted Viktor never claims a live turn.
    want = "codex" if mode == "codex" else "mock"
    require(all(line.get("backend") == want for line in lines),
            f"act {act}: every seller line must be {want}")


def check_max_lines(speech):
    """Check live decisions; guard notices and the fixed opening question are code."""
    lines = [line for line in speech if line["speaker"] == "max" and line.get("backend") != "guard"
             and not (line.get("action") == "open" and line.get("backend") == "mock"
                      and not line.get("fallback_reason"))]
    require(lines and all(line.get("backend") == "codex" and not line.get("fallback_reason") for line in lines),
            "Codex fallback occurred")
    return lines


def service_env(settings, artifact, seller_mode, data_mode):
    """Child services inherit access tokens, keep seller state private and run STRICT_LIVE only when fully live."""
    strict = seller_mode == "codex" and data_mode == "apify"
    return {"API_TOKEN": settings.api_token, "SELLER_API_TOKEN": settings.seller_api_token,
            "VITE_API_TOKEN": settings.api_token, "SELLER_STORE_PATH": str(artifact / "seller.db"),
            "STRICT_LIVE": "1" if strict else "0"}


class Rehearsal:
    def __init__(self, browser=False, *, seller_mode="mock", data_mode="cached", repeats=3):
        require(seller_mode in {"mock", "codex"}, "invalid seller mode")
        require(data_mode in {"cached", "apify"}, "invalid data mode")
        require(repeats in {1, 2, 3}, "repeats must be 1, 2 or 3")
        self.browser = browser
        self.seller_mode, self.data_mode, self.repeats = seller_mode, data_mode, repeats
        self.artifact = ROOT / "data" / f"r-rehearsal-{uuid4().hex[:8]}"
        self.artifact.mkdir(parents=True)
        self.report = {"profile": f"codex/{data_mode}/elevenlabs/simulated", "seller_llm_mode": seller_mode,
                       "repeats": repeats, "runs": [],
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
        self.env = {**os.environ, "PAYMENTS_MODE": "simulated", "LLM_MODE": "codex", "SELLER_LLM_MODE": seller_mode,
                    "APIFY_MODE": data_mode, "TTS_MODE": "elevenlabs", "CRASH_AFTER_LOCK": "0",
                    "APIFY_ALLOW_STALE_CACHE": "0",
                    "LEDGER_PATH": str(self.artifact / "buyer.db"),
                    "AUDIO_DIR": str(self.artifact / "audio"),
                    "GUARD_CAP": "10", "GUARD_APPROVAL_OVER": "8", "MAX_ROUNDS": "6",
                    "SELLER_FLOOR": "7", "SELLER_OPENING_ASK": "18"}
        self.settings = get_settings()
        self.env.update(service_env(self.settings, self.artifact, seller_mode, data_mode))
        self.headers = {"X-API-Token": self.settings.api_token} if self.settings.api_token else {}
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
        # Wallet policy moved out of the right rail into its own tab in the new dashboard.
        page.get_by_role("tab", name="Wallet", exact=True).click()
        page.wait_for_timeout(500)
        require(page.get_by_text("SIMULATED MONEY", exact=True).is_visible(), "simulation label missing")
        require(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "horizontal overflow")
        selectors = [".header", ".guard-status", ".deal-head"]
        selectors += [".approval", ".approval .row"] if approval else [".result-line", ".deal-badges", ".feed"]
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
        with httpx.Client(base_url=self.url("buyer"), timeout=10, trust_env=False, headers=self.headers) as client:
            if self.page:
                self.page.get_by_role("radio").nth(act - 1).click()
            if self.page and not crash:
                with self.page.expect_response(lambda r: r.url.endswith("/tasks") and r.request.method == "POST") as response:
                    self.page.get_by_role("complementary", name="Scenarios and usage").get_by_role(
                        "button", name="Run request", exact=True).click()
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
                    if not any(line.get("audio_status") == "pending" for line in speech_lines(events)):
                        break
                else:
                    require(not ({"released", "refunded", "walked_away"} & types), f"{label}: wrong outcome")
            else:
                raise RuntimeError(f"{label}: 240-second deadline exceeded")
            counts = Counter(e["type"] for e in events)
            require(all(e["simulated"] for e in events), "non-simulated event")
            require(expected in types, f"{label}: missing {expected}")
            speech = speech_lines(events)
            max_lines = check_max_lines(speech)
            check_seller_lines(speech, self.seller_mode, act)
            interrupted = [e for e in speech if not e.get("audio_url")
                           and e.get("audio_reason") == "buyer_restarted" and crash and restarted]
            require(speech and all(e.get("audio_url") or e in interrupted for e in speech),
                    "ElevenLabs text fallback occurred")
            for line in speech:
                if not line.get("audio_url"):
                    continue  # explicitly recorded intentional-crash interruption, never a provider success
                audio = client.get(line["audio_url"]).raise_for_status()
                require(len(audio.content) > 100 and audio.headers.get("content-type", "").startswith("audio/"), "invalid speech clip")
            if expected == "blocked":
                require(counts["escrow_locked"] == 0, "blocked deal was funded")
            else:
                require(counts["escrow_locked"] == 1 and counts[terminal] == 1, "duplicate payment/settlement event")
                delivery = next(e["data"] for e in events if e["type"] == "delivered")
                verified = next(e["data"]["ok"] for e in events if e["type"] == "verified")
                require(verified == (expected == "released"), "wrong verification decision")
                # Act 4 junk sabotages a real scrape (3 items); fallback data is never acceptance.
                source = "apify" if self.data_mode == "apify" else "apify_cached"
                items = 20 if expected == "released" else 3
                require(delivery["source"] == source and delivery["items"] == items,
                        f"expected {items}-item {source} delivery; fallback is not live acceptance")
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
                    require(self.page.locator(".deal-badges").get_by_text("STAGED", exact=True).is_visible(), "STAGED badge missing")
                self.capture(label, deal_id)
            result = {"label": label, "deal_id": deal_id, "outcome": expected, "codex_turns": sum(e.get("backend") == "codex" for e in max_lines),
                      "seller_codex_turns": sum(e.get("backend") == "codex" for e in speech if e["speaker"] == "viktor"),
                      "delivery": next((e["data"] for e in events if e["type"] == "delivered"), None),
                      "speech_clips": sum(bool(e.get("audio_url")) for e in speech),
                      "text_fallbacks": len(interrupted), "crash_interrupted_speech": len(interrupted),
                      "provider_text_fallbacks": 0, "buyer_restarts": int(restarted),
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
                    for repeat in range(1, self.repeats + 1):
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
    parser.add_argument("--seller-mode", choices=("mock", "codex"), default="mock")
    parser.add_argument("--data-mode", choices=("cached", "apify"), default="cached",
                        help="apify uses paid live scrapes; cached fallback fails acceptance")
    parser.add_argument("--repeats", type=int, choices=(1, 2, 3), default=3,
                        help="runs per act; approval/decline also run once each")
    args = parser.parse_args()
    settings = get_settings()
    require(settings.elevenlabs_api_key and settings.voice_max and settings.voice_viktor,
            "Configure ElevenLabs credentials and both voice IDs first")
    if args.data_mode == "cached":
        load_cache(JobSpec(), settings)
    else:
        require(settings.apify_token, "Configure APIFY_TOKEN first")
        print(f"Live data: up to {2 * args.repeats + 1} paid scrapes, each requesting a $1.10 cap.", flush=True)
    Rehearsal(args.browser, seller_mode=args.seller_mode, data_mode=args.data_mode, repeats=args.repeats).run()


if __name__ == "__main__":
    main()
