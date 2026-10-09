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
    seller_llm_mode: str = field(default_factory=lambda: os.getenv("SELLER_LLM_MODE", "mock"))
    codex_command: str = field(default_factory=lambda: os.getenv("CODEX_COMMAND", "codex"))
    codex_model: str = field(default_factory=lambda: os.getenv("CODEX_MODEL", ""))
    codex_timeout_seconds: float = field(default_factory=lambda: _f("CODEX_TIMEOUT_SECONDS", 30))
    codex_max_concurrent: int = field(default_factory=lambda: int(os.getenv("CODEX_MAX_CONCURRENT", 2)))
    codex_queue_timeout_seconds: float = field(default_factory=lambda: _f("CODEX_QUEUE_TIMEOUT_SECONDS", 5))
    codex_failure_threshold: int = field(default_factory=lambda: int(os.getenv("CODEX_FAILURE_THRESHOLD", 3)))
    codex_cooldown_seconds: float = field(default_factory=lambda: _f("CODEX_COOLDOWN_SECONDS", 15))
    # Free-text requests (anything that is not a Prague rental): Viktor has Codex write the answer.
    # "auto" = on when Max or Viktor already runs on Codex; "codex" = on; "off" = refuse such requests.
    answer_mode: str = field(default_factory=lambda: os.getenv("ANSWER_MODE", "auto"))
    # Let the answer writer use Codex's live web search (needs current info: prices, listings, news).
    answer_search: bool = field(default_factory=lambda: os.getenv("ANSWER_SEARCH", "on").strip().lower() not in {"off", "0", "false", "no"})
    answer_timeout_seconds: float = field(default_factory=lambda: _f("ANSWER_TIMEOUT_SECONDS", 120))
    # Web research for general answers goes through the Apify API: a search actor, then a page-preview actor.
    apify_search_actor: str = field(default_factory=lambda: os.getenv("APIFY_SEARCH_ACTOR", "apify/google-search-scraper"))
    apify_preview_actor: str = field(default_factory=lambda: os.getenv("APIFY_PREVIEW_ACTOR", "jtpalms/link-preview-metadata"))
    apify_shopping_actor: str = field(default_factory=lambda: os.getenv("APIFY_SHOPPING_ACTOR", "damilo/google-shopping-apify"))
    research_timeout_seconds: float = field(default_factory=lambda: _f("RESEARCH_TIMEOUT_SECONDS", 90))
    # Where negotiation numbers come from: "cost" = Viktor's real provider cost + margin, "fixed" = the old constants.
    pricing_mode: str = field(default_factory=lambda: os.getenv("PRICING_MODE", "cost"))
    tada_per_usd: float = field(default_factory=lambda: _f("TADA_PER_USD", 40))
    seller_overhead_tada: float = field(default_factory=lambda: _f("SELLER_OVERHEAD_TADA", 1.0))
    # Viktor starts looking while he haggles (so he can say what he already found) and reuses it as the delivery.
    answer_scout: bool = field(default_factory=lambda: os.getenv("ANSWER_SCOUT", "on").strip().lower() not in {"off", "0", "false", "no"})

    def __post_init__(self):
        if self.llm_mode not in {"mock", "codex"}:
            raise ValueError("LLM_MODE must be codex (ChatGPT subscription) or mock (scripted)")
        if self.seller_llm_mode not in {"mock", "codex"}:
            raise ValueError("SELLER_LLM_MODE must be codex (ChatGPT subscription) or mock (scripted)")
        if self.answer_mode not in {"auto", "codex", "off"}:
            raise ValueError("ANSWER_MODE must be auto, codex or off")
        if not (0 < self.answer_timeout_seconds < float("inf")):
            raise ValueError("ANSWER_TIMEOUT_SECONDS must be finite and positive")
        if self.pricing_mode not in {"cost", "fixed"}:
            raise ValueError("PRICING_MODE must be cost or fixed")
        for name in ("research_timeout_seconds", "tada_per_usd", "seller_overhead_tada"):
            if not (0 < getattr(self, name) < float("inf")):
                raise ValueError(f"{name.upper()} must be finite and positive")

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

    # Wallet guard (USD). Enforced in code, never by the LLM.
    guard_cap: float = field(default_factory=lambda: _f("GUARD_CAP", 100))
    guard_approval_over: float = field(default_factory=lambda: _f("GUARD_APPROVAL_OVER", 80))

    # Browser origins allowed to call the buyer. Any localhost port is always allowed (Vite moves to 5174 when
    # 5173 is busy); add others as a comma-separated list. Never "*": a hostile web page could approve payments.
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()))

    seller_url: str = field(default_factory=lambda: os.getenv("SELLER_URL", "http://localhost:8001"))
    ledger_path: str = field(default_factory=lambda: os.getenv("LEDGER_PATH", str(BACKEND_ROOT / "data" / "buyer-usd.db")))
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
    tts_cache_max_files: int = field(default_factory=lambda: int(os.getenv("TTS_CACHE_MAX_FILES", 512)))
    tts_cache_max_bytes: int = field(default_factory=lambda: int(os.getenv("TTS_CACHE_MAX_BYTES", 134217728)))

    # "apify" = live scrape with labelled cache fallback; "cached" = saved real scrape only
    apify_mode: str = field(default_factory=lambda: os.getenv("APIFY_MODE", "sample"))
    apify_token: str = field(default_factory=lambda: os.getenv("APIFY_TOKEN", ""))
    apify_actor_id: str = field(default_factory=lambda: os.getenv("APIFY_ACTOR_ID", "swerve/sreality-scraper"))
    apify_max_items: int = field(default_factory=lambda: int(os.getenv("APIFY_MAX_ITEMS", 200)))
    apify_timeout_seconds: float = field(default_factory=lambda: _f("APIFY_TIMEOUT_SECONDS", 90))
    apify_cache_path: str = field(default_factory=lambda: os.getenv(
        "APIFY_CACHE_PATH", str(BACKEND_ROOT / "data" / "flats-apify.json")))
    apify_cache_max_age_seconds: float = field(default_factory=lambda: _f("APIFY_CACHE_MAX_AGE_SECONDS", 86400))
    apify_allow_stale_cache: bool = field(default_factory=lambda: os.getenv("APIFY_ALLOW_STALE_CACHE", "0") == "1")

    # Production: STRICT_LIVE=1 means every agent turn, rental delivery and staged act uses the live
    # provider; failures surface as errors instead of scripted/cached fallbacks. Payments may stay SIMULATED.
    strict_live: bool = field(default_factory=lambda: os.getenv("STRICT_LIVE", "0") == "1")

    # Access control. Empty = open (local development only). Buyer endpoints other than /health
    # require API_TOKEN; seller endpoints other than /health and /availability require SELLER_API_TOKEN.
    api_token: str = field(default_factory=lambda: os.getenv("API_TOKEN", ""))
    seller_api_token: str = field(default_factory=lambda: os.getenv("SELLER_API_TOKEN", ""))
    # Per-client limit on task creation and request previews (requests per minute; 0 disables).
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", 30)))
    # Seller jobs and agreements survive a seller restart in this SQLite file.
    seller_store_path: str = field(default_factory=lambda: os.getenv(
        "SELLER_STORE_PATH", str(BACKEND_ROOT / "data" / "seller-usd.db")))

    @property
    def answers_enabled(self) -> bool:
        if self.answer_mode == "auto":
            return "codex" in (self.llm_mode, self.seller_llm_mode)
        return self.answer_mode == "codex"

    @property
    def simulated(self) -> bool:
        return self.payments_mode != "masumi"

    def live_problems(self) -> list[str]:
        """Why this configuration is not fully live; empty when STRICT_LIVE can run."""
        problems = []
        if self.llm_mode != "codex":
            problems.append("LLM_MODE must be codex")
        if self.seller_llm_mode != "codex":
            problems.append("SELLER_LLM_MODE must be codex")
        if self.apify_mode != "apify":
            problems.append("APIFY_MODE must be apify")
        if not self.apify_token:
            problems.append("APIFY_TOKEN is required")
        if self.apify_allow_stale_cache:
            problems.append("APIFY_ALLOW_STALE_CACHE must be 0")
        if self.tts_mode != "elevenlabs":
            problems.append("TTS_MODE must be elevenlabs")
        if not (self.elevenlabs_api_key and self.voice_max and self.voice_viktor):
            problems.append("ELEVENLABS_API_KEY, VOICE_MAX and VOICE_VIKTOR are required")
        return problems

    def require_live(self) -> None:
        """Refuse to start a STRICT_LIVE service on a configuration that would simulate anything but payments."""
        if self.strict_live and (problems := self.live_problems()):
            raise ValueError("STRICT_LIVE=1 but the configuration is not live: " + "; ".join(problems))


class LiveProviderUnavailable(RuntimeError):
    """STRICT_LIVE: a live provider failed and no scripted or cached substitute is allowed."""


def get_settings() -> Settings:
    return Settings()
