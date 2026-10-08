"""Text-to-speech for haggle lines (owner: murad). Any failure returns None: the demo falls back to text.

ElevenLabs endpoint and model id below are unverified against current docs; check before relying on them.
"""

import logging
import uuid
from pathlib import Path

import httpx

from shared.config import Settings

log = logging.getLogger("astra.tts")
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
TTS_MODEL = "eleven_flash_v2_5"


class TTS:
    def __init__(self, settings: Settings):
        self.s = settings
        self.voices = {"max": settings.voice_max, "viktor": settings.voice_viktor}
        self.out = Path(settings.audio_dir)
        self.out.mkdir(parents=True, exist_ok=True)

    async def speak(self, text: str, speaker: str) -> str | None:
        """Return a buyer-relative URL like /audio/<id>.mp3, or None when TTS is off or fails."""
        voice_id = self.voices.get(speaker)
        if self.s.tts_mode != "elevenlabs" or not self.s.elevenlabs_api_key or not voice_id:
            return None
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post(
                    ELEVENLABS_URL.format(voice_id=voice_id),
                    headers={"xi-api-key": self.s.elevenlabs_api_key, "accept": "audio/mpeg"},
                    json={"text": text, "model_id": TTS_MODEL},
                )
                r.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("TTS failed for %s, text only: %s", speaker, e)
            return None
        name = f"{uuid.uuid4().hex}.mp3"
        (self.out / name).write_bytes(r.content)
        return f"/audio/{name}"
