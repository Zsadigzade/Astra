"""Payment adapters. Only the WalletGuard holds one; agents never call these directly.

Every method is idempotent per deal_id, so a crash-and-retry can never move money twice.
"""

from dataclasses import dataclass
from typing import Protocol

import httpx

from buyer.ledger import Ledger
from shared.config import Settings
from shared.models import StartJobResponse

BUYER_START_BALANCE = 100.0  # tADA, simulated wallet only


@dataclass
class LockResult:
    ref: str
    already: bool  # True = this deal was already paid; nothing moved now


class InsufficientFunds(Exception):
    pass


class Payments(Protocol):
    simulated: bool

    async def lock(self, deal_id: str, amount: float, seller: str, start: StartJobResponse) -> LockResult: ...
    async def release(self, deal_id: str) -> None: ...
    async def refund(self, deal_id: str) -> None: ...
    async def balances(self) -> dict[str, float]: ...


class SimulatedPayments:
    """SIMULATED escrow in the buyer's SQLite file. Labelled SIMULATED in every event."""

    simulated = True

    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        ledger.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sim_wallets (name TEXT PRIMARY KEY, balance REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sim_escrows (
                deal_id TEXT PRIMARY KEY, amount REAL NOT NULL, seller TEXT NOT NULL,
                status TEXT NOT NULL, ref TEXT NOT NULL
            );
            """
        )
        ledger.db.execute("INSERT OR IGNORE INTO sim_wallets VALUES ('buyer', ?)", (BUYER_START_BALANCE,))

    def _add(self, db, name: str, delta: float) -> None:
        db.execute("INSERT OR IGNORE INTO sim_wallets VALUES (?, 0)", (name,))
        db.execute("UPDATE sim_wallets SET balance = balance + ? WHERE name = ?", (delta, name))

    async def lock(self, deal_id: str, amount: float, seller: str, start: StartJobResponse) -> LockResult:
        with self.ledger.tx() as db:
            row = db.execute("SELECT ref FROM sim_escrows WHERE deal_id = ?", (deal_id,)).fetchone()
            if row:
                return LockResult(ref=row["ref"], already=True)
            bal = db.execute("SELECT balance FROM sim_wallets WHERE name = 'buyer'").fetchone()["balance"]
            if bal < amount:
                raise InsufficientFunds(f"buyer has {bal}, needs {amount}")
            ref = f"SIM-{deal_id}"
            self._add(db, "buyer", -amount)
            db.execute("INSERT INTO sim_escrows VALUES (?,?,?,?,?)", (deal_id, amount, seller, "locked", ref))
            return LockResult(ref=ref, already=False)

    async def _settle(self, deal_id: str, to_seller: bool) -> None:
        with self.ledger.tx() as db:
            row = db.execute("SELECT * FROM sim_escrows WHERE deal_id = ?", (deal_id,)).fetchone()
            if not row or row["status"] != "locked":
                return  # already settled: idempotent
            self._add(db, row["seller"] if to_seller else "buyer", row["amount"])
            status = "released" if to_seller else "refunded"
            db.execute("UPDATE sim_escrows SET status = ? WHERE deal_id = ?", (status, deal_id))

    async def release(self, deal_id: str) -> None:
        await self._settle(deal_id, to_seller=True)

    async def refund(self, deal_id: str) -> None:
        await self._settle(deal_id, to_seller=False)

    async def balances(self) -> dict[str, float]:
        db = self.ledger.db
        wallets = {r["name"]: r["balance"] for r in db.execute("SELECT * FROM sim_wallets")}
        escrow = db.execute("SELECT COALESCE(SUM(amount),0) FROM sim_escrows WHERE status='locked'").fetchone()[0]
        return {
            "buyer": wallets.get("buyer", 0.0),
            "seller": sum(v for k, v in wallets.items() if k != "buyer"),
            "escrow": float(escrow),
        }


class MasumiPayments:
    """Masumi Preprod escrow. TODO(ziya): fill in once the hosted payment service answers /health.

    Unverified assumptions, check against the Masumi docs before relying on them:
    - auth header name is `token`
    - buyer locks funds with POST /purchase using fields from the seller's start_job response,
      identifierFromPurchaser = deal_id (that is our idempotency key on-chain too)
    - release is time-based (unlock time) unless the buyer requests a refund before it
    - whether a payment request can carry a per-job (negotiated) amount
    """

    simulated = False

    def __init__(self, settings: Settings):
        self.base = settings.masumi_payment_url.rstrip("/")
        self.headers = {"token": settings.masumi_api_key}

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{self.base}/health", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def lock(self, deal_id: str, amount: float, seller: str, start: StartJobResponse) -> LockResult:
        raise NotImplementedError("TODO(ziya): look up purchase by deal_id, else POST /purchase")

    async def release(self, deal_id: str) -> None:
        raise NotImplementedError("TODO(ziya): Masumi releases after unlock time; confirm flow")

    async def refund(self, deal_id: str) -> None:
        raise NotImplementedError("TODO(ziya): request refund before unlock time")

    async def balances(self) -> dict[str, float]:
        raise NotImplementedError("TODO(ziya): wallet balances from payment service")


def make_payments(settings: Settings, ledger: Ledger) -> Payments:
    return MasumiPayments(settings) if settings.payments_mode == "masumi" else SimulatedPayments(ledger)
