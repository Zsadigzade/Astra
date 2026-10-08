"""Runner ownership and crash recovery must not disturb parallel sessions or lose payments."""

import socket
import subprocess

import httpx
import pytest

from app.buyer.ledger import Ledger
from app.buyer.payments import SimulatedPayments
from app.core.config import Settings
from scripts import up


def seed(path, status="released", *, simulated=True, escrow_status="released"):
    ledger = Ledger(str(path))
    ledger.create_deal("d1", "t1", "{}", "seller")
    ledger.update("d1", status=status, escrow_ref="SIM-d1" if simulated else "chain-reference")
    if simulated:
        SimulatedPayments(ledger)
        ledger.db.execute("INSERT INTO sim_escrows VALUES (?,?,?,?,?)",
                          ("d1", 7, "seller", escrow_status, "SIM-d1"))
    ledger.append_event(1, {"simulated": simulated})
    ledger.db.close()


def test_reset_archives_configured_relative_ledger_and_preserves_default(tmp_path, monkeypatch):
    monkeypatch.setattr(up, "ROOT", tmp_path)
    default = tmp_path / "data" / "buyer.db"
    custom = tmp_path / "data" / "rehearsal.db"
    seed(default)
    seed(custom)
    original, untouched = custom.read_bytes(), default.read_bytes()
    backup = up.reset_ledger(Settings(ledger_path="data/rehearsal.db"))
    assert not custom.exists()
    assert backup.parent == custom.parent
    assert backup.read_bytes() == original
    assert default.read_bytes() == untouched


@pytest.mark.parametrize("status", ["negotiating", "agreed", "paying", "locked", "delivered", "error", "unknown"])
def test_reset_preserves_unfinished_deals(tmp_path, status):
    path = tmp_path / "buyer.db"
    seed(path, status)
    original = path.read_bytes()
    with pytest.raises(RuntimeError, match="unfinished"):
        up.reset_ledger(Settings(ledger_path=str(path)))
    assert path.read_bytes() == original
    assert not list(tmp_path.glob("*.bak"))


def test_reset_preserves_locked_escrow_even_if_deal_marked_complete(tmp_path):
    path = tmp_path / "buyer.db"
    seed(path, escrow_status="locked")
    with pytest.raises(RuntimeError, match="holds escrow"):
        up.reset_ledger(Settings(ledger_path=str(path)))
    assert path.exists()


@pytest.mark.parametrize("mode", ["masumi", "simulated"])
def test_reset_cannot_erase_real_ledger_after_mode_switch(tmp_path, mode):
    path = tmp_path / "buyer.db"
    seed(path, simulated=False)
    with pytest.raises(RuntimeError):
        up.reset_ledger(Settings(ledger_path=str(path), payments_mode=mode))
    assert path.exists()


def test_reset_rejects_mixed_payment_history(tmp_path):
    path = tmp_path / "buyer.db"
    seed(path)
    ledger = Ledger(str(path))
    ledger.append_event(2, {"simulated": False})
    ledger.db.close()
    with pytest.raises(RuntimeError, match="conflicting payment modes"):
        up.reset_ledger(Settings(ledger_path=str(path)))
    assert path.exists()


def test_reset_preserves_empty_masumi_bound_ledger(tmp_path):
    path = tmp_path / "buyer.db"
    ledger = Ledger(str(path))
    ledger.bind_payment_mode("masumi")
    ledger.db.close()
    with pytest.raises(RuntimeError, match="real payments"):
        up.reset_ledger(Settings(ledger_path=str(path), payments_mode="simulated"))
    assert path.exists()


def test_reset_preserves_real_start_response_in_mixed_ledger(tmp_path):
    path = tmp_path / "buyer.db"
    seed(path)
    ledger = Ledger(str(path))
    ledger.update("d1", start_json='{"blockchainIdentifier": "real-payment"}')
    ledger.db.close()
    with pytest.raises(RuntimeError, match="conflicting payment modes"):
        up.reset_ledger(Settings(ledger_path=str(path)))
    assert path.exists()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_reset_does_not_separate_sqlite_sidecars(tmp_path, suffix):
    path = tmp_path / "buyer.db"
    seed(path)
    sidecar = tmp_path / (path.name + suffix)
    sidecar.write_bytes(b"pending data")
    with pytest.raises(RuntimeError, match="sidecar"):
        up.reset_ledger(Settings(ledger_path=str(path)))
    assert path.exists() and sidecar.read_bytes() == b"pending data"


def test_reset_rejects_corrupt_file(tmp_path):
    path = tmp_path / "buyer.db"
    path.write_bytes(b"not sqlite")
    with pytest.raises(RuntimeError, match="safely inspected"):
        up.reset_ledger(Settings(ledger_path=str(path)))
    assert path.read_bytes() == b"not sqlite"


