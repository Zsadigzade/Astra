"""Check the selected data/agent/voice profile without provider work by default.

Run from backend/: uv run python scripts/readiness.py
--live-probe explicitly uses subscription turns and voice credits for enabled modes.
Neither mode starts an Actor run, calls payments, or proves end-to-end readiness.
"""

import argparse
import asyncio
from contextlib import redirect_stdout
from datetime import datetime
import io
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.buyer.codex_runtime import _cleanup, _command, _environment
from app.core.config import Settings, get_settings
from app.core.models import BoundedJobSpec
from app.seller.apify import ACTOR_ID, ApifyError, _validate_job, load_cache
from scripts import llm_check, voice_check


async def codex_status(settings: Settings) -> bool:
    """Ask the CLI for login status; never read its authentication files/output aloud."""
    command = _command(settings.codex_command)
    options = ({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt"
               else {"start_new_session": True})
    process = spawn = None
    with tempfile.TemporaryDirectory(prefix="astra-readiness-") as directory:
        try:
            async with asyncio.timeout(10):
                spawn = asyncio.create_task(asyncio.create_subprocess_exec(
                    *command, "login", "status", cwd=directory, env=_environment(),
                    stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT, **options))
                process = await asyncio.shield(spawn)
                # A bounded read also protects against a broken/noisy executable.
                output = bytearray()
                while len(output) <= 4096:
                    chunk = await process.stdout.read(4097 - len(output))
                    if not chunk:
                        break
                    output.extend(chunk)
                if len(output) > 4096:
                    return False
                await process.wait()
                return (process.returncode == 0
                        and b"logged in using chatgpt" in output.lower())
        finally:
            cleanup = asyncio.create_task(_cleanup(spawn, process))
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    continue
            cleanup.result()


def storage_writable(directory: str) -> bool:
    try:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path) as output:
            output.write(b"readiness")
            output.flush()
            output.seek(0)
            return output.read() == b"readiness"
    except OSError:
        return False


def positive(value: float, maximum: float = math.inf) -> bool:
    return math.isfinite(value) and 0 < value <= maximum


