"""Root Astra.exe starter: environment, port ownership and repository detection; no services are started."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("astra_desktop_start", ROOT / "scripts/desktop/start.py")
start = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "Astra with spaces"
    (root / "backend").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "backend/pyproject.toml").write_text("[project]\nname='test'\n")
    (root / "scripts/dev.mjs").write_text("// fixture\n")
    return root


def test_finds_repository_from_its_root_or_a_subfolder(repo):
    assert start.find_root([repo]) == repo.resolve()
    assert start.find_root([repo / "scripts"]) == repo.resolve()
    with pytest.raises(ValueError):
        start.find_root([repo.parent])


def test_dotenv_keys_reads_names_only(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nSTRICT_LIVE=1\nexport APIFY_MODE = apify\n  SELLER_LLM_MODE=codex # live\n"
                   "not a line\nEMPTY=\n", encoding="utf-8")
    assert start.dotenv_keys(env) == {"STRICT_LIVE", "APIFY_MODE", "SELLER_LLM_MODE", "EMPTY"}
    assert start.dotenv_keys(tmp_path / "missing.env") == set()


def test_terminal_overrides_of_dotenv_keys_are_dropped_without_mutating_the_source():
    inherited = {"SELLER_LLM_MODE": "mock", "APIFY_MODE": "sample", "PATH": "C:/bin",
                 "VIRTUAL_ENV": "C:/other/.venv", "NO_OPEN": "1"}
    env, dropped = start.clean_env(inherited, {"SELLER_LLM_MODE", "APIFY_MODE", "STRICT_LIVE"})
    assert env == {"PATH": "C:/bin", "NO_OPEN": "1"}
    assert dropped == ["APIFY_MODE", "SELLER_LLM_MODE"]  # names only, never values
    assert inherited["SELLER_LLM_MODE"] == "mock"


def test_netstat_listeners_for_requested_ports_only():
    text = """
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1200
  TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       28788
  TCP    127.0.0.1:8000         127.0.0.1:50000        ESTABLISHED     28788
  TCP    127.0.0.1:18001        0.0.0.0:0              LISTENING       77
  TCP    [::1]:5173             [::]:0                 LISTENING       18756
  UDP    0.0.0.0:8001           *:*                                    999
"""
    assert start.listeners(text, (8000, 8001, 5173)) == {8000: {28788}, 5173: {18756}}


@pytest.mark.parametrize("port,body,astra", [
    (8000, '{"ok":true,"payments_mode":"simulated","simulated":true}', True),
    (8001, '{"ok":true,"agent":"viktor","simulated":true}', True),
    (5173, "<html><head><title>Astra - The Haggle</title>", True),
    (8000, '{"ok":true}', False),
    (5173, "<title>Some other app</title>", False),
    (8001, None, False),  # nothing answered
])
def test_port_owner_is_astra_only_when_its_own_endpoint_answers(port, body, astra):
    assert start.is_astra(port, lambda url: body) is astra


@pytest.mark.parametrize("family,host", [("AF_INET", "127.0.0.1"), ("AF_INET6", "::1")])
def test_busy_ports_sees_ipv4_and_ipv6_listeners(family, host):
    import os
    import socket
    if os.name != "nt":
        pytest.skip("Windows netstat output")
    with socket.socket(getattr(socket, family), socket.SOCK_STREAM) as sock:  # Vite listens on [::1]
        sock.bind((host, 0))
        sock.listen()
        port = sock.getsockname()[1]
        assert start.busy_ports((port,)) == {port: {os.getpid()}}
