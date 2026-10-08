"""In-memory stand-in for the Masumi payment service: same paths, wrapper and field names as
masumi-payment-service main (2026-10-06). One node holds both the seller and buyer sides, as ours will.
On-chain confirmation is instant here; on Preprod each step takes minutes."""

import time
import uuid

from fastapi import FastAPI, HTTPException, Request


def create_fake_masumi(api_key: str = "test-key") -> FastAPI:
    app = FastAPI()
    payments: dict[str, dict] = {}
    purchases: dict[str, dict] = {}
    app.state.payments, app.state.purchases = payments, purchases

    @app.middleware("http")
    async def auth(request: Request, call_next):
        if request.headers.get("token") != api_key:
            from fastapi.responses import JSONResponse
            return JSONResponse({"status": "error", "error": "Unauthorized"}, 401)
        return await call_next(request)

    def ok(data):
        return {"status": "success", "data": data}

    def find(store, body):
        rec = store.get(body["blockchainIdentifier"])
        if rec is None:
            raise HTTPException(404, "not found")
        return rec

    @app.get("/health")
    async def health():
        return ok({"type": "masumi-payment", "version": "fake"})

    @app.post("/payment")
    async def create_payment(body: dict):
        assert body["RequestedFunds"][0]["unit"] == ""
        assert 14 <= len(body["identifierFromPurchaser"]) <= 26
        int(body["identifierFromPurchaser"], 16)  # must be hex
        now = int(time.time() * 1000)
        bid = f"bid-{uuid.uuid4().hex}"
        payments[bid] = {"blockchainIdentifier": bid, "onChainState": None, "inputHash": body["inputHash"],
                         "RequestedFunds": body["RequestedFunds"], "payByTime": str(now + 600_000),
                         "submitResultTime": str(now + 1_200_000), "unlockTime": str(now + 1_800_000),
                         "externalDisputeUnlockTime": str(now + 3_600_000), "resultHash": None,
                         "CurrentTransaction": None, "NextAction": {"requestedAction": "WaitingForExternalAction"}}
        return ok(payments[bid])

    @app.post("/payment/resolve-blockchain-identifier")
    async def resolve_payment(body: dict):
        return ok(find(payments, body))

    @app.post("/payment/submit-result")
    async def submit_result(body: dict):
        pay = find(payments, body)
        assert len(body["submitResultHash"]) == 64
        pay.update(onChainState="ResultSubmitted", resultHash=body["submitResultHash"])
        purchases[pay["blockchainIdentifier"]]["onChainState"] = "ResultSubmitted"
        return ok(pay)

    @app.post("/purchase")
    async def create_purchase(body: dict):
        pay = find(payments, body)
        assert body["inputHash"] == pay["inputHash"]
        assert body["Amounts"] == pay["RequestedFunds"]
        if body["blockchainIdentifier"] in purchases:
            raise HTTPException(409, "purchase exists")
        tx = {"txHash": uuid.uuid4().hex * 2}
        purchases[body["blockchainIdentifier"]] = {**body, "onChainState": "FundsLocked", "CurrentTransaction": tx,
                                                   "NextAction": {"requestedAction": "WaitingForExternalAction"}}
        pay.update(onChainState="FundsLocked", CurrentTransaction=tx)
        return ok(purchases[body["blockchainIdentifier"]])

    @app.post("/purchase/resolve-blockchain-identifier")
    async def resolve_purchase(body: dict):
        return ok(find(purchases, body))

    @app.post("/purchase/request-refund")
    async def request_refund(body: dict):
        pur = find(purchases, body)
        pur["onChainState"] = "Disputed" if pur["onChainState"] == "ResultSubmitted" else "RefundRequested"
        return ok(pur)

    return app
