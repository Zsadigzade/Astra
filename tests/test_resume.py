"""Restart recovery: funded deals are never stranded, the seller is never asked to start twice."""

import asyncio
import sqlite3

import httpx
import pytest

from buyer.app import create_app as create_buyer
from buyer.ledger import Ledger
from buyer.payments import SimulatedPayments
from seller.app import create_app as create_seller
from seller.job import sample_flats
from shared.config import Settings
from shared.masumi import MasumiClient
from shared.models import (
    JobResult,
    JobSpec,
    StartJobResponse,
    StatusResponse,
    TaskCreate,
)
from tests.test_masumi import masumi_settings

TASK = TaskCreate().model_dump_json()
OLD_START = StartJobResponse(status="success", job_id="j-old", price=7)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def settings(tmp_path, **kw) -> Settings:
    return Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"),
                    seller_url="http://seller", **kw)


def seed(s: Settings, deal_id: str, status: str, **fields) -> Ledger:
    ledger = Ledger(s.ledger_path)
    ledger.create_deal(deal_id, "t-1", TASK, s.seller_url)
    ledger.update(deal_id, status=status, **fields)
    return ledger


class FakeSeller:
    """Records every call; /start_job hands out a NEW job, like a restarted seller would."""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append((req.url.path, req.url.params.get("job_id", "")))
        if req.url.path == "/start_job":
            return httpx.Response(200, json=StartJobResponse(status="success", job_id="j-new", price=7).model_dump())
        if req.url.path == "/status":
            result = JobResult(flats=sample_flats(JobSpec()), source="sample")
            st = StatusResponse(job_id=req.url.params["job_id"], status="completed", result=result)
            return httpx.Response(200, json=st.model_dump())
        return httpx.Response(200, json={"deal_id": "x", "round": 99, "action": "walk", "price": 0, "message": ""})

    def paths(self) -> list[str]:
        return [p for p, _ in self.calls]


async def restart(s: Settings, seller: FakeSeller, until: set[str], approve: bool | None = None):
    """Start the buyer on an existing ledger (lifespan runs resume_unfinished) and wait for an event."""
    http = httpx.AsyncClient(transport=httpx.MockTransport(seller), base_url=s.seller_url)
    buyer = create_buyer(s, http=http)
    async with buyer.router.lifespan_context(buyer):
        for _ in range(500):
            types = {e.type for e in buyer.state.bus.history}
            if "needs_approval" in types and approve is not None:
                buyer.state.orch.approve(next(e.deal_id for e in buyer.state.bus.history
                                              if e.type == "needs_approval"), approve)
            if until & types:
                break
            await asyncio.sleep(0.01)
        bal = await buyer.state.guard.balances()
    await http.aclose()
    return buyer, bal


@pytest.mark.anyio
async def test_errored_funded_deal_resumes_without_relock_or_new_start(tmp_path):
    s = settings(tmp_path)
    ledger = seed(s, "d1", "error", price=7, escrow_ref="SIM-d1", job_id="j-old",
                  start_json=OLD_START.model_dump_json())
    await SimulatedPayments(ledger).lock("d1", 7, "http://seller", OLD_START)
    seller = FakeSeller()
    buyer, bal = await restart(s, seller, {"released", "refunded", "error"})
    types = [e.type for e in buyer.state.bus.history]
    assert "already_paid" in types and "released" in types and "escrow_locked" not in types
    assert "/start_job" not in seller.paths()
    assert ("/status", "j-old") in seller.calls  # polled the job the escrow was locked for
    assert (bal["buyer"], bal["seller"], bal["escrow"]) == (93, 7, 0)
    assert buyer.state.ledger.get("d1")["status"] == "released"


@pytest.mark.anyio
async def test_crash_after_lock_reuses_stored_start(tmp_path):
    # Act 3 gap: money locked, ledger still says "paying". Seller restarted meanwhile.
    s = settings(tmp_path)
    ledger = seed(s, "d1", "paying", price=7, job_id="j-old", start_json=OLD_START.model_dump_json())
    await SimulatedPayments(ledger).lock("d1", 7, "http://seller", OLD_START)
    seller = FakeSeller()
    buyer, bal = await restart(s, seller, {"released", "refunded", "error"})
    assert "already_paid" in [e.type for e in buyer.state.bus.history]
    assert "/start_job" not in seller.paths()
    assert bal["buyer"] == 93


@pytest.mark.anyio
async def test_start_is_saved_before_pay(tmp_path, monkeypatch):
    s = settings(tmp_path)
    seed(s, "d1", "agreed", price=7)
    seen = {}

    async def crash_in_pay(self, deal_id, *a, **kw):
        seen["start_json"] = self.ledger.get(deal_id)["start_json"]
        raise RuntimeError("buyer died inside guard.pay")

    monkeypatch.setattr("buyer.guard.WalletGuard.pay", crash_in_pay)
    seller = FakeSeller()
    await restart(s, seller, {"error"})
    assert StartJobResponse.model_validate_json(seen["start_json"]).job_id == "j-new"
    assert seller.paths().count("/start_job") == 1


