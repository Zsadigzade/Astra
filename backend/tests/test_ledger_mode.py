"""Payment mode cannot change across restarts or mislabel legacy payment history."""

import json
import sqlite3

import pytest

from app.buyer.ledger import Ledger, LedgerSafetyError, payment_mode
from app.buyer.payments import MasumiPayments, SimulatedPayments, make_payments
from app.core.config import Settings


@pytest.mark.parametrize("mode,other", [("simulated", "masumi"), ("masumi", "simulated")])
def test_mode_binding_survives_restart_even_without_deals(tmp_path, mode, other):
    path = str(tmp_path / "buyer.db")
    ledger = Ledger(path)
    ledger.bind_payment_mode(mode)
    ledger.db.close()
    restarted = Ledger(path)
    restarted.bind_payment_mode(mode)
    with pytest.raises(LedgerSafetyError, match="separate LEDGER_PATH"):
        restarted.bind_payment_mode(other)
    assert payment_mode(restarted.db) == mode
    restarted.db.close()


def test_simulated_adapter_refuses_real_ledger_before_creating_wallets():
    ledger = Ledger(":memory:")
    ledger.bind_payment_mode("masumi")
    with pytest.raises(LedgerSafetyError):
        SimulatedPayments(ledger)
    tables = {r[0] for r in ledger.db.execute("SELECT name FROM sqlite_master")}
    assert "sim_wallets" not in tables
    assert "sim_escrows" not in tables


def test_real_adapter_refuses_simulated_ledger_before_creating_client(monkeypatch):
    ledger = Ledger(":memory:")
    SimulatedPayments(ledger)

    def forbidden(*args, **kwargs):
        pytest.fail("Masumi client constructed before rejecting a simulated ledger")

    monkeypatch.setattr("app.buyer.payments.MasumiClient", forbidden)
    with pytest.raises(LedgerSafetyError):
        MasumiPayments(Settings(payments_mode="masumi"), ledger)
    assert ledger.db.execute("SELECT balance FROM sim_wallets WHERE name='buyer'").fetchone()[0] == 1000


@pytest.mark.parametrize("evidence,mode", [
    ("wallets", "simulated"), ("escrows", "simulated"),
    ("sim_ref", "simulated"), ("real_ref", "masumi"),
    ("sim_start", "simulated"), ("real_start", "masumi"),
    ("sim_event", "simulated"), ("real_event", "masumi"),
])
def test_legacy_mode_inferred_without_rewriting_history(evidence, mode):
    ledger = Ledger(":memory:")
    ledger.create_deal("d1", "t1", "{}", "seller")
    if evidence == "wallets":
        ledger.db.execute("CREATE TABLE sim_wallets (name TEXT, balance REAL)")
    elif evidence == "escrows":
        ledger.db.execute("CREATE TABLE sim_escrows (deal_id TEXT)")
    elif evidence.endswith("ref"):
        ledger.update("d1", status="released", escrow_ref="SIM-d1" if mode == "simulated" else "chain-id")
    elif evidence.endswith("start"):
        ledger.update("d1", status="paying", start_json=json.dumps({
            "job_id": "j1", "blockchainIdentifier": "chain-id" if mode == "masumi" else None,
        }))
    else:
        ledger.append_event(1, {"simulated": mode == "simulated"})
    before = ledger.get("d1")
    events = ledger.load_events()
    with pytest.raises(LedgerSafetyError):
        ledger.bind_payment_mode("masumi" if mode == "simulated" else "simulated")
    ledger.bind_payment_mode(mode)
    assert ledger.get("d1") == before
    assert ledger.load_events() == events
    assert payment_mode(ledger.db) == mode


@pytest.mark.parametrize("mode", ["simulated", "masumi"])
def test_preexisting_mixed_ledger_rejected_for_both_modes(mode):
    ledger = Ledger(":memory:")
    ledger.db.execute("CREATE TABLE sim_wallets (name TEXT, balance REAL)")
    ledger.create_deal("d1", "t1", "{}", "seller")
    ledger.update("d1", escrow_ref="chain-id")
    with pytest.raises(LedgerSafetyError, match="conflicting"):
        ledger.bind_payment_mode(mode)
    assert ledger.get("d1")["escrow_ref"] == "chain-id"


def test_conflicting_history_rejected_even_with_existing_binding():
    ledger = Ledger(":memory:")
    ledger.bind_payment_mode("simulated")
    ledger.append_event(1, {"simulated": False})
    with pytest.raises(LedgerSafetyError, match="conflicting"):
        ledger.bind_payment_mode("simulated")


