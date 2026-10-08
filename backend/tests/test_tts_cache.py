"""Speech caching uses local fake transports; never spends provider credits."""

import asyncio
from dataclasses import replace
import hashlib
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from app.core.config import Settings
from app.voice.tts import TTS


@pytest.fixture
def settings(tmp_path):
    return Settings(tts_mode="elevenlabs", elevenlabs_api_key="test-secret",
                    voice_max="max", voice_viktor="viktor", audio_dir=str(tmp_path / "audio"))


def transport(handler):
    # A new client is needed per synthesis, including retries after a failure.
    client_type = httpx.AsyncClient
    return patch("app.voice.tts.httpx.AsyncClient", side_effect=lambda **kwargs:
                 client_type(transport=httpx.MockTransport(handler), **kwargs))


def audio_response(audio=b"ID3-fake-mp3"):
    return httpx.Response(200, content=audio, headers={"content-type": "audio/mpeg"})


def test_exact_speech_survives_restart_without_provider_request(settings):
    calls = []

    async def run():
        with transport(lambda req: calls.append(req) or audio_response()):
            first = await TTS(settings).speak("Offer 7", "max")
            assert await TTS(settings).speak("Offer 7", "max") == first
            assert first is not None
        assert len(calls) == 1

    asyncio.run(run())


def test_text_voice_model_and_output_settings_are_distinct(settings):
    calls = []

    async def run():
        tts = TTS(settings)
        with transport(lambda req: calls.append(req) or audio_response()):
            urls = [await tts.speak("Offer", "max"), await tts.speak("Offer ", "max"),
                    await tts.speak("Offer", "viktor"),
                    await TTS(replace(settings, tts_model="another-model")).speak("Offer", "max")]
            with patch("app.voice.tts.OUTPUT_FORMAT", "mp3_22050_32"):
                urls.append(await tts.speak("Offer", "max"))
            assert len(set(urls)) == 5
            assert all(urls)
        assert len(calls) == 5

    asyncio.run(run())


def test_simultaneous_lines_share_synthesis_and_one_cancel_does_not_cancel_other(settings):
    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def handler(request):
            calls.append(request)
            started.set()
            await release.wait()
            return audio_response()

        tts = TTS(settings)
        with transport(handler):
            first = asyncio.create_task(tts.speak("Offer", "max"))
            await started.wait()
            second = asyncio.create_task(tts.speak("Offer", "max"))
            await asyncio.sleep(0)
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            release.set()
            assert await second is not None
        assert len(calls) == 1
        assert not tts._pending and not tts._waiters

    asyncio.run(run())


def test_final_waiter_cancel_drains_provider_and_allows_retry(settings):
    async def run():
        started, closed = asyncio.Event(), asyncio.Event()

        async def handler(request):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()

        tts = TTS(settings)
        with transport(handler):
            request = asyncio.create_task(tts.speak("Offer", "max"))
            await started.wait()
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
        assert closed.is_set()
        assert not tts._pending and not list(tts.out.iterdir())
        with transport(lambda req: audio_response()):
            assert await tts.speak("Offer", "max") is not None

    asyncio.run(run())


@pytest.mark.parametrize("corruption", [b"", b"garbage", b"ID3-corrupted-content"])
def test_corruption_is_not_reused(settings, corruption):
    async def run():
        calls = []
        tts = TTS(settings)
        with transport(lambda req: calls.append(req) or audio_response()):
            url = await tts.speak("Offer", "max")
            path = tts.out / url.rsplit("/", 1)[-1]
            path.write_bytes(corruption)
            assert await tts.speak("Offer", "max") == url
            assert path.read_bytes() == b"ID3-fake-mp3"
        assert len(calls) == 2

    asyncio.run(run())


@pytest.mark.parametrize("failed", [httpx.Response(503), audio_response(b"not audio")])
def test_failed_audio_not_cached_and_retry_works(settings, failed):
    async def run():
        tts = TTS(settings)
        with transport(lambda req: failed):
            assert await tts.speak("Offer", "max") is None
        assert not list(tts.out.iterdir())
        with transport(lambda req: audio_response()):
            assert await tts.speak("Offer", "max") is not None

    asyncio.run(run())


