"""Subscription CLI isolation, failure, and cancellation tests; no live requests."""

import asyncio
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

import app.buyer.codex_runtime as runtime
from app.core.config import Settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


def settings(**kwargs):
    return Settings(llm_mode="codex", codex_command="codex", codex_model="", **kwargs)


class FakeProcess:
    pid = 12345

    def __init__(self, args, *, result='{"action":"counter","price":5,"message":"Five."}', code=0, hang=False):
        self.args, self.result, self.code, self.hang = args, result, code, hang
        self.returncode = None
        self.input = None

    async def communicate(self, input):
        self.input = input
        if self.hang:
            await asyncio.Future()
        if self.result is not None:
            Path(self.args[self.args.index("--output-last-message") + 1]).write_text(self.result, encoding="utf-8")
        self.returncode = self.code
        return None, None


def fake_spawn(monkeypatch, **options):
    calls = []

    async def spawn(*args, **kwargs):
        process = FakeProcess(args, **options)
        calls.append((args, kwargs, process))
        return process

    monkeypatch.setattr(runtime, "_command", lambda value: ["trusted-codex"])
    monkeypatch.setattr(runtime.asyncio, "create_subprocess_exec", spawn)
    return calls


@pytest.mark.anyio
async def test_subprocess_isolated_and_only_structured_move_returned(monkeypatch):
    calls = fake_spawn(monkeypatch)
    for key in ("OPENAI_API_KEY", "APIFY_TOKEN", "ELEVENLABS_API_KEY", "MASUMI_API_KEY", "NODE_OPTIONS", "OPENAI_BASE_URL"):
        monkeypatch.setenv(key, "private-value")
    monkeypatch.setenv("CODEX_HOME", "native-auth-directory")
    schema = {"type": "object"}
    result = await runtime.run_codex("seller dialogue", schema, settings())
    assert result["price"] == 5
    args, options, process = calls[0]
    assert args[0] == "trusted-codex"
    assert args[-1] == "-"
    assert "--model" not in args  # honor the CLI's subscription default
    assert "--ignore-user-config" in args and "--ignore-rules" in args
    assert "--ephemeral" in args and "--no-daemon" in args
    assert args[args.index("--sandbox") + 1] == "read-only"
    assert 'forced_login_method="chatgpt"' in args
    assert 'approval_policy="never"' in args
    assert "features.shell_tool=false" in args
    assert "features.apps=false" in args and "features.plugins=false" in args
    assert 'web_search="disabled"' in args
    assert options["env"]["CODEX_HOME"] == "native-auth-directory"
    assert "private-value" not in options["env"].values()
    assert options["stdout"] == options["stderr"] == asyncio.subprocess.DEVNULL
    assert process.input == b"seller dialogue"
    assert not Path(options["cwd"]).exists()  # temp schema/output are removed
    assert "shell" not in options


def test_model_override_is_one_argument(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "_command", lambda value: ["codex"])
    config = Settings(llm_mode="codex", codex_model="configured model; not shell code")
    args = runtime._arguments(config, tmp_path / "schema.json", tmp_path / "out.json")
    assert args[args.index("--model") + 1] == config.codex_model


@pytest.mark.anyio
@pytest.mark.parametrize("result,code", [(None, 0), ("[]", 0), ("{}", 1), ("x" * 64_001, 0)],
                         ids=["missing", "array", "exit-failure", "too-large"])
async def test_unusable_child_output_is_safe_failure(monkeypatch, result, code):
    calls = fake_spawn(monkeypatch, result=result, code=code)

    async def terminate(process):
        pass

    monkeypatch.setattr(runtime, "_terminate", terminate)
    with pytest.raises(runtime.CodexRuntimeError):
        await runtime.run_codex("seller", {}, settings())
    assert not Path(calls[0][1]["cwd"]).exists()


@pytest.mark.anyio
async def test_invalid_json_never_returns_success(monkeypatch):
    fake_spawn(monkeypatch, result="not JSON")

    async def terminate(process):
        pass

    monkeypatch.setattr(runtime, "_terminate", terminate)
    with pytest.raises(json.JSONDecodeError):
        await runtime.run_codex("seller", {}, settings())


