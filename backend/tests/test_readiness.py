import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.models import BoundedJobSpec, JobResult
from app.seller import apify
from scripts import readiness
from tests.test_apify import row


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings(tmp_path):
    return Settings(llm_mode="mock", seller_llm_mode="mock", apify_mode="sample",
                    tts_mode="off", apify_token="", elevenlabs_api_key="",
                    voice_max="", voice_viktor="", audio_dir=str(tmp_path / "audio"),
                    apify_cache_path=str(tmp_path / "cache.json"))


@pytest.fixture(autouse=True)
def local_only(monkeypatch):
    async def missing(settings):
        return False

    def forbidden(*args, **kwargs):
        pytest.fail("Default readiness must not contact providers or move money")

    monkeypatch.setattr(readiness, "codex_status", missing)
    monkeypatch.setattr(readiness.httpx, "AsyncClient", forbidden)
    monkeypatch.setattr(readiness.llm_check, "check_agents", forbidden)
    monkeypatch.setattr(readiness.voice_check, "check", forbidden)
    monkeypatch.setattr(apify, "scrape", forbidden)
    monkeypatch.setattr(apify, "recover_run", forbidden)


def cache(settings):
    job = BoundedJobSpec(count=2)
    result = JobResult(flats=apify.map_items([row(1), row(2)], job), source="apify",
                       actor_id=apify.ACTOR_ID, run_id="safe_run", dataset_id="safe_dataset",
                       fetched_at=datetime.now(timezone.utc).isoformat())
    apify.save_cache(job, result, settings)
    return job, result


@pytest.mark.anyio
async def test_sample_profile_needs_no_credentials_or_provider_work(settings, capsys):
    assert await readiness.check(settings, BoundedJobSpec()) == 0
    output = capsys.readouterr().out
    assert "SCRIPTED" in output and "SAMPLE" in output and "OFF" in output
    assert "live escrow and full E2E acceptance NOT verified" in output
    assert list(Path(settings.audio_dir).iterdir()) == []


@pytest.mark.anyio
async def test_cached_profile_reports_exact_provenance(settings, capsys):
    settings = replace(settings, apify_mode="cached")
    job, result = cache(settings)
    path = apify.cache_path(job, settings)
    before = path.read_bytes()
    assert await readiness.check(settings, job) == 0
    output = capsys.readouterr().out
    assert result.fetched_at in output and "run=safe_run; dataset=safe_dataset" in output
    assert "exact request match; CACHED APIFY; 2 records" in output
    assert path.read_bytes() == before
    assert await readiness.check(settings, BoundedJobSpec(count=1)) == 1
    assert "--run-id" in capsys.readouterr().out


@pytest.mark.anyio
async def test_readiness_obeys_cache_freshness_and_labels_override(settings, capsys):
    settings = replace(settings, apify_mode="cached", apify_cache_max_age_seconds=60,
                       apify_allow_stale_cache=False)
    job, result = cache(settings)
    timestamp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    apify.save_cache(job, result.model_copy(update={"fetched_at": timestamp}), settings)
    assert await readiness.check(settings, job) == 1
    assert "APIFY_CACHE_MAX_AGE_SECONDS" in capsys.readouterr().out
    assert await readiness.check(replace(settings, apify_allow_stale_cache=True), job) == 0
    output = capsys.readouterr().out
    assert timestamp in output and "STALE" in output and "override" in output


@pytest.mark.anyio
async def test_corrupt_cache_and_provider_values_never_leak(settings, capsys):
    secret = "private-secret-with-\n-control-characters"
    Path(settings.apify_cache_path).write_text(json.dumps({"token": secret}))
    settings = replace(settings, apify_mode="cached", codex_command=secret,
                       elevenlabs_api_key=secret, apify_token=secret)
    assert await readiness.check(settings, BoundedJobSpec()) == 1
    assert secret not in capsys.readouterr().out


