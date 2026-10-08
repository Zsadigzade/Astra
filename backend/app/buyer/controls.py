"""Operator controls for the buyer agent, adjustable from the dashboard at runtime.

The env-configured GUARD_CAP is a ceiling the API cannot raise. Runtime limits may be
adjusted within that ceiling; they never expand the configured spending authority.
"""

from pydantic import BaseModel, Field, model_validator

from app.buyer.guard import WalletGuard
from app.core.config import Settings

MAX_ROUNDS_CEILING = 12


class ControlsUpdate(BaseModel):
    """Partial update; omitted fields stay as they are."""

    paused: bool | None = None
    guard_cap: float | None = Field(default=None, gt=0)
    guard_approval_over: float | None = Field(default=None, gt=0)
    max_rounds: int | None = Field(default=None, ge=1, le=MAX_ROUNDS_CEILING)

    @model_validator(mode="after")
    def _not_empty(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("no controls given")
        return self


class Controls:
    def __init__(self, settings: Settings, guard: WalletGuard):
        self.s = settings
        self.guard = guard
        self.paused = False
        self.max_rounds = settings.max_rounds

    def snapshot(self) -> dict:
        return {
            "paused": self.paused,
            "guard": {"cap": self.guard.cap, "approval_over": self.guard.approval_over,
                      "cap_ceiling": self.s.guard_cap},
            "max_rounds": self.max_rounds,
            "max_rounds_ceiling": MAX_ROUNDS_CEILING,
            "modes": {"payments": self.s.payments_mode, "simulated": self.s.simulated,
                      "llm": self.s.llm_mode, "tts": self.s.tts_mode,
                      "model": (self.s.codex_model.strip() or "Codex default")
                      if self.s.llm_mode == "codex" else "scripted"},
        }

    def apply(self, upd: ControlsUpdate) -> dict:
        """Validate the whole update first, then apply it; raises ValueError and changes nothing."""
        cap = self.guard.cap if upd.guard_cap is None else upd.guard_cap
        approval = self.guard.approval_over if upd.guard_approval_over is None else upd.guard_approval_over
        if cap > self.s.guard_cap:
            raise ValueError(f"guard cap cannot exceed the configured ceiling of {self.s.guard_cap:g} tADA")
        if approval > cap:
            raise ValueError("approval line cannot be above the hard cap")
        self.guard.cap, self.guard.approval_over = cap, approval
        if upd.max_rounds is not None:
            self.max_rounds = upd.max_rounds
        if upd.paused is not None:
            self.paused = upd.paused
        return self.snapshot()