@pytest.mark.anyio
async def test_failure_after_lock_keeps_deal_resumable(tmp_path):
    s = settings(tmp_path)
    seed(s, "d1", "locked", price=7, escrow_ref="SIM-d1", job_id="j-old", start_json=OLD_START.model_dump_json())
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)), base_url=s.seller_url)
    buyer = create_buyer(s, http=http)
    async with buyer.router.lifespan_context(buyer):
        for _ in range(500):
            if "error" in {e.type for e in buyer.state.bus.history}:
                break
            await asyncio.sleep(0.01)
    await http.aclose()
    ledger = buyer.state.ledger
    assert ledger.get("d1")["status"] == "error"
    assert [d["deal_id"] for d in ledger.unfinished()] == ["d1"]
    assert ledger.spent("t-1") == 7  # still committed, not silently forgotten


@pytest.mark.anyio
async def test_agreed_deal_waiting_for_approval_survives_restart(tmp_path):
    s = settings(tmp_path, guard_approval_over=6)
    seed(s, "d1", "agreed", price=7)
    buyer, bal = await restart(s, FakeSeller(), {"released", "refunded", "error"}, approve=True)
    types = [e.type for e in buyer.state.bus.history]
    assert types.index("needs_approval") < types.index("approved") < types.index("released")
    assert bal["seller"] == 7


def test_only_open_or_funded_deals_are_resumed(tmp_path):
    s = settings(tmp_path)
    ledger = Ledger(s.ledger_path)
    for status in ("negotiating", "agreed", "paying", "locked", "delivered",
                   "blocked", "walked", "released", "refunded", "error"):
        ledger.create_deal(status, "t-1", TASK, s.seller_url)
        ledger.update(status, status=status)
    ledger.create_deal("error-funded", "t-1", TASK, s.seller_url)
    ledger.update("error-funded", status="error", escrow_ref="SIM-x")
    assert {d["deal_id"] for d in ledger.unfinished()} == {"agreed", "paying", "locked", "delivered", "error-funded"}


def test_old_ledger_gets_start_json_column(tmp_path):
    path = tmp_path / "old.db"
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE deals (deal_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, task_json TEXT NOT NULL, "
               "seller_url TEXT NOT NULL, status TEXT NOT NULL, price REAL, approved INTEGER NOT NULL DEFAULT 0, "
               "job_id TEXT, escrow_ref TEXT, updated REAL NOT NULL)")
    db.execute("INSERT INTO deals (deal_id, task_id, task_json, seller_url, status, updated) "
               "VALUES ('d1', 't-1', '{}', 'http://seller', 'locked', 0)")
    db.commit()
    db.close()
    ledger = Ledger(str(path))
    assert ledger.get("d1")["start_json"] is None
    Ledger(str(path))  # second open: column already there, no error


def test_simulated_wallet_tops_up_when_low(tmp_path, caplog):
    ledger = Ledger(str(tmp_path / "buyer.db"))
    SimulatedPayments(ledger)
    ledger.db.execute("UPDATE sim_wallets SET balance = 5 WHERE name = 'buyer'")
    with caplog.at_level("WARNING"):
        SimulatedPayments(ledger)
    assert asyncio.run(SimulatedPayments(ledger).balances())["buyer"] == 100
    assert "[SIMULATED] top-up" in caplog.text
    ledger.db.execute("UPDATE sim_wallets SET balance = 50 WHERE name = 'buyer'")
    assert asyncio.run(SimulatedPayments(ledger).balances())["buyer"] == 50  # healthy wallet untouched


@pytest.mark.anyio
@pytest.mark.parametrize("failures,calls,final_state", [(2, 3, "ResultSubmitted"), (99, 3, "FundsLocked")])
async def test_seller_retries_submit_result_and_keeps_completed(tmp_path, monkeypatch, failures, calls,
                                                                final_state):
    from tests.fake_masumi import create_fake_masumi

    real, n = MasumiClient.submit_result, {"calls": 0}

    async def flaky(self, *a, **kw):
        n["calls"] += 1
        if n["calls"] <= failures:
            raise httpx.ConnectError("masumi down")
        return await real(self, *a, **kw)

    monkeypatch.setattr(MasumiClient, "submit_result", flaky)
    s = masumi_settings(tmp_path)
    fake = create_fake_masumi()
    masumi_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=fake))
    seller_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_seller(s, masumi_http=masumi_http)),
                                    base_url="http://seller")
    buyer = create_buyer(s, http=seller_http, masumi_http=masumi_http)
    async with buyer.router.lifespan_context(buyer):
        await buyer.state.orch.create_task(TaskCreate())
        for _ in range(500):  # wait until the seller is done retrying
            if n["calls"] >= calls and {"released", "refunded", "error"} & {e.type for e in buyer.state.bus.history}:
                break
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)
        (purchase,) = fake.state.purchases.values()
        job_id = buyer.state.ledger.all_deals()[0]["job_id"]
        job = (await seller_http.get("/status", params={"job_id": job_id})).json()
    assert n["calls"] == calls
    assert purchase["onChainState"] == final_state
    assert job["status"] == "completed"  # a failed submit never un-delivers the work
    await masumi_http.aclose()
    await seller_http.aclose()
