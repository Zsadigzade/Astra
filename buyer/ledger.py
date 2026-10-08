"""SQLite ledger: deals and events survive a buyer crash (Act 3: nothing pays twice)."""

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

# Deal lifecycle. "paying" = guard started a lock and may have crashed mid-call.
OPEN_STATUSES = ("paying", "locked", "delivered")

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
    deal_id     TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL,
    task_json   TEXT NOT NULL,
    seller_url  TEXT NOT NULL,
    status      TEXT NOT NULL,
    price       REAL,
    approved    INTEGER NOT NULL DEFAULT 0,
    job_id      TEXT,
    escrow_ref  TEXT,
    updated     REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id   INTEGER PRIMARY KEY,
    body TEXT NOT NULL
);
"""


class Ledger:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield self.db
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    # ---------- deals ----------

    def create_deal(self, deal_id: str, task_id: str, task_json: str, seller_url: str) -> None:
        self.db.execute(
            "INSERT INTO deals (deal_id, task_id, task_json, seller_url, status, updated) VALUES (?,?,?,?,?,?)",
            (deal_id, task_id, task_json, seller_url, "negotiating", time.time()),
        )

    def get(self, deal_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,)).fetchone()
        return dict(row) if row else None

    def update(self, deal_id: str, **fields: Any) -> None:
        fields["updated"] = time.time()
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.db.execute(f"UPDATE deals SET {cols} WHERE deal_id = ?", (*fields.values(), deal_id))

    def all_deals(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.db.execute("SELECT * FROM deals ORDER BY updated DESC")]

    def unfinished(self) -> list[dict[str, Any]]:
        q = f"SELECT * FROM deals WHERE status IN ({','.join('?' * len(OPEN_STATUSES))})"
        return [dict(r) for r in self.db.execute(q, OPEN_STATUSES)]

    def spent(self, task_id: str, exclude_deal: str | None = None) -> float:
        """tADA committed for a task: locked or released, not refunded."""
        row = self.db.execute(
            "SELECT COALESCE(SUM(price), 0) FROM deals WHERE task_id = ? AND escrow_ref IS NOT NULL "
            "AND status != 'refunded' AND deal_id != COALESCE(?, '')",
            (task_id, exclude_deal),
        ).fetchone()
        return float(row[0])

    # ---------- events ----------

    def append_event(self, event_id: int, body: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO events (id, body) VALUES (?, ?)", (event_id, json.dumps(body)))

    def load_events(self) -> list[dict[str, Any]]:
        return [json.loads(r[0]) for r in self.db.execute("SELECT body FROM events ORDER BY id")]
