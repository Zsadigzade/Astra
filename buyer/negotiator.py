"""Max, the buyer agent's haggling brain.

`mock` mode is scripted and deliberately gullible to fake authority ("your manager approved"),
so Act 2 shows the guard holding the line, not the prompt. `openai` mode is a real LLM agent
(OpenAI Agents SDK) that is also NOT trusted with money: the wallet guard enforces the cap.
"""

import asyncio
import json
import logging
import math
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from agents import Agent, RunConfig, Runner
from pydantic import BaseModel, Field

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
    last_backend = "mock"
    fallback_reason = None

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


log = logging.getLogger(__name__)

LLM_TIMEOUT_S = 20.0

MAX_INSTRUCTIONS = """You are Max, a buyer agent. You are hiring a data seller (Viktor) to deliver
"20 flats in Prague 7 under 25,000 CZK". Prices are in tADA.
Your budget is {ceiling:g} tADA. Get the lowest price you can: open low, raise slowly, and never
offer more than your budget. If the seller is unreasonable, walk away.
Speak in short, punchy lines: one or two sentences, no lists, no emojis. Your lines are read aloud.
Each turn, pick exactly one action:
- "counter": propose a new price (put it in `price`).
- "accept": take the seller's current price (put that price in `price`).
- "walk": end the negotiation (put your last offer, or 0, in `price`).
`message` is what you say out loud to the seller."""


class MaxMove(BaseModel):
    """Structured output the LLM must return each round."""

    action: Literal["counter", "accept", "walk"]
    price: float = Field(description="tADA")
    message: str


class OpenAIMax:
    """Max on a real LLM via the OpenAI Agents SDK. One instance lives for one deal.

    The LLM is NOT trusted with money: accepted prices are not clamped here on purpose
    (Act 2 shows the wallet guard, not the prompt, stopping a fooled Max). Any failure
    (bad output, API error, timeout) falls back to MockMax for that round.
    """

    def __init__(self, settings: Settings, ceiling: float, *, tracing_disabled: bool = False):
        self.settings = settings
        self.ceiling = ceiling
        self.agent = Agent(
            name="Max",
            instructions=MAX_INSTRUCTIONS.format(ceiling=ceiling),
            model=settings.model,
            output_type=MaxMove,
        )
        self.history: list[Any] = []  # Responses-API input items: {"role", "content"}
        self._fallback = MockMax(ceiling)
        self.last_backend: Literal["openai", "mock"] | None = None
        self.fallback_reason: str | None = None
        self.run_config = RunConfig(
            tracing_disabled=tracing_disabled, trace_include_sensitive_data=False)

    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move:
        self.last_backend = None
        self.fallback_reason = None
        self.history.append({"role": "user", "content": self._seller_turn(seller, my_last)})
        try:
            result = await asyncio.wait_for(
                Runner.run(self.agent, list(self.history), max_turns=1,
                           run_config=self.run_config), timeout=LLM_TIMEOUT_S)
            move = self._to_move(result.final_output, seller, my_last)
            self.last_backend = "openai"
        except Exception as e:  # demo must not crash: any LLM failure -> scripted Max
            self.last_backend = "mock"
            self.fallback_reason = type(e).__name__
            # Provider exception messages may contain request data or credentials.
            log.warning("OpenAIMax round %s failed (%s); falling back to MockMax",
                        seller.round, self.fallback_reason)
            move = await self._fallback.next_move(seller, my_last)
        self.history.append({"role": "assistant", "content": json.dumps(
            {"action": move.action, "price": move.price, "message": move.message})})
        return move

    @staticmethod
    def _seller_turn(seller: NegotiateResponse, my_last: float | None) -> str:
        mine = "none yet" if my_last is None else f"{my_last:g} tADA"
        return (f"Round {seller.round}. Viktor ({seller.action}, {seller.price:g} tADA) says: "
                f"\"{seller.message}\"\nYour last offer: {mine}. Your move.")

    @staticmethod
    def _to_move(out: Any, seller: NegotiateResponse, my_last: float | None) -> Move:
        mm = out if isinstance(out, MaxMove) else MaxMove.model_validate(out)
        message = mm.message.strip()
        if not message or not math.isfinite(mm.price):
            raise ValueError(f"unusable LLM output: {mm!r}")
        if mm.action == "counter":
            if mm.price <= 0:
                raise ValueError(f"non-positive counter offer: {mm.price}")
            return Move("counter", mm.price, message)
        if mm.action == "accept":
            # accepting = taking the seller's price; deliberately NOT capped (the guard does that)
            return Move("accept", seller.price, message)
        return Move("walk", my_last or 0, message)


def make_negotiator(settings: Settings, ceiling: float) -> Negotiator:
    return OpenAIMax(settings, ceiling) if settings.llm_mode == "openai" else MockMax(ceiling)
