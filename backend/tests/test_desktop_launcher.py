"""Repository launcher safety and result reporting; never call external providers."""
import ctypes
from ctypes import wintypes
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("astra_desktop_launcher", ROOT / "scripts/desktop/launcher.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "Astra repository with spaces"
    (root / "backend").mkdir(parents=True)
    (root / "frontend").mkdir()
    (root / "scripts").mkdir()
    (root / "backend/pyproject.toml").write_text("[project]\nname='test'\n")
    (root / "scripts/dev.mjs").write_text("// fixture\n")
    return root


def test_explicit_repository_must_exist_and_cannot_fall_back_to_parent(repo):
    assert launcher.find_repo(repo) == repo.resolve()
    with pytest.raises(ValueError):
        launcher.find_repo(repo / "missing")
    with pytest.raises(ValueError):
        launcher.find_repo(repo / "backend/pyproject.toml")


def test_sample_profile_overrides_live_environment_without_mutating_it(repo, monkeypatch):
    original = {"PAYMENTS_MODE": "masumi", "LLM_MODE": "codex", "SELLER_LLM_MODE": "codex",
                "APIFY_MODE": "apify", "TTS_MODE": "elevenlabs", "CRASH_AFTER_LOCK": "1",
                "LEDGER_PATH": "existing-live.db", "AUDIO_DIR": "existing-audio"}
    for key, value in original.items():
        monkeypatch.setenv(key, value)
    artifact = repo / "backend/data/new run"
    env = launcher.environment(repo, artifact, "sample")
    assert env["PAYMENTS_MODE"] == "simulated"
    assert env["LLM_MODE"] == env["SELLER_LLM_MODE"] == "mock"
    assert env["APIFY_MODE"] == "sample" and env["TTS_MODE"] == "off"
    assert env["CRASH_AFTER_LOCK"] == "0"
    assert Path(env["LEDGER_PATH"]) == artifact / "buyer.db"
    assert Path(env["AUDIO_DIR"]) == artifact / "audio"
    assert all(os.environ[key] == value for key, value in original.items())


def test_configured_profile_preserves_provider_modes_but_isolates_payments(repo, monkeypatch):
    for key, value in {"PAYMENTS_MODE": "masumi", "LLM_MODE": "codex", "APIFY_MODE": "cached",
                       "TTS_MODE": "elevenlabs", "LEDGER_PATH": "funded.db"}.items():
        monkeypatch.setenv(key, value)
    artifact = repo / "backend/data/check"
    env = launcher.environment(repo, artifact, "configured")
    assert (env["LLM_MODE"], env["APIFY_MODE"], env["TTS_MODE"]) == ("codex", "cached", "elevenlabs")
    assert env["PAYMENTS_MODE"] == "simulated"
    assert Path(env["LEDGER_PATH"]) == artifact / "buyer.db"
    assert env["LEDGER_PATH"] != os.environ["LEDGER_PATH"]


@pytest.mark.parametrize("action,profile,allowed", [
    ("live-probe", "configured", False), ("rehearse", "configured", False),
    ("demo", "configured", False), ("recovery", "configured", False),
    ("live-probe", "sample", True), ("rehearse", "sample", True),
])
def test_live_actions_require_explicit_usage_and_configured_profile(repo, monkeypatch, action, profile, allowed):
    monkeypatch.setattr(launcher, "tool", lambda name: pytest.fail("Denied action must not start tools"))
    runner = launcher.Runner(repo, profile=profile, emit=lambda line: None, allow_live=allowed)
    assert runner.run(action) == 1
    report = json.loads((runner.artifact / "report.json").read_text())
    assert report["passed"] is False
    assert report["payments"] == "SIMULATED"
    assert report["results"] == []
    assert report["error"]


def test_smoke_failure_is_reported_as_failure(repo, monkeypatch):
    monkeypatch.setattr(launcher, "tool", lambda name: name)
    runner = launcher.Runner(repo, emit=lambda line: None)
    def fail_demo(*args, **kwargs):
        raise RuntimeError("Sample balance conservation failed.")
    monkeypatch.setattr(runner, "demo", fail_demo)
    assert runner.run("smoke") == 1
    report = json.loads((runner.artifact / "report.json").read_text())
    assert report["passed"] is False
    assert "balance conservation" in report["error"]


def test_failed_development_check_is_not_hidden_by_later_success(repo, monkeypatch):
    monkeypatch.setattr(launcher, "tool", lambda name: name)
    monkeypatch.setattr(launcher, "npm_command", lambda *args: ["npm", *args])
    runner = launcher.Runner(repo, emit=lambda line: None)
    outcomes = iter((False, True, True))
    seen = []
    def command(label, cmd, cwd, env):
        seen.append(label)
        return next(outcomes)
    monkeypatch.setattr(runner, "command", command)
    assert runner.run("tests") == 1
    assert len(seen) == 3
    assert runner.report["passed"] is False


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Objects")
def test_windows_job_gate_stops_descendants_and_preserves_unrelated_process(tmp_path):
    """Real OS test: no child before attachment, kill descendants after gate exits."""
    pid_file = tmp_path / "grandchild.pid"
    child_file = tmp_path / "child.pid"
    grandchild = "import time; time.sleep(60)"
    child_code = ("import subprocess,sys,pathlib,os; "
                  f"p=subprocess.Popen([sys.executable,'-c',{grandchild!r}]); "
                  f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid)); "
                  f"pathlib.Path({str(child_file)!r}).write_text(str(os.getpid()))")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    def running(pid):
        handle = api.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return False
        try:
            return api.WaitForSingleObject(handle, 0) == 258  # WAIT_TIMEOUT
        finally:
            api.CloseHandle(handle)
    job = launcher.WindowsJob()
    outsider = subprocess.Popen([sys.executable, "-c", grandchild], creationflags=subprocess.CREATE_NO_WINDOW)
    gate = subprocess.Popen([sys.executable, str(ROOT / "scripts/desktop/process_gate.py"),
                             sys.executable, "-c", child_code], stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW | 0x4)  # CREATE_SUSPENDED
    try:
        time.sleep(.1)
        assert not pid_file.exists(), "Gate must not start workload before ownership attaches"
        job.attach(gate)
        gate.stdin.write(b"G\n")
        gate.stdin.close()
        gate.wait(timeout=10)
        assert gate.returncode == 0
        assert child_file.exists()
        grandchild_pid = int(pid_file.read_text())
        assert running(grandchild_pid)
        job.close()
        deadline = time.monotonic() + 5
        while running(grandchild_pid) and time.monotonic() < deadline:
            time.sleep(.02)
        assert not running(grandchild_pid), "Grandchild must die even when its parent and gate have exited"
        assert outsider.poll() is None, "Unrelated terminal processes must remain running"
    finally:
        job.close()
        if gate.poll() is None:
            gate.kill()
        gate.wait(timeout=10)
        outsider.terminate()
        outsider.wait(timeout=10)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Objects")
def test_runner_launch_owns_redirector_descendants_and_preserves_failure_code(tmp_path):
    """The repository venv Python redirector must not escape ownership at startup."""
    pid_file = tmp_path / "owned-grandchild.pid"
    child_code = ("import subprocess,sys,pathlib; "
                  "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                  f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid)); sys.exit(7)")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    runner = launcher.Runner(ROOT, emit=lambda line: None)
    job = launcher.WindowsJob()
    process = thread = handle = None
    try:
        process, thread = runner.launch([sys.executable, "-c", child_code], ROOT,
                                       launcher.environment(ROOT, runner.artifact, "sample"), job)
        assert process.wait(timeout=15) == 7
        assert pid_file.exists()
        handle = api.OpenProcess(0x100000, False, int(pid_file.read_text()))
        assert handle and api.WaitForSingleObject(handle, 0) == 258
        job.close()
        assert api.WaitForSingleObject(handle, 5000) == 0, "Runner left a descendant outside its Job Object"
    finally:
        job.close()
        if handle:
            api.CloseHandle(handle)
        if process:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
        if thread:
            thread.join(timeout=5)
        runner.log.close()