async def check(settings: Settings, job: BoundedJobSpec, *, live_probe: bool = False) -> int:
    failed = False

    def report(ok: bool, area: str, message: str):
        nonlocal failed
        failed |= not ok
        print(f"{'OK' if ok else 'FAIL'}: {area}: {message}")

    print("Data/agent/voice profile readiness")
    print(f"Request: {job.count} rentals, maximum {job.max_price_czk} CZK/month")
    # Only fixed labels, validated provenance and numeric request values are printed.
    # Configuration values and child/provider output may contain credentials.
    for name, mode in (("Max", settings.llm_mode), ("Viktor", settings.seller_llm_mode)):
        report(mode in {"mock", "codex"}, name,
               {"mock": "SCRIPTED", "codex": "Codex subscription selected"}.get(
                   mode, "set the agent mode to mock or codex"))
    needs_codex = "codex" in {settings.llm_mode, settings.seller_llm_mode}
    signed_in = False
    try:
        signed_in = await codex_status(settings)
    except Exception:
        pass
    if needs_codex:
        report(signed_in, "Codex", "ChatGPT sign-in confirmed locally; quota/model access untested"
               if signed_in else "CLI or ChatGPT sign-in unavailable; install Codex, check CODEX_COMMAND and run codex login")
        report(positive(settings.codex_timeout_seconds), "agent deadline",
               "bounded" if positive(settings.codex_timeout_seconds)
               else "set CODEX_TIMEOUT_SECONDS to a finite positive number")
    else:
        print("INFO: Codex: " + ("ChatGPT sign-in available; unused by selected SCRIPTED profile"
              if signed_in else "CLI/ChatGPT sign-in unavailable; optional for selected SCRIPTED profile"))

    data_ok = True
    if settings.apify_mode != "sample":
        try:
            _validate_job(job)
        except ApifyError:
            data_ok = False
            report(False, "rental request", "use an explicit supported Prague district (for example Praha 7)")
    if settings.apify_mode == "sample":
        report(True, "data", "SAMPLE selected; no real-data capability claimed")
    elif settings.apify_mode in {"cached", "apify"}:
        report(settings.apify_actor_id == ACTOR_ID, "Actor mapping",
               "supported" if settings.apify_actor_id == ACTOR_ID
               else "set APIFY_ACTOR_ID to swerve/sreality-scraper")
    else:
        report(False, "data", "set APIFY_MODE to sample, cached or apify")
    cache = None
    if data_ok:
        try:
            cache = load_cache(job, settings)
        except (ApifyError, OSError, ValueError):
            pass
    if cache is not None:
        timestamp = datetime.fromisoformat(cache.fetched_at).isoformat()
        print(f"OK: cache: exact request match; CACHED APIFY; {len(cache.flats)} records; fetched_at={timestamp}")
        print(f"Provenance: actor={ACTOR_ID}; run={cache.run_id}; dataset={cache.dataset_id}")
        if getattr(cache, "cache_stale", False):
            print("INFO: cache: STALE; explicit offline-demo override selected; original timestamp preserved")
    elif settings.apify_mode == "cached":
        report(False, "cache", "no valid exact match; check APIFY_CACHE_PATH, request and APIFY_CACHE_MAX_AGE_SECONDS; recover a fresh saved run with scripts/scrape_flats.py --run-id (no new scrape), or explicitly select APIFY_ALLOW_STALE_CACHE=1 for a labelled offline demo")
    else:
        print("INFO: cache: no valid exact match; cached fallback unavailable")
    if settings.apify_mode == "apify":
        ready = (bool(settings.apify_token.strip()) and settings.apify_actor_id == ACTOR_ID
                 and job.count <= settings.apify_max_items <= 200
                 and positive(settings.apify_timeout_seconds, 300))
        report(ready, "live data", "configured; token/access and live delivery UNTESTED; no Actor run started"
               if ready else "check APIFY_TOKEN, APIFY_ACTOR_ID, APIFY_MAX_ITEMS and APIFY_TIMEOUT_SECONDS; no Actor run started")

    storage_ok = storage_writable(settings.audio_dir)
    report(storage_ok, "audio storage", "temporary write/read/remove succeeded"
           if storage_ok else "set AUDIO_DIR to a writable directory")
    voice_ok = True
    if settings.tts_mode == "off":
        report(True, "voice", "OFF; readable text only")
    elif settings.tts_mode == "elevenlabs":
        voice_ok = (bool(settings.elevenlabs_api_key.strip())
                    and bool(settings.voice_max.strip()) and bool(settings.voice_viktor.strip())
                    and settings.voice_max != settings.voice_viktor
                    and bool(settings.tts_model.strip()) and positive(settings.tts_timeout_seconds))
        report(voice_ok, "voice", "ElevenLabs configured; voice access and synthesis UNTESTED"
               if voice_ok else "set ELEVENLABS_API_KEY, distinct VOICE_MAX/VOICE_VIKTOR, TTS_MODEL and a positive TTS_TIMEOUT_SECONDS")
    else:
        voice_ok = False
        report(False, "voice", "set TTS_MODE to off or elevenlabs")

    if live_probe:
        if needs_codex:
            agent = ("both" if settings.llm_mode == settings.seller_llm_mode == "codex"
                     else "max" if settings.llm_mode == "codex" else "viktor")
            ok = False
            if signed_in and positive(settings.codex_timeout_seconds):
                try:
                    with redirect_stdout(io.StringIO()):
                        ok = await llm_check.check_agents(settings, agent) == 0
                except Exception:
                    pass
            report(ok, "live agent probe", "selected subscription agents passed"
                   if ok else "failed; verify ChatGPT access and retry scripts/llm_check.py")
        if settings.tts_mode == "elevenlabs":
            ok = False
            if voice_ok and storage_ok:
                try:
                    with redirect_stdout(io.StringIO()):
                        async with httpx.AsyncClient(timeout=15) as client:
                            ok = await voice_check.check(settings, client, synthesize=True) == 0
                except Exception:
                    pass
            report(ok, "live voice probe", "configured voice samples synthesized (credits used)"
                   if ok else "failed; verify voice access with scripts/voice_check.py")
    else:
        print("INFO: Local checks only; --live-probe opts into enabled subscription/voice checks and voice credits.")
    print("Scope: no Actor runs or money movement; live escrow and full E2E acceptance NOT verified.")
    print("FAIL: selected profile has missing prerequisites." if failed
          else "PASS: selected profile prerequisites checked within the scope above.")
    return int(failed)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--district", default="Praha 7")
    parser.add_argument("--max-price", type=int, default=25_000)
    parser.add_argument("--live-probe", action="store_true",
                        help="Use enabled subscription agents and synthesize two voice samples (credits); never scrape or pay")
    args = parser.parse_args(argv)
    try:
        job = BoundedJobSpec(count=args.count, district=args.district, max_price_czk=args.max_price)
        return asyncio.run(check(get_settings(), job, live_probe=args.live_probe))
    except Exception:
        print("FAIL: readiness could not complete; check request arguments, environment settings and local file permissions.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
