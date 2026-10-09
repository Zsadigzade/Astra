"""SQLite ledger: deals and events survive a buyer crash (Act 3: nothing pays twice)."""

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

# Deal lifecycle. "paying" = guard started a lock and may have crashed mid-call.
# "agreed" = price settled, maybe waiting for a human approval that a restart lost.
OPEN_STATUSES = ("agreed", "paying", "locked", "delivered")

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
    start_json  TEXT,
    updated     REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id   INTEGER PRIMARY KEY,
    body TEXT NOT NULL
);
"""


class LedgerSafetyError(RuntimeError):
    """The ledger cannot safely be used with the requested payment operation."""


def payment_mode(db: sqlite3.Connection) -> str | None:
    """Read mode evidence, including ledgers created before mode binding existed."""
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    modes: set[str] = set()
    if "ledger_metadata" in tables:
        row = db.execute("SELECT value FROM ledger_metadata WHERE key = 'payments_mode'").fetchone()
        if row:
            modes.add(row[0])
    if tables & {"sim_wallets", "sim_escrows"}:
        modes.add("simulated")
    columns = {r[1] for r in db.execute("PRAGMA table_info(deals)")}
    start_column = "start_json" if "start_json" in columns else "NULL"
    ambiguous = False
    for ref, start_json, status in db.execute(f"SELECT escrow_ref, {start_column}, status FROM deals"):
        if ref:
            modes.add("simulated" if ref.startswith("SIM-") else "masumi")
        if start_json:
            try:
                start = json.loads(start_json)
                modes.add("masumi" if start.get("blockchainIdentifier") else "simulated")
            except (ValueError, AttributeError) as exc:
                raise LedgerSafetyError("Cannot identify payment mode from stored job data.") from exc
        if not ref and not start_json and status in {"paying", "locked", "delivered", "released", "refunded"}:
            ambiguous = True
    for (body,) in db.execute("SELECT body FROM events"):
        try:
            simulated = json.loads(body).get("simulated")
        except (ValueError, AttributeError) as exc:
            raise LedgerSafetyError("Cannot identify payment mode from stored events.") from exc
        if isinstance(simulated, bool):
            modes.add("simulated" if simulated else "masumi")
    if len(modes) > 1 or modes - {"simulated", "masumi"}:
        raise LedgerSafetyError("Ledger contains conflicting payment modes; preserve it and use a separate LEDGER_PATH.")
    if not modes and ambiguous:
        raise LedgerSafetyError("Legacy ledger has payment activity with unknown mode; preserve it and use a separate LEDGER_PATH.")
    return next(iter(modes), None)


class Ledger:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(deals)")}
        if "start_json" not in cols:  # ledgers created before the column existed
            self.db.execute("ALTER TABLE deals ADD COLUMN start_json TEXT")

    def bind_payment_mode(self, mode: str) -> None:
        """Bind before constructing an adapter or resuming any deals, atomically."""
        if mode not in {"simulated", "masumi"}:
            raise LedgerSafetyError("PAYMENTS_MODE must be simulated or masumi.")
        with self.tx() as db:
            existing = payment_mode(db)
            if existing is not None and existing != mode:
                raise LedgerSafetyError(
                    f"Ledger belongs to {existing} payments, not {mode}; use a separate LEDGER_PATH."
                )
            db.execute("CREATE TABLE IF NOT EXISTS ledger_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO ledger_metadata VALUES ('payments_mode', ?)", (mode,))

    def bind_currency(self, currency: str = "USD") -> None:
        """Bind the money unit. Ledgers from before the USD switch hold tADA amounts: refuse them."""
        with self.tx() as db:
            db.execute("CREATE TABLE IF NOT EXISTS ledger_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            row = db.execute("SELECT value FROM ledger_metadata WHERE key = 'currency'").fetchone()
            if row:
                if row[0] != currency:
                    raise LedgerSafetyError(f"Ledger amounts are in {row[0]}, not {currency}; use a separate LEDGER_PATH.")
                return
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            paid = db.execute("SELECT 1 FROM deals WHERE price IS NOT NULL OR escrow_ref IS NOT NULL LIMIT 1").fetchone()
            if paid or "sim_wallets" in tables:
                raise LedgerSafetyError("Ledger holds tADA amounts from before the USD switch; "
                                        "preserve it and use a separate LEDGER_PATH.")
            db.execute("INSERT INTO ledger_metadata VALUES ('currency', ?)", (currency,))

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
        # A funded deal that errored still holds escrow: resume it, never strand the money.
        q = (f"SELECT * FROM deals WHERE status IN ({','.join('?' * len(OPEN_STATUSES))}) "
             "OR (status = 'error' AND escrow_ref IS NOT NULL)")
        return [dict(r) for r in self.db.execute(q, OPEN_STATUSES)]

    def spent(self, task_id: str, exclude_deal: str | None = None) -> float:
        """USD committed for a task: locked or released, not refunded."""
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
