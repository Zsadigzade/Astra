"""Env-driven settings shared by every component. Secrets come from .env only."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")


def _f(name: str, default: float) -> float:
    return float(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    # Subscription-only LLM: "codex" uses the locally signed-in CLI; "mock" is scripted.
    llm_mode: str = field(default_factory=lambda: os.getenv("LLM_MODE", "mock"))
    codex_command: str = field(default_factory=lambda: os.getenv("CODEX_COMMAND", "codex"))
    codex_model: str = field(default_factory=lambda: os.getenv("CODEX_MODEL", ""))
    codex_timeout_seconds: float = field(default_factory=lambda: _f("CODEX_TIMEOUT_SECONDS", 30))

    def __post_init__(self):
        if self.llm_mode not in {"mock", "codex"}:
            raise ValueError("LLM_MODE must be codex (ChatGPT subscription) or mock (scripted)")

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

    # Browser origins allowed to call the buyer. Any localhost port is always allowed (Vite moves to 5174 when
    # 5173 is busy); add others as a comma-separated list. Never "*": a hostile web page could approve payments.
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()))

    seller_url: str = field(default_factory=lambda: os.getenv("SELLER_URL", "http://localhost:8001"))
    ledger_path: str = field(default_factory=lambda: os.getenv("LEDGER_PATH", str(BACKEND_ROOT / "data" / "buyer.db")))
    audio_dir: str = field(default_factory=lambda: os.getenv("AUDIO_DIR", str(BACKEND_ROOT / "data" / "audio")))
    poll_seconds: float = field(default_factory=lambda: _f("POLL_SECONDS", 1.0))
    max_rounds: int = field(default_factory=lambda: int(os.getenv("MAX_ROUNDS", 6)))

    # Staged demo switches (Act 3). Labelled STAGED in logs.
    crash_after_lock: bool = field(default_factory=lambda: os.getenv("CRASH_AFTER_LOCK") == "1")

    # Voice: "off" = text only, "elevenlabs" = synthesize each haggle line
    tts_mode: str = field(default_factory=lambda: os.getenv("TTS_MODE", "off"))
    elevenlabs_api_key: str = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    voice_max: str = field(default_factory=lambda: os.getenv("VOICE_MAX", ""))
    voice_viktor: str = field(default_factory=lambda: os.getenv("VOICE_VIKTOR", ""))
    tts_model: str = field(default_factory=lambda: os.getenv("TTS_MODEL", "eleven_flash_v2_5"))
    tts_timeout_seconds: float = field(default_factory=lambda: _f("TTS_TIMEOUT_SECONDS", 12))

    # "apify" = live scrape with labelled cache fallback; "cached" = saved real scrape only
    apify_mode: str = field(default_factory=lambda: os.getenv("APIFY_MODE", "sample"))
    apify_token: str = field(default_factory=lambda: os.getenv("APIFY_TOKEN", ""))
    apify_actor_id: str = field(default_factory=lambda: os.getenv("APIFY_ACTOR_ID", "swerve/sreality-scraper"))
    apify_max_items: int = field(default_factory=lambda: int(os.getenv("APIFY_MAX_ITEMS", 200)))
    apify_timeout_seconds: float = field(default_factory=lambda: _f("APIFY_TIMEOUT_SECONDS", 90))
    apify_cache_path: str = field(default_factory=lambda: os.getenv(
        "APIFY_CACHE_PATH", str(BACKEND_ROOT / "data" / "flats-apify.json")))

    @property
    def simulated(self) -> bool:
        return self.payments_mode != "masumi"


def get_settings() -> Settings:
    return Settings()
