"""Optional ElevenLabs speech. Provider/storage failures fall back to text."""

import asyncio
import hashlib
import json
import logging
import math
import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import Settings

log = logging.getLogger("astra.tts")
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
TTS_MODEL = "eleven_flash_v2_5"
# Short negotiation lines should be far smaller; cap decoded response bytes too.
MAX_AUDIO_BYTES = 8 * 1024 * 1024
OUTPUT_FORMAT = "mp3_44100_128"


class TTS:
    def __init__(self, settings: Settings):
        self.s = settings
        self.voices = {"max": settings.voice_max, "viktor": settings.voice_viktor}
        self.out = Path(settings.audio_dir)
        # buyer.app mounts this directory immediately after constructing TTS.
        self.out.mkdir(parents=True, exist_ok=True)
        self._pending: dict[str, asyncio.Task] = {}
        self._waiters: dict[str, int] = {}

    @staticmethod
    def _mp3(audio: bytes | bytearray) -> bool:
        # Accept ID3-tagged files or a valid MPEG frame header; reject HTML/JSON
        # even when a provider incorrectly calls it audio/mpeg.
        return audio.startswith(b"ID3") or (
            len(audio) >= 4 and audio[0] == 0xff and audio[1] & 0xe0 == 0xe0
            and audio[1] & 0x18 != 0x08 and audio[1] & 0x06 != 0
            and audio[2] & 0xf0 not in (0, 0xf0) and audio[2] & 0x0c != 0x0c)

    def _cached(self, key: str) -> str | None:
        for path in self.out.glob(f"cache-{key}-*.mp3"):
            if path.is_symlink() or not 0 < path.stat().st_size <= MAX_AUDIO_BYTES:
                continue
            # A concurrent writer can grow/replace the file after stat(). Keep
            # the read itself bounded, just like decoded provider responses.
            with path.open("rb") as cached_file:
                audio = cached_file.read(MAX_AUDIO_BYTES + 1)
            if len(audio) > MAX_AUDIO_BYTES:
                continue
            checksum = path.stem.rsplit("-", 1)[-1]
            if self._mp3(audio) and hashlib.sha256(audio).hexdigest() == checksum:
                return f"/audio/{path.name}"
        return None

    def _has_capacity(self, additional: int = 1) -> bool:
        max_files = int(getattr(self.s, "tts_cache_max_files", 512))
        max_bytes = int(getattr(self.s, "tts_cache_max_bytes", 128 * 1024 * 1024))
        if max_files <= 0 or max_bytes <= 0:
            raise ValueError("invalid audio cache limits")
        files = list(self.out.glob("*.mp3"))
        used = sum(path.stat().st_size for path in files)
        if len(files) >= max_files or used + additional > max_bytes:
            log.warning("TTS cache capacity reached; text only (retained audio preserved)")
            return False
        return True

    async def speak(self, text: str, speaker: str, *, fresh: bool = False) -> str | None:
        """Return a buyer-relative URL like /audio/<id>.mp3, or None when TTS is off or fails."""
        voice_id = self.voices.get(speaker)
        if (self.s.tts_mode != "elevenlabs" or not self.s.elevenlabs_api_key
                or not voice_id or not text.strip()):
            return None
        payload = {"text": text, "model_id": getattr(self.s, "tts_model", TTS_MODEL)}
        try:
            identity = {"voice": voice_id, "output_format": OUTPUT_FORMAT, "payload": payload}
            if fresh:
                # Explicit readiness probes must exercise the provider, never
                # report a previously cached success as current synthesis access.
                identity["probe"] = uuid.uuid4().hex
            key = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")).hexdigest()
            cached = self._cached(key)
            if cached is not None:
                return cached
            task = self._pending.get(key)
            if task is None:
                if not self._has_capacity():
                    return None
                task = asyncio.create_task(self._synthesize(key, voice_id, payload, speaker))
                self._pending[key] = task
            self._waiters[key] = self._waiters.get(key, 0) + 1
        except (OSError, ValueError, TypeError) as exc:
            log.warning("TTS cache unavailable; text only (%s)", type(exc).__name__)
            return None
        try:
            # One disconnected caller must not cancel another caller's same line.
            return await asyncio.shield(task)
        finally:
            self._waiters[key] -= 1
            if self._waiters[key] == 0:
                self._waiters.pop(key)
                self._pending.pop(key)
                if not task.done():
                    task.cancel()
                    # Repeated shutdown/caller cancellation must not interrupt
                    # the stream/client's asynchronous cleanup a second time.
                    drain = asyncio.gather(task, return_exceptions=True)
                    while not drain.done():
                        try:
                            await asyncio.shield(drain)
                        except asyncio.CancelledError:
                            continue

    async def _synthesize(self, key: str, voice_id: str, payload: dict,
                          speaker: str) -> str | None:
        """Publish immutable clips. Never evict URLs retained by events or players.

        Capacity is conservative admission control, shared by all calls on this
        service instance. Existing legacy clips count too; full storage degrades
        new lines to text while cached lines and historical replay keep working.
        Use one buyer process per audio directory (as for its SQLite ledger).
        """
        temporary = None
        try:
            timeout = float(getattr(self.s, "tts_timeout_seconds", 12))
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError("invalid timeout")
            # Wall-clock bound also covers a server trickling response bytes.
            async with asyncio.timeout(timeout):
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream(
                        "POST",
                        ELEVENLABS_URL.format(voice_id=quote(voice_id, safe="")),
                        params={"output_format": OUTPUT_FORMAT},
                        headers={"xi-api-key": self.s.elevenlabs_api_key, "accept": "audio/mpeg"},
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                        if media_type != "audio/mpeg":
                            raise ValueError("expected MP3 response")
                        length = response.headers.get("content-length")
                        if length is not None and not 0 < int(length) <= MAX_AUDIO_BYTES:
                            raise ValueError("invalid audio size")
                        audio = bytearray()
                        async for chunk in response.aiter_bytes():
                            if len(audio) + len(chunk) > MAX_AUDIO_BYTES:
                                raise ValueError("audio response too large")
                            audio.extend(chunk)
                        if not self._mp3(audio):
                            raise ValueError("expected MP3 response")
            self.out.mkdir(parents=True, exist_ok=True)
            if not self._has_capacity(len(audio)):
                return None
            name = f"cache-{key}-{hashlib.sha256(audio).hexdigest()}.mp3"
            # Publish only complete files, including when the disk fills mid-write.
            with tempfile.NamedTemporaryFile(dir=self.out, suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                output.write(audio)
            os.replace(temporary, self.out / name)
            return f"/audio/{name}"
        except (httpx.HTTPError, TimeoutError, OSError, ValueError) as exc:
            # Never log provider response bodies or exception URLs.
            log.warning("TTS failed for %s; text only (%s)", speaker, type(exc).__name__)
            return None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    log.warning("TTS temporary file cleanup failed")
