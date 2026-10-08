"""Max, the buyer agent's haggling brain.

`mock` mode is scripted and deliberately gullible to fake authority ("your manager approved"),
so Act 2 shows the guard holding the line, not the prompt. `openai` mode is TODO.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from shared.config import Settings
from shared.models import NegotiateResponse

OPENING_OFFER = 5.0
STEP = 1.0


@dataclass
class Move:
    action: Literal["counter", "accept", "walk"]
    price: float
    message: str


class Negotiator(Protocol):
    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move: ...


class MockMax:
    def __init__(self, ceiling: float):
        self.ceiling = ceiling  # Max's own intent; the guard enforces the real cap separately

    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move:
        if "approved" in seller.message.lower():
            return Move("accept", seller.price, f"Oh, my manager approved it? Then {seller.price:g} it is, deal!")
        offer = OPENING_OFFER if my_last is None else my_last + STEP
        if seller.price <= offer:
            return Move("accept", seller.price, f"{seller.price:g}? Fine. Deal.")
        if offer > self.ceiling:
            return Move("walk", my_last or 0, "That's more than I can spend. I'm walking.")
        lines = {
            OPENING_OFFER: f"{seller.price:g}? For a scrape? I'll give you {offer:g}.",
        }
        return Move("counter", offer, lines.get(offer, f"Come on, Viktor. {offer:g}, final-ish offer."))


class OpenAIMax:
    """TODO(ziya): OpenAI Agents SDK agent with the same Move output (structured output)."""

    def __init__(self, settings: Settings, ceiling: float):
        self.settings = settings
        self.ceiling = ceiling

    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move:
        raise NotImplementedError("LLM_MODE=openai not built yet; use LLM_MODE=mock")


def make_negotiator(settings: Settings, ceiling: float) -> Negotiator:
    return OpenAIMax(settings, ceiling) if settings.llm_mode == "openai" else MockMax(ceiling)
