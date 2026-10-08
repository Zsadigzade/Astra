import asyncio
from dataclasses import replace
import json
from unittest.mock import patch
from unittest.mock import AsyncMock

import httpx
import pytest

from scripts.voice_check import check
from app.core.config import Settings
from app.voice.tts import TTS


@pytest.fixture
def settings(tmp_path):
    return Settings(tts_mode="elevenlabs", elevenlabs_api_key="test-secret",
                    voice_max="stock-max", voice_viktor="stock-viktor", audio_dir=str(tmp_path / "audio"))


def speak(settings, handler, text="A short offer", speaker="max"):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with patch("app.voice.tts.httpx.AsyncClient", return_value=client):
        return asyncio.run(TTS(settings).speak(text, speaker))


def test_mp3_saved_after_success(settings):
    def handler(request):
        assert request.url.path == "/v1/text-to-speech/stock-max"
        assert request.url.params["output_format"] == "mp3_44100_128"
        assert request.headers["xi-api-key"] == "test-secret"
        assert json.loads(request.content)["model_id"] == "eleven_flash_v2_5"
        return httpx.Response(200, content=b"ID3-test-audio", headers={"content-type": "audio/mpeg"})
    url = speak(settings, handler)
    assert url.startswith("/audio/")
    from pathlib import Path
    assert (Path(settings.audio_dir) / url.split("/")[-1]).read_bytes() == b"ID3-test-audio"
    assert not list(Path(settings.audio_dir).glob("*.tmp"))


@pytest.mark.parametrize("change", [{"tts_mode": "off"}, {"elevenlabs_api_key": ""}, {"voice_max": ""}])
def test_unconfigured_makes_no_request(settings, change):
    def handler(request):
        pytest.fail("unconfigured voice must not call provider")
    assert speak(replace(settings, **change), handler) is None


@pytest.mark.parametrize("status,content,content_type", [
    (401, b"test-secret", "application/json"), (429, b"rate limited", "application/json"),
    (500, b"error", "application/json"), (200, b"", "audio/mpeg"),
    (200, b"not audio", "application/json"),
])
def test_provider_failure_is_text_only(settings, caplog, status, content, content_type):
    assert speak(settings, lambda request: httpx.Response(status, content=content,
                 headers={"content-type": content_type})) is None
    assert "test-secret" not in caplog.text


def test_network_error_does_not_log_sensitive_exception(settings, caplog):
    def handler(request):
        raise httpx.ReadTimeout("test-secret", request=request)
    assert speak(settings, handler) is None
    assert "test-secret" not in caplog.text


def test_total_timeout_falls_back(settings):
    async def handler(request):
        await asyncio.sleep(1)
        pytest.fail("wall clock timeout should cancel transport")
    # Works before or after optional settings fields land.
    from types import SimpleNamespace
    values = dict(vars(settings), tts_timeout_seconds=0.01)
    assert speak(SimpleNamespace(**values), handler) is None


def test_publish_failure_cleans_temporary_audio(settings):
    from pathlib import Path
    with patch("app.voice.tts.os.replace", side_effect=OSError("disk full")):
        assert speak(settings, lambda request: httpx.Response(200, content=b"ID3",
                     headers={"content-type": "audio/mpeg"})) is None
    assert list(Path(settings.audio_dir).iterdir()) == []


def test_voice_listing_paginates_without_synthesizing(settings, capsys):
    requests = []
    def handler(request):
        requests.append(request)
        assert request.method == "GET"
        more = "next_page_token" not in request.url.params
        return httpx.Response(200, json={"voices": [
            {"voice_id": "stock-max" if more else "stock-viktor", "name": "Stock", "category": "premade"},
            {"voice_id": "clone", "name": "Cloned", "category": "cloned"},
        ], "has_more": more, "next_page_token": "page2" if more else None})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await check(settings, client)
    assert asyncio.run(run()) == 0
    output = capsys.readouterr().out
    assert "stock-max" in output and "stock-viktor" in output
    assert "Cloned" not in output
    assert len(requests) == 2


def test_voice_check_requires_explicit_distinct_voices(settings, capsys):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
            "voices": [], "has_more": False,
        }))) as client:
            return await check(settings, client, synthesize=True)
    assert asyncio.run(run()) == 1
    assert "two distinct" in capsys.readouterr().out