@pytest.mark.anyio
@pytest.mark.parametrize("changes, expected", [
    ({"apify_mode": "cached"}, "APIFY_CACHE_PATH"),
    ({"apify_mode": "apify"}, "APIFY_TOKEN"),
    ({"apify_mode": "unknown-secret"}, "APIFY_MODE"),
    ({"llm_mode": "codex"}, "codex login"),
    ({"seller_llm_mode": "codex"}, "codex login"),
    ({"tts_mode": "elevenlabs"}, "VOICE_MAX"),
    ({"tts_mode": "unknown-secret"}, "TTS_MODE"),
])
async def test_missing_prerequisites_fail_actionably(settings, capsys, changes, expected):
    assert await readiness.check(replace(settings, **changes), BoundedJobSpec()) == 1
    output = capsys.readouterr().out
    assert expected in output and "unknown-secret" not in output


@pytest.mark.anyio
async def test_live_capability_is_configuration_only(settings, capsys):
    settings = replace(settings, apify_mode="apify", apify_token="private-secret")
    assert await readiness.check(settings, BoundedJobSpec()) == 0
    output = capsys.readouterr().out
    assert "live delivery UNTESTED" in output and "cached fallback unavailable" in output
    assert "private-secret" not in output


@pytest.mark.anyio
async def test_storage_failure_detected_even_with_voice_off(settings, tmp_path, capsys):
    path = tmp_path / "file"
    path.write_text("preserve me")
    assert await readiness.check(replace(settings, audio_dir=str(path)), BoundedJobSpec()) == 1
    assert "AUDIO_DIR" in capsys.readouterr().out
    assert path.read_text() == "preserve me"


@pytest.mark.anyio
async def test_synthesis_and_model_access_untested_by_default(settings, monkeypatch, capsys):
    async def signed_in(settings):
        return True
    monkeypatch.setattr(readiness, "codex_status", signed_in)
    settings = replace(settings, llm_mode="codex", tts_mode="elevenlabs",
                       elevenlabs_api_key="private-key", voice_max="private-max",
                       voice_viktor="private-viktor")
    assert await readiness.check(settings, BoundedJobSpec()) == 0
    output = capsys.readouterr().out
    assert "quota/model access untested" in output and "synthesis UNTESTED" in output
    assert "private-" not in output


@pytest.mark.anyio
@pytest.mark.parametrize("probe_fails", [False, True])
async def test_explicit_probe_checks_only_selected_agents_and_voice(settings, monkeypatch, capsys, probe_fails):
    calls = []

    async def signed_in(settings):
        return True

    async def agents(settings, agent):
        calls.append(agent)
        print("private-child-output")
        return int(probe_fails)

    async def voices(settings, client, synthesize):
        assert synthesize
        calls.append("voice")
        print("private-provider-output")
        return int(probe_fails)

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(readiness, "codex_status", signed_in)
    monkeypatch.setattr(readiness.llm_check, "check_agents", agents)
    monkeypatch.setattr(readiness.voice_check, "check", voices)
    monkeypatch.setattr(readiness.httpx, "AsyncClient", Client)
    settings = replace(settings, seller_llm_mode="codex", tts_mode="elevenlabs",
                       elevenlabs_api_key="key", voice_max="max", voice_viktor="viktor")
    assert await readiness.check(settings, BoundedJobSpec(), live_probe=True) == int(probe_fails)
    assert calls == ["viktor", "voice"]
    output = capsys.readouterr().out
    assert "private-" not in output and "live agent probe" in output and "live voice probe" in output


@pytest.mark.anyio
async def test_live_probe_with_disabled_modes_makes_no_provider_calls(settings):
    assert await readiness.check(settings, BoundedJobSpec(), live_probe=True) == 0


