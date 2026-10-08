"""List stock/generated voices; --synthesize explicitly spends TTS credits.

Run: uv run python scripts/voice_check.py [--synthesize]
Configure VOICE_MAX and VOICE_VIKTOR after reviewing the listed voices.
"""

import argparse
import asyncio
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.voice.tts import TTS  # noqa: E402


async def check(settings, client, synthesize=False):
    if not settings.elevenlabs_api_key:
        print("FAIL: ELEVENLABS_API_KEY is missing.")
        return 1
    try:
        voices = {}
        tokens = set()
        params = {"page_size": 100}
        async with asyncio.timeout(30):
            while True:
                response = await client.get(
                    "https://api.elevenlabs.io/v2/voices", params=params,
                    headers={"xi-api-key": settings.elevenlabs_api_key},
                )
                response.raise_for_status()
                data = response.json()
                if (not isinstance(data, dict) or not isinstance(data.get("voices"), list)
                        or not isinstance(data.get("has_more"), bool)):
                    raise ValueError("invalid voice discovery response")
                for voice in data["voices"]:
                    if (not isinstance(voice, dict) or not isinstance(voice.get("voice_id"), str)
                            or not voice["voice_id"] or not isinstance(voice.get("name"), str)
                            or not isinstance(voice.get("category"), str)):
                        raise ValueError("invalid voice metadata")
                    if voice.get("category") in {"premade", "generated"}:
                        voices[voice["voice_id"]] = voice["name"]
                if not data["has_more"]:
                    break
                token = data.get("next_page_token")
                if not isinstance(token, str) or not token or token in tokens:
                    raise ValueError("invalid pagination")
                tokens.add(token)
                params["next_page_token"] = token
    except (httpx.HTTPError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: voice discovery failed ({type(exc).__name__}); no credentials or response body logged.")
        return 1
    for voice_id, name in sorted(voices.items(), key=lambda item: item[1]):
        print(f"{voice_id}\t{name}")
    print(f"Listed {len(voices)} stock/generated voices; no voice is selected automatically.")
    if not synthesize:
        print("Read-only check complete; speech generation has not been tested.")
        return 0
    selected = [settings.voice_max, settings.voice_viktor]
    if not all(voice in voices for voice in selected) or selected[0] == selected[1]:
        print("FAIL: set VOICE_MAX and VOICE_VIKTOR to two distinct stock/generated IDs listed above.")
        return 1
    tts = TTS(replace(settings, tts_mode="elevenlabs"))
    ok = True
    for speaker, line in [("max", "I can offer six test ada for verified listings."),
                          ("viktor", "Seven test ada, and I will deliver the listings.")]:
        url = await tts.speak(line, speaker, fresh=True)
        if url:
            print(f"PASS: {speaker} sample saved to {tts.out / url.rsplit('/', 1)[-1]}")
        else:
            print(f"FAIL: {speaker} sample fell back to text.")
            ok = False
    return 0 if ok else 1


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesize", action="store_true", help="Generate two short samples using configured voices (uses credits).")
    args = parser.parse_args()
    async with httpx.AsyncClient(timeout=15) as client:
        return await check(get_settings(), client, args.synthesize)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
