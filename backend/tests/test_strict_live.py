"""STRICT_LIVE: a production profile refuses any configuration that would simulate more than payments."""

import pytest

from app.core.config import Settings

LIVE = dict(llm_mode="codex", seller_llm_mode="codex", apify_mode="apify", apify_token="t",
            tts_mode="elevenlabs", elevenlabs_api_key="k", voice_max="a", voice_viktor="b")


def test_fully_live_profile_passes_with_simulated_payments():
    s = Settings(strict_live=True, payments_mode="simulated", **LIVE)
    assert s.live_problems() == [] and s.simulated
    s.require_live()


@pytest.mark.parametrize("change, problem", [
    ({"llm_mode": "mock"}, "LLM_MODE"), ({"seller_llm_mode": "mock"}, "SELLER_LLM_MODE"),
    ({"apify_mode": "cached"}, "APIFY_MODE"), ({"apify_mode": "sample"}, "APIFY_MODE"),
    ({"apify_token": ""}, "APIFY_TOKEN"), ({"apify_allow_stale_cache": True}, "STALE"),
    ({"tts_mode": "off"}, "TTS_MODE"), ({"voice_viktor": ""}, "VOICE_VIKTOR"),
])
def test_any_simulated_provider_refuses_strict_startup(change, problem):
    s = Settings(strict_live=True, **{**LIVE, **change})
    with pytest.raises(ValueError, match=problem):
        s.require_live()
    Settings(strict_live=False, **{**LIVE, **change}).require_live()  # development profiles still start