def test_reset_missing_or_memory_ledger_is_noop(tmp_path):
    assert up.reset_ledger(Settings(ledger_path=str(tmp_path / "missing.db"))) is None
    assert up.reset_ledger(Settings(ledger_path=":memory:")) is None
    assert list(tmp_path.iterdir()) == []


def test_busy_port_aborts_before_reset_or_spawning(tmp_path, monkeypatch, capsys):
    path = tmp_path / "buyer.db"
    seed(path)
    original = path.read_bytes()
    monkeypatch.setattr(up, "get_settings", lambda: Settings(ledger_path=str(path)))
    monkeypatch.setattr(up, "start", lambda *a: pytest.fail("must not launch services"))
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        port = occupied.getsockname()[1]
        monkeypatch.setattr(up, "SERVICES", {"seller": ("unused", port)})
        assert up.main(["--reset"]) == 1
    assert path.read_bytes() == original
    assert "existing session" in capsys.readouterr().out


class Process:
    def __init__(self, code=None):
        self.returncode = code
        self.terminated = False
        self.waited = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def wait(self, timeout):
        self.waited = True
        return self.returncode


def test_health_from_other_server_cannot_hide_dead_child(monkeypatch):
    monkeypatch.setattr(up.httpx, "get", lambda *a, **kw: pytest.fail("child already exited"))
    assert up.wait_healthy(8000, Process(1)) is False


def test_child_exiting_during_health_response_is_not_ready(monkeypatch):
    process = Process()

    def health(*a, **kw):
        process.returncode = 1
        return httpx.Response(200)

    monkeypatch.setattr(up.httpx, "get", health)
    assert up.wait_healthy(8000, process) is False


def test_partial_launch_failure_cleans_up_only_owned_child(monkeypatch):
    seller = Process()
    monkeypatch.setattr(up, "check_ports", lambda: None)

    def launch(name, env):
        if name == "buyer":
            raise OSError("cannot launch")
        return seller

    monkeypatch.setattr(up, "start", launch)
    assert up.main([]) == 1
    assert seller.terminated and seller.waited


@pytest.mark.parametrize("staged,restart_healthy", [(False, True), (True, True), (True, False)])
def test_recovery_is_bounded_and_clears_dotenv_crash_flag(monkeypatch, capsys, staged, restart_healthy):
    monkeypatch.setenv("CRASH_AFTER_LOCK", "1" if staged else "0")
    monkeypatch.setattr(up, "SERVICES", {"seller": ("unused", 18001), "buyer": ("unused", 18000)})
    monkeypatch.setattr(up, "check_ports", lambda: None)
    spawned = []

    def launch(name, env):
        process = Process()
        spawned.append((name, env, process))
        return process

    def sleep(seconds):
        if seconds == 0.5:
            spawned[-1][2].returncode = 1

    monkeypatch.setattr(up, "start", launch)
    monkeypatch.setattr(up.time, "sleep", sleep)
    checked_ports = []

    def healthy(port, process):
        checked_ports.append(port)
        return len(spawned) < 3 or restart_healthy

    def health(url, **kwargs):
        assert url == "http://127.0.0.1:18000/health"
        return httpx.Response(200, json={
            "payments_mode": "simulated", "llm_mode": "mock", "tts_mode": "off"})

    monkeypatch.setattr(up, "wait_healthy", healthy)
    monkeypatch.setattr(up.httpx, "get", health)
    assert up.main([]) == 1
    assert [name for name, _, _ in spawned] == (["seller", "buyer", "buyer"] if staged else ["seller", "buyer"])
    assert spawned[0][2].terminated  # own seller is cleaned up when the runner exits
    assert checked_ports == ([18001, 18000, 18000] if staged else [18001, 18000])
    if staged:
        assert spawned[1][1]["CRASH_AFTER_LOCK"] == "1"
        assert spawned[2][1]["CRASH_AFTER_LOCK"] == "0"
    if not restart_healthy:
        output = capsys.readouterr().out
        assert "restart failed" in output and "buyer back" not in output


def test_cleanup_waits_after_forced_kill(monkeypatch):
    class StuckProcess(Process):
        def wait(self, timeout):
            if self.returncode != -9:
                raise subprocess.TimeoutExpired("owned child", timeout)
            self.waited = True

        def kill(self):
            self.returncode = -9

    seller = StuckProcess()
    monkeypatch.setattr(up, "check_ports", lambda: None)
    monkeypatch.setattr(up, "start", lambda name, env: seller if name == "seller" else Process(1))
    monkeypatch.setattr(up, "wait_healthy", lambda *a: False)
    assert up.main([]) == 1
    assert seller.waited and seller.returncode == -9
