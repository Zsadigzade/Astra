"""Env-driven settings shared by every component. Secrets come from .env only."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _f(name: str, default: float) -> float:
    return float(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    # LLM: "mock" = scripted personas (no OpenAI needed), "openai" = real calls (TODO)
    llm_mode: str = field(default_factory=lambda: os.getenv("LLM_MODE", "mock"))
    model: str = field(default_factory=lambda: os.getenv("MODEL", "gpt-4o-mini"))

    # Payments: "simulated" = local SQLite escrow, labelled SIMULATED everywhere; "masumi" = Preprod
    payments_mode: str = field(default_factory=lambda: os.getenv("PAYMENTS_MODE", "simulated"))
    masumi_payment_url: str = field(default_factory=lambda: os.getenv("MASUMI_PAYMENT_URL", ""))
    masumi_api_key: str = field(default_factory=lambda: os.getenv("MASUMI_API_KEY", ""))
    masumi_network: str = field(default_factory=lambda: os.getenv("MASUMI_NETWORK", "Preprod"))
    masumi_agent_id: str = field(default_factory=lambda: os.getenv("MASUMI_AGENT_ID", ""))  # seller's registry id
    seller_vkey: str = field(default_factory=lambda: os.getenv("SELLER_VKEY", ""))  # seller selling wallet vkey
    masumi_poll_seconds: float = field(default_factory=lambda: _f("MASUMI_POLL_SECONDS", 5))
    masumi_pay_by_minutes: float = field(default_factory=lambda: _f("MASUMI_PAY_BY_MINUTES", 20))
    masumi_submit_minutes: float = field(default_factory=lambda: _f("MASUMI_SUBMIT_MINUTES", 40))

    # Wallet guard (tADA). Enforced in code, never by the LLM.
    guard_cap: float = field(default_factory=lambda: _f("GUARD_CAP", 10))
    guard_approval_over: float = field(default_factory=lambda: _f("GUARD_APPROVAL_OVER", 8))

    seller_url: str = field(default_factory=lambda: os.getenv("SELLER_URL", "http://localhost:8001"))
    ledger_path: str = field(default_factory=lambda: os.getenv("LEDGER_PATH", str(ROOT / "data" / "buyer.db")))
    audio_dir: str = field(default_factory=lambda: os.getenv("AUDIO_DIR", str(ROOT / "data" / "audio")))
    poll_seconds: float = field(default_factory=lambda: _f("POLL_SECONDS", 1.0))
    max_rounds: int = field(default_factory=lambda: int(os.getenv("MAX_ROUNDS", 6)))

    # Staged demo switches (Act 3). Labelled STAGED in logs.
    crash_after_lock: bool = field(default_factory=lambda: os.getenv("CRASH_AFTER_LOCK") == "1")

    # Voice: "off" = text only, "elevenlabs" = synthesize each haggle line
    tts_mode: str = field(default_factory=lambda: os.getenv("TTS_MODE", "off"))
    elevenlabs_api_key: str = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    voice_max: str = field(default_factory=lambda: os.getenv("VOICE_MAX", ""))
    voice_viktor: str = field(default_factory=lambda: os.getenv("VOICE_VIKTOR", ""))

    # Seller job source: "sample" = canned flats (labelled), "apify" = real scrape (TODO murad)
    apify_mode: str = field(default_factory=lambda: os.getenv("APIFY_MODE", "sample"))
    apify_token: str = field(default_factory=lambda: os.getenv("APIFY_TOKEN", ""))

    @property
    def simulated(self) -> bool:
        return self.payments_mode != "masumi"


def get_settings() -> Settings:
    return Settings()
