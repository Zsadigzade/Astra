"""Run one demo act from the terminal and print the deal as it happens. Needs buyer + seller running.

Run: uv run python scripts/act.py honest|con|junk [--buyer http://localhost:8000]
Act 3: start the buyer with CRASH_AFTER_LOCK=1, run `act.py honest`, restart the buyer, run `act.py --watch`.
"""

import argparse
import json
import sys

import httpx

FINAL = {"released", "refunded", "walked_away", "error"}
COLORS = {"blocked": "\033[1;31m", "error": "\033[1;31m", "released": "\033[1;32m", "refunded": "\033[1;33m",
          "needs_approval": "\033[1;35m", "already_paid": "\033[1;36m", "escrow_locked": "\033[36m"}
RESET = "\033[0m"


def line(ev: dict) -> str:
    d, t = ev["data"], ev["type"]
    tags = ("[SIMULATED]" if ev["simulated"] else "[MASUMI]") + (" [STAGED]" if ev["staged"] else "")
    if t == "negotiation":
        who = "MAX   " if d["speaker"] == "max" else "VIKTOR"
        return f"  {who} ({d['action']} {d['price']:g}): {d['text']}"
    extra = {k: v for k, v in d.items() if k not in ("result", "text") and v not in (None, "", {})}
    return f"{COLORS.get(t, '')}{t.upper():15}{RESET} {tags} {json.dumps(extra, ensure_ascii=False)[:160]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", choices=["honest", "con", "junk"], default="honest")
    ap.add_argument("--buyer", default="http://localhost:8000")
    ap.add_argument("--watch", action="store_true", help="don't start a task; follow the newest deal")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252; flats have Czech names

    with httpx.Client(base_url=a.buyer, timeout=None) as c:
        deal_id = None
        if not a.watch:
            deal_id = c.post("/tasks", json={"demo_mode": a.mode}).raise_for_status().json()["deal_id"]
            print(f"deal {deal_id} ({a.mode})")
        with c.stream("GET", "/events") as r:
            for raw in r.iter_lines():
                if not raw.startswith("data: "):
                    continue
                ev = json.loads(raw[6:])
                if a.watch and ev["type"] in ("already_paid", "task_created"):
                    deal_id = ev["deal_id"]  # replayed history: follow the newest deal
                if ev["deal_id"] != deal_id:
                    continue
                print(line(ev), flush=True)
                if ev["type"] == "needs_approval":
                    ok = input("approve? [y/N] ").strip().lower() == "y"
                    c.post(f"/approvals/{deal_id}", json={"approve": ok}).raise_for_status()
                if ev["type"] in FINAL:
                    return 0 if ev["type"] != "error" else 1
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError):
        print(f"{COLORS['blocked']}BUYER DOWN{RESET} connection lost. Act 3: restart the buyer, then `act.py --watch`.")
        sys.exit(2)