def test_legacy_payment_intent_without_mode_evidence_rejected():
    ledger = Ledger(":memory:")
    ledger.create_deal("d1", "t1", "{}", "seller")
    ledger.update("d1", status="paying", price=70)
    with pytest.raises(LedgerSafetyError, match="unknown mode"):
        ledger.bind_payment_mode("masumi")


@pytest.mark.parametrize("body", ["not json", "null", "[]"])
def test_corrupt_legacy_history_is_not_assigned_a_mode(body):
    ledger = Ledger(":memory:")
    ledger.db.execute("INSERT INTO events VALUES (1, ?)", (body,))
    with pytest.raises(LedgerSafetyError, match="stored events"):
        ledger.bind_payment_mode("simulated")


def test_old_schema_without_start_json_can_be_inspected_read_only(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE deals (escrow_ref TEXT, status TEXT)")
        db.execute("INSERT INTO deals VALUES ('SIM-old', 'released')")
        db.execute("CREATE TABLE events (body TEXT)")
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        assert payment_mode(db) == "simulated"
    finally:
        db.close()


def test_unknown_payment_mode_does_not_silently_construct_simulator():
    ledger = Ledger(":memory:")
    with pytest.raises(ValueError, match="PAYMENTS_MODE"):
        make_payments(Settings(payments_mode="typo"), ledger)
    assert payment_mode(ledger.db) is None


def test_fresh_ledger_binds_usd_and_reopens(tmp_path):
    path = str(tmp_path / "b.db")
    ledger = Ledger(path)
    ledger.bind_currency()
    SimulatedPayments(ledger)
    ledger.create_deal("d1", "t1", "{}", "http://s")
    ledger.update("d1", status="released", price=70, escrow_ref="SIM-d1")
    ledger.db.close()
    again = Ledger(path)
    again.bind_currency()  # its own USD record: reopening is fine
    assert again.db.execute("SELECT value FROM ledger_metadata WHERE key='currency'").fetchone()[0] == "USD"


@pytest.mark.parametrize("legacy", ["deal", "wallet"])
def test_legacy_tada_ledger_is_refused(tmp_path, legacy):
    ledger = Ledger(str(tmp_path / "b.db"))
    if legacy == "deal":
        ledger.create_deal("d1", "t1", "{}", "http://s")
        ledger.update("d1", status="released", price=7, escrow_ref="SIM-d1")
    else:
        SimulatedPayments(ledger)  # an old simulated wallet holding tADA
    with pytest.raises(LedgerSafetyError, match="tADA"):
        ledger.bind_currency()


def test_buyer_app_refuses_a_legacy_tada_ledger(tmp_path):
    from app.buyer.app import create_app
    path = str(tmp_path / "old.db")
    SimulatedPayments(Ledger(path))
    with pytest.raises(LedgerSafetyError, match="LEDGER_PATH"):
        create_app(Settings(ledger_path=path, audio_dir=str(tmp_path / "audio")))


def test_default_stores_are_fresh_usd_files():
    import os
    from unittest import mock
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("LEDGER_PATH", None)
        os.environ.pop("SELLER_STORE_PATH", None)
        s = Settings()
    assert s.ledger_path.endswith("buyer-usd.db") and s.seller_store_path.endswith("seller-usd.db")


def test_masumi_payments_are_disabled_for_both_services(tmp_path):
    from app.seller.app import create_app as create_seller
    s = Settings(payments_mode="masumi", ledger_path=str(tmp_path / "b.db"), seller_store_path=":memory:")
    with pytest.raises(ValueError, match="Masumi payments are disabled"):
        make_payments(s, Ledger(s.ledger_path))
    with pytest.raises(ValueError, match="Masumi payments are disabled"):
        create_seller(s)


def test_seller_blank_store_path_uses_the_usd_default(tmp_path, monkeypatch):
    import app.seller.app as seller_app
    opened = []
    monkeypatch.setattr(seller_app, "SellerStore", lambda path: opened.append(path) or (_ for _ in ()).throw(RuntimeError("stop")))
    with pytest.raises(RuntimeError, match="stop"):
        seller_app.create_app(Settings(seller_store_path=""))
    assert opened and opened[0].endswith("seller-usd.db")


def test_masumi_seller_is_refused_before_opening_its_store(tmp_path, monkeypatch):
    import app.seller.app as seller_app
    opened = []
    monkeypatch.setattr(seller_app, "SellerStore", lambda path: opened.append(path))
    with pytest.raises(ValueError, match="Masumi payments are disabled"):
        seller_app.create_app(Settings(payments_mode="masumi", seller_store_path=str(tmp_path / "s.db")))
    assert opened == []