@pytest.mark.anyio
async def test_timeout_terminates_before_temp_cleanup(monkeypatch):
    calls = fake_spawn(monkeypatch, hang=True)
    terminated = []

    async def terminate(process):
        assert Path(calls[0][1]["cwd"]).is_dir()
        terminated.append(process)

    monkeypatch.setattr(runtime, "_terminate", terminate)
    with pytest.raises(TimeoutError):
        await runtime.run_codex("seller", {}, settings(codex_timeout_seconds=0.01))
    assert terminated == [calls[0][2]]
    assert not Path(calls[0][1]["cwd"]).exists()


@pytest.mark.anyio
async def test_cancellation_terminates_child_and_propagates(monkeypatch):
    calls = fake_spawn(monkeypatch, hang=True)
    terminated = []

    async def terminate(process):
        terminated.append(process)

    monkeypatch.setattr(runtime, "_terminate", terminate)
    task = asyncio.create_task(runtime.run_codex("seller", {}, settings()))
    while not calls or calls[0][2].input is None:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert terminated == [calls[0][2]]


@pytest.mark.anyio
async def test_cancellation_during_spawn_does_not_orphan_process(monkeypatch):
    started, finish_spawn = asyncio.Event(), asyncio.Event()
    terminated = []
    process = SimpleNamespace(pid=12345)

    async def spawn(*args, **kwargs):
        started.set()
        await finish_spawn.wait()
        return process

    async def terminate(process):
        terminated.append(process)

    monkeypatch.setattr(runtime, "_command", lambda value: ["codex"])
    monkeypatch.setattr(runtime.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(runtime, "_terminate", terminate)
    task = asyncio.create_task(runtime.run_codex("seller", {}, settings()))
    await started.wait()
    task.cancel()
    await asyncio.sleep(0)
    finish_spawn.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert terminated == [process]


@pytest.mark.anyio
@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
async def test_invalid_timeout_rejected(timeout):
    with pytest.raises(ValueError, match="TIMEOUT"):
        await runtime.run_codex("seller", {}, settings(codex_timeout_seconds=timeout))


def test_missing_command_fails_without_shell(monkeypatch):
    monkeypatch.setattr(runtime.shutil, "which", lambda command: None)
    with pytest.raises(runtime.CodexRuntimeError, match="not found"):
        runtime._command("codex && injected-command")


@pytest.mark.skipif(os.name != "nt", reason="Windows npm shim")
def test_windows_npm_shim_uses_node_without_shell(monkeypatch, tmp_path):
    shim = tmp_path / "codex.cmd"
    shim.touch()
    entry = tmp_path / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    entry.parent.mkdir(parents=True)
    entry.touch()
    monkeypatch.setattr(runtime.shutil, "which", lambda name: str(shim) if name == "codex" else "node.exe")
    assert runtime._command("codex") == ["node.exe", str(entry)]


@pytest.mark.anyio
async def test_real_child_structured_output_and_cleanup(monkeypatch, tmp_path):
    # Exercise Windows/POSIX asyncio subprocess pipes and cleanup without Codex.
    script = tmp_path / "fake_codex.py"
    script.write_text("""import json, pathlib, sys
args = sys.argv
assert sys.stdin.read() == 'negotiation only'
out = pathlib.Path(args[args.index('--output-last-message') + 1])
out.write_text(json.dumps({'message': 'Five.', 'price': 5, 'action': 'counter'}))
""")
    monkeypatch.setattr(runtime, "_command", lambda command: [sys.executable, str(script)])
    result = await runtime.run_codex("negotiation only", {}, settings())
    assert result["action"] == "counter"


@pytest.mark.skipif(os.name != "nt", reason="Windows process tree cleanup")
@pytest.mark.anyio
async def test_real_windows_timeout_kills_child_tree(monkeypatch, tmp_path):
    import ctypes

    script, ids = tmp_path / "hang.py", tmp_path / "pids.json"
    script.write_text("""import json, os, pathlib, subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                         creationflags=subprocess.CREATE_NO_WINDOW)
pathlib.Path(sys.argv[1]).write_text(json.dumps([os.getpid(), child.pid]))
time.sleep(60)
""")
    monkeypatch.setattr(runtime, "_command", lambda command: [sys.executable, str(script), str(ids)])
    with pytest.raises(TimeoutError):
        await runtime.run_codex("seller", {}, settings(codex_timeout_seconds=1))
    assert ids.is_file(), "test child did not initialize within the deadline"
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    for pid in json.loads(ids.read_text()):
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if handle:
            try:
                assert kernel.WaitForSingleObject(handle, 1000) == 0, f"child {pid} survived timeout"
            finally:
                kernel.CloseHandle(handle)
