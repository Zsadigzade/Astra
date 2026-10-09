"""Durable seller state: job statuses, start acknowledgements and Viktor's agreements.

A seller restart must not strand a funded deal: the buyer's stored job id has to keep answering
/status, a retried /start_job must return the same job, and an agreed price must stay agreed.
One SQLite connection (WAL for files), every call serialized by a lock; ":memory:" for tests.
"""

import sqlite3
import threading
from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass
from pathlib import Path

from app.core.models import BoundedJobSpec, DemoMode, StartJobResponse, StatusResponse
from app.seller.persona import DealState

SCHEMA = """
CREATE TABLE IF NOT EXISTS seller_jobs (
    job_id TEXT PRIMARY KEY,
    status_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS seller_starts (
    purchaser TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    response_json TEXT NOT NULL,
    job_json TEXT NOT NULL,
    demo_mode TEXT NOT NULL,
    blockchain_id TEXT,
    deadline REAL
);
CREATE TABLE IF NOT EXISTS seller_deals (
    deal_id TEXT PRIMARY KEY,
    ask REAL NOT NULL,
    agreed REAL,
    walked INTEGER NOT NULL
);
"""


@dataclass(frozen=True)
class StartRecord:
    purchaser: str
    job_id: str
    response: StartJobResponse
    job: BoundedJobSpec
    demo_mode: DemoMode
    blockchain_id: str | None
    deadline: float | None


class SellerStore:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=10)
        with self._lock:
            if path != ":memory:":
                self._db.execute("PRAGMA journal_mode=WAL")
                self._db.execute("PRAGMA synchronous=NORMAL")
            self._db.executescript(SCHEMA)

    def _run(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock:
            return self._db.execute(sql, params).fetchall()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # --- job statuses ---
    def put_status(self, status: StatusResponse) -> None:
        self._run("INSERT INTO seller_jobs VALUES (?, ?) ON CONFLICT(job_id) DO UPDATE SET status_json=excluded.status_json",
                  (status.job_id, status.model_dump_json()))

    def statuses(self) -> dict[str, StatusResponse]:
        return {job_id: StatusResponse.model_validate_json(body)
                for job_id, body in self._run("SELECT job_id, status_json FROM seller_jobs")}

    # --- start acknowledgements (idempotency per purchaser + what a restart needs to resume) ---
    def put_start(self, purchaser: str, response: StartJobResponse, job: BoundedJobSpec, demo_mode: DemoMode,
                  blockchain_id: str | None = None, deadline: float | None = None) -> None:
        self._run("INSERT OR REPLACE INTO seller_starts VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (purchaser, response.job_id, response.model_dump_json(), job.model_dump_json(),
                   demo_mode.value, blockchain_id, deadline))

    def starts(self) -> list[StartRecord]:
        rows = self._run("SELECT purchaser, job_id, response_json, job_json, demo_mode, blockchain_id, deadline "
                         "FROM seller_starts")
        return [StartRecord(p, j, StartJobResponse.model_validate_json(r), BoundedJobSpec.model_validate_json(js),
                            DemoMode(m), b, d) for p, j, r, js, m, b, d in rows]

    # --- Viktor's negotiation state ---
    def get_deal(self, deal_id: str) -> DealState | None:
        rows = self._run("SELECT ask, agreed, walked FROM seller_deals WHERE deal_id=?", (deal_id,))
        if not rows:
            return None
        ask, agreed, walked = rows[0]
        return DealState(ask=ask, agreed=agreed, walked=bool(walked))

    def put_deal(self, deal_id: str, state: DealState) -> None:
        self._run("INSERT OR REPLACE INTO seller_deals VALUES (?, ?, ?, ?)",
                  (deal_id, float(state.ask), None if state.agreed is None else float(state.agreed),
                   int(bool(state.walked))))

    def delete_deal(self, deal_id: str) -> bool:
        with self._lock:
            return self._db.execute("DELETE FROM seller_deals WHERE deal_id=?", (deal_id,)).rowcount > 0

    def deal_ids(self) -> list[str]:
        return [row[0] for row in self._run("SELECT deal_id FROM seller_deals")]


class PersistentDeals(MutableMapping):
    """Write-through replacement for `Viktor.deals`.

    Reads return a fresh DealState; the persona mutates it and assigns it back
    (`self.deals[deal_id] = state`), which is the write that persists it.
    """

    def __init__(self, store: SellerStore):
        self.store = store

    def __getitem__(self, deal_id: str) -> DealState:
        state = self.store.get_deal(deal_id)
        if state is None:
            raise KeyError(deal_id)
        return state

    def __setitem__(self, deal_id: str, state: DealState) -> None:
        self.store.put_deal(deal_id, state)

    def __delitem__(self, deal_id: str) -> None:
        if not self.store.delete_deal(deal_id):
            raise KeyError(deal_id)

    def __iter__(self) -> Iterator[str]:
        return iter(self.store.deal_ids())

    def __len__(self) -> int:
        return len(self.store.deal_ids())
