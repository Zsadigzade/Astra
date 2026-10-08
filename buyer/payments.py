"""Payment adapters. Only the WalletGuard holds one; agents never call these directly.

Every method is idempotent per deal_id, so a crash-and-retry can never move money twice.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from buyer.ledger import Ledger
from shared.config import Settings
from shared.masumi import MasumiClient, MasumiError, tx_link
from shared.models import StartJobResponse

BUYER_START_BALANCE = 100.0  # tADA, simulated wallet only
BUYER_TOPUP_BELOW = 20.0  # rehearsals drain the simulated wallet; refill on startup

log = logging.getLogger("astra.payments")


@dataclass
class LockResult:
    ref: str
    already: bool  # True = this deal was already paid; nothing moved now
    info: dict[str, Any] = field(default_factory=dict)  # extra event data (tx link, on-chain state)


class InsufficientFunds(Exception):
    pass


class Payments(Protocol):
    simulated: bool

    async def lock(self, deal_id: str, amount: float, seller: str, start: StartJobResponse) -> LockResult: ...
    async def release(self, deal_id: str) -> dict[str, Any]: ...
    async def refund(self, deal_id: str) -> dict[str, Any]: ...
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
        bal = ledger.db.execute("SELECT balance FROM sim_wallets WHERE name = 'buyer'").fetchone()["balance"]
        if bal < BUYER_TOPUP_BELOW:
            ledger.db.execute("UPDATE sim_wallets SET balance = ? WHERE name = 'buyer'", (BUYER_START_BALANCE,))
            log.warning("[SIMULATED] top-up: buyer wallet %g -> %g tADA", bal, BUYER_START_BALANCE)

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

    async def _settle(self, deal_id: str, to_seller: bool) -> dict[str, Any]:
        with self.ledger.tx() as db:
            row = db.execute("SELECT * FROM sim_escrows WHERE deal_id = ?", (deal_id,)).fetchone()
            if not row or row["status"] != "locked":
                return {}  # already settled: idempotent
            self._add(db, row["seller"] if to_seller else "buyer", row["amount"])
            status = "released" if to_seller else "refunded"
            db.execute("UPDATE sim_escrows SET status = ? WHERE deal_id = ?", (status, deal_id))
        return {}

    async def release(self, deal_id: str) -> dict[str, Any]:
        return await self._settle(deal_id, to_seller=True)

    async def refund(self, deal_id: str) -> dict[str, Any]:
        return await self._settle(deal_id, to_seller=False)

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
    """Masumi Preprod escrow via the hosted payment service (buyer = purchasing side).

    - lock: idempotent. Looks the purchase up by the seller's blockchainIdentifier first; the
      identifierFromPurchaser is our deal_id, so a restarted buyer finds its own purchase.
    - release: Masumi has no buyer-triggered release. The seller submits the result hash and funds
      unlock for the seller after unlockTime. We report that state and time (`settles_at`).
    - refund: buyer requests a refund; if the seller already submitted a result this becomes a
      dispute the seller must authorize. Decided 21:45: Act 4 runs SIMULATED.
    """

    simulated = False

    def __init__(self, settings: Settings, ledger: Ledger, http: httpx.AsyncClient | None = None):
        self.ledger = ledger
        self.client = MasumiClient(settings.masumi_payment_url, settings.masumi_api_key,
                                   settings.masumi_network, http)

    def _ref(self, deal_id: str) -> str:
        deal = self.ledger.get(deal_id)
        if not deal or not deal["escrow_ref"]:
            raise MasumiError(f"deal {deal_id} has no Masumi purchase")
        return deal["escrow_ref"]

    async def health(self) -> dict:
        return await self.client.health()

    async def lock(self, deal_id: str, amount: float, seller: str, start: StartJobResponse) -> LockResult:
        bid = start.blockchainIdentifier
        if not bid:
            raise MasumiError("seller returned no blockchainIdentifier (is the seller in masumi mode?)")
        existing = await self.client.resolve_purchase(bid)
        if existing:
            return LockResult(ref=bid, already=True, info=_state(existing))
        purchase = await self.client.create_purchase(start.model_dump(), deal_id, amount)
        return LockResult(ref=bid, already=False, info=_state(purchase))

    async def release(self, deal_id: str) -> dict[str, Any]:
        purchase = await self.client.resolve_purchase(self._ref(deal_id))
        return {**_state(purchase), "release": "scheduled", "settles_at": (purchase or {}).get("unlockTime")}

    async def refund(self, deal_id: str) -> dict[str, Any]:
        return _state(await self.client.request_refund(self._ref(deal_id)))

    async def balances(self) -> dict[str, float]:
        raise NotImplementedError("Masumi balances not wired; show tx links instead")


def _state(record: dict[str, Any] | None) -> dict[str, Any]:
    record = record or {}
    return {"on_chain_state": record.get("onChainState"), "tx_url": tx_link(record),
            "next_action": (record.get("NextAction") or {}).get("requestedAction")}


def make_payments(settings: Settings, ledger: Ledger, http: httpx.AsyncClient | None = None) -> Payments:
    if settings.payments_mode == "masumi":
        return MasumiPayments(settings, ledger, http)
    return SimulatedPayments(ledger)