@pytest.mark.anyio
async def test_unsupported_real_data_district_fails(settings, capsys):
    assert await readiness.check(replace(settings, apify_mode="apify", apify_token="key"),
                                 BoundedJobSpec(district="Brno")) == 1
    assert "supported Prague district" in capsys.readouterr().out
    assert await readiness.check(settings, BoundedJobSpec(district="Praha 8")) == 0


def test_invalid_cli_configuration_does_not_print_secrets(monkeypatch, capsys):
    monkeypatch.setenv("APIFY_TIMEOUT_SECONDS", "private-secret")
    assert readiness.main([]) == 1
    assert "private-secret" not in capsys.readouterr().out


# Preserve the implementation reference before the autouse fixture replaces it.
real_codex_status = readiness.codex_status
real_timeout = asyncio.timeout


@pytest.mark.anyio
@pytest.mark.parametrize("output, code, expected", [
    (b"Logged in using ChatGPT\n", 0, True),
    (b"Logged in using an API key: private-key\n", 0, False),
    (b"Not logged in\n", 1, False),
    (b"Logged in using ChatGPT\n", 1, False),
    (b"x" * 5000, 0, False),
])
async def test_local_login_status_is_bounded_filtered_and_never_echoed(settings, monkeypatch, capsys, output, code, expected):
    calls = []
    reaped = []

    class Process:
        returncode = code
        stdout = asyncio.StreamReader()
        async def wait(self):
            return code

    process = Process()
    process.stdout.feed_data(output)
    process.stdout.feed_eof()

    async def spawn(*args, **kwargs):
        calls.append((args, kwargs))
        return process

    async def cleanup(spawn, child):
        reaped.append(child)

    monkeypatch.setenv("OPENAI_API_KEY", "private-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "private-key")
    monkeypatch.setattr(readiness, "_command", lambda command: ["codex-executable"])
    monkeypatch.setattr(readiness.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(readiness, "_cleanup", cleanup)
    assert await real_codex_status(settings) is expected
    assert calls[0][0] == ("codex-executable", "login", "status")
    assert "OPENAI_API_KEY" not in calls[0][1]["env"]
    assert "ELEVENLABS_API_KEY" not in calls[0][1]["env"]
    assert reaped == [process]
    assert "private-key" not in capsys.readouterr().out


@pytest.mark.anyio
@pytest.mark.parametrize("cancel", [False, True])
async def test_login_timeout_or_cancellation_reaps_owned_process(settings, monkeypatch, cancel):
    entered = asyncio.Event()
    reaped = []

    class Process:
        returncode = None
        stdout = asyncio.StreamReader()

    process = Process()

    async def spawn(*args, **kwargs):
        entered.set()
        return process

    async def cleanup(spawn, child):
        reaped.append(child if child is not None else await spawn)

    monkeypatch.setattr(readiness, "_command", lambda command: ["codex-executable"])
    monkeypatch.setattr(readiness.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(readiness, "_cleanup", cleanup)
    monkeypatch.setattr(readiness.asyncio, "timeout", lambda seconds: real_timeout(1 if cancel else 0.01))
    task = asyncio.create_task(real_codex_status(settings))
    await entered.wait()
    if cancel:
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else TimeoutError):
        await task
    assert reaped == [process]


@pytest.mark.anyio
@pytest.mark.parametrize("changes", [
    {"apify_mode": "apify", "apify_token": "key", "apify_timeout_seconds": float("nan")},
    {"apify_mode": "apify", "apify_token": "key", "apify_max_items": 1},
    {"tts_mode": "elevenlabs", "elevenlabs_api_key": "key", "voice_max": "same", "voice_viktor": "same"},
    {"tts_mode": "elevenlabs", "elevenlabs_api_key": "key", "voice_max": "max", "voice_viktor": "viktor", "tts_timeout_seconds": float("inf")},
])
async def test_invalid_provider_limits_fail_without_probe(settings, changes):
    assert await readiness.check(replace(settings, **changes), BoundedJobSpec()) == 1
