"""Thin client for the Masumi payment service, used by buyer (purchase side) and seller (payment side).

Shapes taken from masumi-network/masumi-payment-service `main` (pushed 2026-10-06) and the
pip-masumi SDK. Every response is wrapped as {"status": ..., "data": {...}}. Auth header: `token`.
Amounts are lovelace strings; unit "" = ADA.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

LOVELACE_PER_ADA = 1_000_000
LOCKED_STATES = {"FundsLocked", "ResultSubmitted", "RefundRequested", "Disputed",
                 "WithdrawAuthorized", "RefundAuthorized", "Withdrawn", "RefundWithdrawn", "DisputedWithdrawn"}
EXPLORER_TX = "https://preprod.cardanoscan.io/transaction/{}"


class MasumiError(Exception):
    pass


def to_lovelace(tada: float) -> str:
    return str(round(tada * LOVELACE_PER_ADA))


def input_hash(input_data: dict[str, Any], purchaser_id: str) -> str:
    """MIP-004: sha256("<identifierFromPurchaser>;<canonical JSON of input_data>")."""
    canon = json.dumps(input_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(f"{purchaser_id};{canon}".encode()).hexdigest()


def output_hash(output: str, purchaser_id: str) -> str:
    """MIP-004: sha256("<identifierFromPurchaser>;<JSON-escaped output string>")."""
    escaped = json.dumps(output, ensure_ascii=False)[1:-1]
    return hashlib.sha256(f"{purchaser_id};{escaped}".encode()).hexdigest()


def tx_link(record: dict[str, Any] | None) -> str | None:
    tx = ((record or {}).get("CurrentTransaction") or {}).get("txHash")
    return EXPLORER_TX.format(tx) if tx else None


def _iso_in(minutes: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class MasumiClient:
    def __init__(self, base_url: str, api_key: str, network: str = "Preprod",
                 http: httpx.AsyncClient | None = None):
        self.base = base_url.rstrip("/")
        self.network = network
        self.headers = {"token": api_key}
        self.http = http or httpx.AsyncClient(timeout=30)

    async def _call(self, method: str, path: str, body: dict | None = None,
                    missing_ok: bool = False) -> dict[str, Any] | None:
        r = await self.http.request(method, f"{self.base}{path}", json=body, headers=self.headers)
        if missing_ok and r.status_code == 404:
            return None
        if r.is_error:
            # Provider bodies may echo credentials; errors also reach dashboard events.
            raise MasumiError(f"{method} {path} -> HTTP {r.status_code}")
        data = r.json()
        return data.get("data", data) if isinstance(data, dict) else data

    async def health(self) -> dict[str, Any]:
        return await self._call("GET", "/health")

    # ---------- seller side ----------

    async def create_payment(self, agent_id: str, in_hash: str, purchaser_id: str, amount_tada: float,
                             pay_by_minutes: float, submit_minutes: float) -> dict[str, Any]:
        return await self._call("POST", "/payment", {
            "network": self.network,
            "agentIdentifier": agent_id,
            "inputHash": in_hash,
            "identifierFromPurchaser": purchaser_id,
            "RequestedFunds": [{"amount": to_lovelace(amount_tada), "unit": ""}],  # Dynamic pricing
            "payByTime": _iso_in(pay_by_minutes),
            "submitResultTime": _iso_in(submit_minutes),
        })

    async def resolve_payment(self, blockchain_id: str) -> dict[str, Any] | None:
        return await self._call("POST", "/payment/resolve-blockchain-identifier",
                                {"network": self.network, "blockchainIdentifier": blockchain_id}, missing_ok=True)

    async def submit_result(self, blockchain_id: str, result_hash: str) -> dict[str, Any]:
        return await self._call("POST", "/payment/submit-result", {
            "network": self.network, "blockchainIdentifier": blockchain_id, "submitResultHash": result_hash})

    # ---------- buyer side ----------

    async def create_purchase(self, start: dict[str, Any], purchaser_id: str, amount_tada: float) -> dict[str, Any]:
        keys = ("blockchainIdentifier", "payByTime", "submitResultTime", "unlockTime",
                "externalDisputeUnlockTime", "agentIdentifier", "sellerVKey", "inputHash")
        missing = [k for k in keys if not start.get(k)]
        if missing:
            raise MasumiError(f"seller start_job response lacks {missing}")
        return await self._call("POST", "/purchase", {
            "network": self.network,
            "identifierFromPurchaser": purchaser_id,
            "blockchainIdentifier": start["blockchainIdentifier"],
            "payByTime": str(start["payByTime"]),
            "submitResultTime": str(start["submitResultTime"]),
            "unlockTime": str(start["unlockTime"]),
            "externalDisputeUnlockTime": str(start["externalDisputeUnlockTime"]),
            "agentIdentifier": start["agentIdentifier"],
            "sellerVkey": start["sellerVKey"],
            "inputHash": start["inputHash"],
            "Amounts": [{"amount": to_lovelace(amount_tada), "unit": ""}],
        })

    async def resolve_purchase(self, blockchain_id: str) -> dict[str, Any] | None:
        return await self._call("POST", "/purchase/resolve-blockchain-identifier",
                                {"network": self.network, "blockchainIdentifier": blockchain_id}, missing_ok=True)

    async def request_refund(self, blockchain_id: str) -> dict[str, Any]:
        return await self._call("POST", "/purchase/request-refund",
                                {"network": self.network, "blockchainIdentifier": blockchain_id})
