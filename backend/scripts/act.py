"""Run one demo act from the terminal and print the deal as it happens. Needs buyer + seller running.

Run: uv run python scripts/act.py honest|con|junk [--buyer http://localhost:8000]
Act 3: start the buyer with CRASH_AFTER_LOCK=1, run `act.py honest`, restart the buyer, run `act.py --watch`.
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings  # noqa: E402

FINAL = {"released", "refunded", "walked_away", "error"}
COLORS = {"blocked": "\033[1;31m", "error": "\033[1;31m", "released": "\033[1;32m", "refunded": "\033[1;33m",
          "needs_approval": "\033[1;35m", "already_paid": "\033[1;36m", "escrow_locked": "\033[36m"}
RESET = "\033[0m"
REQUEST_TIMEOUT = 10.0


def line(ev: dict) -> str:
    d, t = ev["data"], ev["type"]
    tags = ("[SIMULATED]" if ev["simulated"] else "[MASUMI]") + (" [STAGED]" if ev["staged"] else "")
    if t == "negotiation":
        who = "MAX   " if d["speaker"] == "max" else "VIKTOR"
        return f"  {who} ({d['action']} {d['price']:g}): {d['text']}"
    extra = {k: v for k, v in d.items() if k not in ("result", "text") and v not in (None, "", {})}
    return f"{COLORS.get(t, '')}{t.upper():15}{RESET} {tags} {json.dumps(extra, ensure_ascii=False)[:160]}"


def current_deal(client: httpx.Client, deal_id: str) -> dict | None:
    return next((deal for deal in client.get("/deals").raise_for_status().json()
                 if deal["deal_id"] == deal_id), None)


def run(client: httpx.Client, mode: str, watch: bool) -> int:
    prompted: set[str] = set()
    if watch:
        deals = client.get("/deals").raise_for_status().json()
        # The API sorts by latest update. SSE starts with all historic events;
        # those events must never repoint an already selected watch target.
        deal_id = deals[0]["deal_id"] if deals else None
    else:
        deal_id = client.post("/tasks", json={"demo_mode": mode}).raise_for_status().json()["deal_id"]
        print(f"deal {deal_id} ({mode})")
    with client.stream("GET", "/events", timeout=httpx.Timeout(REQUEST_TIMEOUT, read=None)) as response:
        response.raise_for_status()
        for raw in response.iter_lines():
            if not raw.startswith("data: "):
                continue
            ev = json.loads(raw[6:])
            if watch and deal_id is None and ev["type"] == "task_created":
                deal_id = ev["deal_id"]
            if deal_id is None or ev["deal_id"] != deal_id:
                continue
            print(line(ev), flush=True)
            if ev["type"] == "needs_approval" and deal_id not in prompted:
                deal = current_deal(client, deal_id)
                if (deal and deal["status"] == "agreed" and not deal.get("approved")
                        and not deal.get("escrow_ref")):
                    prompted.add(deal_id)
                    ok = input("approve? [y/N] ").strip().lower() == "y"
                    approval = client.post(f"/approvals/{deal_id}", json={"approve": ok})
                    if approval.status_code == 404:
                        print("Approval was already resolved or expired; continuing to watch.")
                    else:
                        approval.raise_for_status()
            if ev["type"] in FINAL:
                deal = current_deal(client, deal_id)
                expected = {"released": {"released"}, "refunded": {"refunded"},
                            "walked_away": {"walked", "blocked"}, "error": {"error", "paying"}}
                if deal and deal["status"] not in expected[ev["type"]]:
                    continue  # An older failed attempt may already be recovering.
                return 0 if ev["type"] != "error" else 1
    return 1


def buyer_headers() -> dict[str, str]:
    """The buyer's API_TOKEN from .env, when access control is on."""
    token = get_settings().api_token
    return {"X-API-Token": token} if token else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", choices=["honest", "con", "junk"], default="honest")
    ap.add_argument("--buyer", default="http://localhost:8000")
    ap.add_argument("--watch", action="store_true", help="don't start a task; follow the newest deal")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles; flats have Czech names.
    try:
        with httpx.Client(base_url=a.buyer, timeout=REQUEST_TIMEOUT, headers=buyer_headers()) as client:
            return run(client, a.mode, a.watch)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            print("Buyer rejected the API token (HTTP 401); API_TOKEN in .env must match the running buyer.")
        elif exc.response.status_code == 429:
            print("Buyer rate limit reached (HTTP 429); wait a minute or raise RATE_LIMIT_PER_MINUTE.")
        elif exc.response.status_code == 423:
            print("Agents are paused; resume them in the dashboard before starting an act.")
        else:
            print(f"Buyer request failed (HTTP {exc.response.status_code}); check the buyer service.")
        return 1
    except httpx.RequestError:
        print(f"{COLORS['blocked']}BUYER DOWN{RESET} connection lost or timed out. "
              "Act 3: restart the buyer, then `act.py --watch`.")
        return 2
    except (ValueError, KeyError, TypeError):
        print("Buyer returned an invalid response; check the buyer service.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
