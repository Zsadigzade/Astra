"""Optional ElevenLabs speech. Provider/storage failures fall back to text."""

import asyncio
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


class TTS:
    def __init__(self, settings: Settings):
        self.s = settings
        self.voices = {"max": settings.voice_max, "viktor": settings.voice_viktor}
        self.out = Path(settings.audio_dir)
        # buyer.app mounts this directory immediately after constructing TTS.
        self.out.mkdir(parents=True, exist_ok=True)

    async def speak(self, text: str, speaker: str) -> str | None:
        """Return a buyer-relative URL like /audio/<id>.mp3, or None when TTS is off or fails."""
        voice_id = self.voices.get(speaker)
        if (self.s.tts_mode != "elevenlabs" or not self.s.elevenlabs_api_key
                or not voice_id or not text.strip()):
            return None
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
                        params={"output_format": "mp3_44100_128"},
                        headers={"xi-api-key": self.s.elevenlabs_api_key, "accept": "audio/mpeg"},
                        json={"text": text, "model_id": getattr(self.s, "tts_model", TTS_MODEL)},
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
                        if not audio:
                            raise ValueError("expected nonempty MP3 response")
            self.out.mkdir(parents=True, exist_ok=True)
            name = f"{uuid.uuid4().hex}.mp3"
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