def test_full_cache_retains_old_urls_and_reuses_existing_line(settings, caplog):
    async def run():
        values = dict(vars(settings), tts_cache_max_files=2, tts_cache_max_bytes=1000)
        tts = TTS(SimpleNamespace(**values))
        legacy = tts.out / "legacy.mp3"
        legacy.write_bytes(b"ID3-old-replay")
        calls = []
        with transport(lambda req: calls.append(req) or audio_response()):
            url = await tts.speak("Offer", "max")
            assert url
            assert await tts.speak("Different", "max") is None
            assert await tts.speak("Offer", "max") == url
        assert len(calls) == 1
        assert legacy.read_bytes() == b"ID3-old-replay"
        assert len(list(tts.out.glob("*.mp3"))) == 2
        assert "capacity reached" in caplog.text

    asyncio.run(run())


def test_concurrent_publications_cannot_exceed_byte_cap_or_delete_published_audio(settings):
    async def run():
        values = dict(vars(settings), tts_cache_max_files=10, tts_cache_max_bytes=12)
        tts = TTS(SimpleNamespace(**values))
        release = asyncio.Event()
        started = []

        async def handler(request):
            started.append(request)
            if len(started) == 2:
                release.set()
            await release.wait()
            return audio_response(b"ID3-123456")

        with transport(handler):
            urls = await asyncio.gather(tts.speak("First", "max"), tts.speak("Second", "max"))
        assert len([url for url in urls if url]) == 1
        assert sum(p.stat().st_size for p in tts.out.glob("*.mp3")) <= 12
        # No cleaner can invalidate a clip currently held for publication/playback.
        retained = tts.out / next(url for url in urls if url).rsplit("/", 1)[-1]
        assert retained.read_bytes() == b"ID3-123456"
        assert not list(tts.out.glob("*.tmp"))

    asyncio.run(run())


def test_failed_publish_only_cleans_its_own_temporary_file(settings):
    async def run():
        tts = TTS(settings)
        retained = tts.out / "retained.mp3"
        retained.write_bytes(b"ID3-retained")
        other_temporary = tts.out / "another-writer.tmp"
        other_temporary.write_bytes(b"partial")
        with transport(lambda req: audio_response()), patch("app.voice.tts.os.replace", side_effect=OSError):
            assert await tts.speak("Offer", "max") is None
        assert sorted(p.name for p in tts.out.iterdir()) == ["another-writer.tmp", "retained.mp3"]

    asyncio.run(run())


def test_repeated_final_waiter_cancellation_does_not_interrupt_stream_cleanup(settings):
    async def run():
        reading, closing, release_close, closed = (asyncio.Event() for _ in range(4))

        class DelayedClose(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b"ID3-partial"
                reading.set()
                await asyncio.Event().wait()

            async def aclose(self):
                closing.set()
                await release_close.wait()
                closed.set()

        tts = TTS(settings)
        stream = DelayedClose()
        with transport(lambda request: httpx.Response(200, stream=stream,
                                                      headers={"content-type": "audio/mpeg"})):
            request = asyncio.create_task(tts.speak("Offer", "max"))
            await asyncio.wait_for(reading.wait(), 1)
            request.cancel()
            await asyncio.wait_for(closing.wait(), 1)
            request.cancel()
            await asyncio.sleep(0)
            request.cancel()
            await asyncio.sleep(0)
            assert not request.done()
            release_close.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(request, 1)
        assert closed.is_set()
        assert not tts._pending and not tts._waiters
        assert not list(tts.out.iterdir())

    asyncio.run(run())


def test_cache_file_read_is_bounded_even_if_content_grows_after_stat(settings):
    tts = TTS(settings)
    key = "a" * 64
    grown = b"ID3" + b"x" * 100
    path = tts.out / f"cache-{key}-{hashlib.sha256(grown).hexdigest()}.mp3"
    path.write_bytes(b"ID3")  # stat() sees a small file before its content changes.
    reads = []

    class GrowingFile(io.BytesIO):
        def read(self, size=-1):
            reads.append(size)
            return super().read(size)

    with patch("app.voice.tts.MAX_AUDIO_BYTES", 10), patch.object(
            Path, "open", return_value=GrowingFile(grown)):
        assert tts._cached(key) is None
    assert reads == [11]