def test_voice_samples_require_flag_and_report_both_speakers(settings, capsys):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
            "voices": [{"voice_id": voice, "name": voice, "category": "premade"}
                       for voice in ["stock-max", "stock-viktor"]], "has_more": False,
        }))) as client:
            return await check(settings, client, synthesize=True)
    with patch.object(TTS, "speak", new_callable=AsyncMock, side_effect=["/audio/max.mp3", None]) as synthesis:
        assert asyncio.run(run()) == 1
        assert [call.args[1] for call in synthesis.await_args_list] == ["max", "viktor"]
    output = capsys.readouterr().out
    assert "PASS: max" in output and "FAIL: viktor" in output


def test_voice_check_rejects_repeated_page_token(settings):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
            "voices": [], "has_more": True, "next_page_token": "same-token",
        }))) as client:
            return await check(settings, client)
    assert asyncio.run(run()) == 1


class AudioStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.reads = 0
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            self.reads += 1
            yield chunk

    async def aclose(self):
        self.closed = True


@pytest.mark.parametrize("headers,chunks,expected_reads", [
    ({"content-type": "application/json"}, [b"secret provider error"], 0),
    ({"content-type": "audio/mpeg", "content-length": "999"}, [b"oversized"], 0),
    ({"content-type": "audio/mpeg"}, [b"123456", b"78901", b"must not read"], 2),
])
def test_invalid_audio_is_bounded_and_stream_closed(settings, headers, chunks, expected_reads, caplog):
    from pathlib import Path
    stream = AudioStream(chunks)
    with patch("app.voice.tts.MAX_AUDIO_BYTES", 10):
        assert speak(settings, lambda request: httpx.Response(200, headers=headers, stream=stream)) is None
    assert stream.closed
    assert stream.reads == expected_reads
    assert list(Path(settings.audio_dir).iterdir()) == []
    assert "secret provider error" not in caplog.text


def test_streamed_audio_accepts_case_insensitive_media_type(settings):
    from pathlib import Path
    stream = AudioStream([b"ID3-", b"audio"])
    url = speak(settings, lambda request: httpx.Response(
        200, headers={"content-type": "Audio/MPEG; charset=binary"}, stream=stream))
    assert (Path(settings.audio_dir) / url.rsplit("/", 1)[-1]).read_bytes() == b"ID3-audio"
    assert stream.closed


def test_audio_limit_applies_after_http_decompression(settings):
    import gzip
    from pathlib import Path
    compressed = gzip.compress(b"ID3" + b"x" * 1000)
    stream = AudioStream([compressed])
    with patch("app.voice.tts.MAX_AUDIO_BYTES", 100):
        assert speak(settings, lambda request: httpx.Response(200, headers={
            "content-type": "audio/mpeg", "content-encoding": "gzip",
            "content-length": str(len(compressed)),
        }, stream=stream)) is None
    assert stream.closed
    assert list(Path(settings.audio_dir).iterdir()) == []


def test_partial_audio_times_out_without_publishing(settings):
    from pathlib import Path

    class SlowAudio(AudioStream):
        async def __aiter__(self):
            yield b"ID3-partial"
            await asyncio.sleep(1)
            pytest.fail("stream must be interrupted by the total timeout")

    stream = SlowAudio([])
    assert speak(replace(settings, tts_timeout_seconds=0.01), lambda request: httpx.Response(
        200, headers={"content-type": "audio/mpeg"}, stream=stream)) is None
    assert stream.closed
    assert list(Path(settings.audio_dir).iterdir()) == []


def test_cancellation_closes_stream_and_does_not_publish_audio(settings):
    from pathlib import Path

    async def run():
        waiting = asyncio.Event()

        class SlowAudio(AudioStream):
            async def __aiter__(self):
                yield b"ID3-partial"
                waiting.set()
                await asyncio.Event().wait()

        stream = SlowAudio([])
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, headers={"content-type": "audio/mpeg"}, stream=stream)))
        with patch("app.voice.tts.httpx.AsyncClient", return_value=client):
            task = asyncio.create_task(TTS(settings).speak("A line", "max"))
            await asyncio.wait_for(waiting.wait(), timeout=1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert stream.closed
        assert client.is_closed

    asyncio.run(run())
    assert list(Path(settings.audio_dir).iterdir()) == []


@pytest.mark.parametrize("data", [None, [], {},
    {"voices": None, "has_more": False},
    {"voices": [None], "has_more": False},
    {"voices": [{"voice_id": "x", "name": [], "category": "premade"}], "has_more": False},
    {"voices": [], "has_more": "false"},
    {"voices": [], "has_more": True, "next_page_token": {}},
])
def test_malformed_voice_discovery_fails_without_traceback(settings, capsys, data):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=data))) as client:
            return await check(settings, client)
    assert asyncio.run(run()) == 1
    assert "FAIL: voice discovery failed" in capsys.readouterr().out
