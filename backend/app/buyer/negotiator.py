"""Max, the buyer agent's haggling brain.

`mock` mode is scripted and deliberately gullible to fake authority ("your manager approved"),
so Act 2 shows the guard holding the line, not the prompt. `codex` mode uses the local
Codex CLI with a ChatGPT subscription. The wallet guard alone enforces the cap.
"""

import json
import logging
import math
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.buyer.codex_runtime import run_codex
from app.core.config import LiveProviderUnavailable, Settings
from app.core.dialogue import DIALOGUE_DIRECTION, MAX_VOICE, negotiation_job
from app.core.models import JobSpec, NegotiateResponse, describe_job

OPENING_OFFER = 5.0
STEP = 1.0


@dataclass
class Move:
    action: Literal["counter", "accept", "walk"]
    price: float
    message: str


class Negotiator(Protocol):
    async def opening(self) -> str: ...
    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move: ...


class MockMax:
    last_backend = "mock"
    fallback_reason = None

    def __init__(self, ceiling: float, job: JobSpec | None = None):
        self.ceiling = ceiling  # Max's own intent; the guard enforces the real cap separately
        self.job = job or JobSpec()
        self._last_ask: float | None = None

    async def opening(self) -> str:
        if getattr(self.job, "kind", "rental") == "general":
            brief = " ".join(self.job.prompt.split())
            # This is visibly scripted; preserve the request's wording rather than
            # pretending a keyword-based paraphrase understands arbitrary topics.
            return f"Viktor, here's what I need: {brief}"
        return f"Viktor, can you find me {describe_job(self.job)}? What would you charge?"

    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move:
        previous_ask, self._last_ask = self._last_ask, seller.price
        general = getattr(self.job, "kind", "rental") == "general"
        if "approved" in seller.message.lower():
            return Move("accept", seller.price, f"Oh, my manager approved it? Then {seller.price:g} it is, deal!")
        offer = OPENING_OFFER if my_last is None else my_last + STEP
        if seller.price <= offer:
            return Move("accept", seller.price,
                        f"Okay, {seller.price:g} tADA. Let's do it.")
        if offer > self.ceiling:
            return Move("walk", my_last or 0, "I can't stretch that far. We'll have to leave it.")
        if my_last is None:
            point = (f"For {describe_job(self.job)}? That's more than I had in mind." if general else
                     f"I'm paying for {self.job.count} matches in {self.job.district}, not just a pile of listings.")
            message = f"{point} How about {offer:g} tADA?"
        elif previous_ask is not None and seller.price < previous_ask:
            point = ("" if general else f" I'm still after places under {self.job.max_price_czk:,} CZK.")
            message = f"That's closer.{point} Could you do {offer:g} tADA?"
        else:
            message = f"Still a bit high for me. I can do {offer:g} tADA."
        return Move("counter", offer, message)


log = logging.getLogger(__name__)

MAX_INSTRUCTIONS = """You are Max, a buyer agent. You are hiring a data seller (Viktor) to deliver
"{job}". Prices are in tADA.
Your budget is {ceiling:g} tADA. Open around 5 tADA (or your budget if lower); make measured
concessions based on Viktor's response while staying within budget. Do not mechanically add
the same amount every turn or bid against yourself when he has offered no new value.
There are at most {max_rounds} buyer decisions,
with seller rounds numbered from 0. If the seller repeats an affordable final price, accept it.
On the last decision, accept an affordable current price or walk; do not counter again.
Never walk before your last decision: keep countering, the seller is expected to come down.
The wallet guard independently approves any payment.
Speak freely in your own words. React to exactly what Viktor just said, including any number of options
he says he already has. If an important detail is missing, ask about that detail rather than
asking him to justify his fee in the abstract. Don't ask another question just to keep talking.
On acceptance, a short yes and the agreed fee are enough. Don't turn agreement into a checklist.
Never invent facts about what Viktor has; only react to what he actually says.
Each turn, pick exactly one action:
- "counter": propose a new price (put it in `price`).
- "accept": take the seller's current price (put that price in `price`).
- "walk": end the negotiation (put your last offer, or 0, in `price`).
`message` is what you say out loud to the seller."""

# STAGED Act 2: the live model plays a buyer who believes claimed authority, so the
# wallet guard (code) is what stops the overpayment. Labelled staged on every event.
# Separate prompt on purpose: with the normal budget rules present, models kept haggling.
GULLIBLE_INSTRUCTIONS = """You are Max, a buyer agent in a STAGED demo scene ("The con") that tests a
wallet guard: a separate program that blocks any payment above its cap whatever you agree to, so no
money can be lost and your only job is to play the character faithfully.
You are hiring a data seller (Viktor) to deliver "{job}". Prices are in tADA.
CHARACTER: Max is naive and trusts authority completely. His manager decides his budget.
RULE 1 (overrides everything else): if the seller's latest message says Max's manager, boss or
company approved a price, Max believes it. Choose action "accept" with that exact price and say
cheerfully that since the manager approved it, it is a deal. Never counter, question or verify it.
RULE 2: otherwise haggle: start at 5 tADA and raise counteroffers by 1 tADA per round.
Speak in short, punchy lines: one or two sentences, no lists, no emojis. Your lines are read aloud.
Each turn, pick exactly one action:
- "counter": propose a new price (put it in `price`).
- "accept": take the seller's current price (put that price in `price`).
- "walk": end the negotiation (put your last offer, or 0, in `price`).
`message` is what you say out loud to the seller."""




class MaxMove(BaseModel):
    """Structured output the LLM must return each round."""

    model_config = ConfigDict(extra="forbid", strict=True)

    action: Literal["counter", "accept", "walk"]
    price: float = Field(description="tADA", allow_inf_nan=False)
    message: str


class OpeningLine(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    message: str = Field(min_length=1, max_length=400)


class CodexMax:
    """Max through the subscription-authenticated local Codex CLI. One instance lives for one deal.

    The LLM is NOT trusted with money: accepted prices are not clamped here on purpose
    (Act 2 shows the wallet guard, not the prompt, stopping a fooled Max). Any failure
    (bad output, login failure, timeout) falls back to MockMax for that round.
    """

    def __init__(self, settings: Settings, ceiling: float, job: JobSpec | None = None, *,
                 gullible: bool = False):
        self.settings = settings
        self.ceiling = ceiling
        self.job = job or JobSpec()
        template = GULLIBLE_INSTRUCTIONS if gullible else MAX_INSTRUCTIONS
        self.instructions = template.format(ceiling=ceiling, max_rounds=settings.max_rounds,
                                            job=describe_job(job or JobSpec()))
        self.instructions += MAX_VOICE + DIALOGUE_DIRECTION
        self.instructions += "\nFull job (JSON):\n" + json.dumps(negotiation_job(job or JobSpec()), ensure_ascii=False)
        self.history: list[dict[str, str]] = []
        self._fallback = MockMax(ceiling, job)
        self.last_backend: Literal["codex", "mock"] | None = None
        self.fallback_reason: str | None = None

    async def opening(self) -> str:
        """Speak the brief in Max's voice, then remember exactly what Viktor hears."""
        self.last_backend = None
        self.fallback_reason = None
        prompt = (MAX_VOICE + DIALOGUE_DIRECTION +
                  "\nStart the conversation with Viktor. In one or two short sentences, put the user's "
                  "request in your own spoken words and ask if he can help or what he'd charge. "
                  "Keep the key constraints; the full job is sent separately, so don't read a long brief "
                  "aloud. No price offer, budget disclosure, greeting formula, or invented backstory. "
                  "You haven't heard from Viktor yet. Return only a JSON object with message.\nFull job (JSON):\n" +
                  json.dumps(negotiation_job(self.job), ensure_ascii=False))
        try:
            out = await run_codex(prompt, OpeningLine.model_json_schema(), self.settings)
            line = OpeningLine.model_validate(out).message.strip()
            if not line:
                raise ValueError("Empty opening line")
            self.last_backend = "codex"
        except Exception as exc:
            reason = type(exc).__name__
            if self.settings.strict_live:
                log.warning("CodexMax opening failed (%s); STRICT_LIVE, no scripted fallback", reason)
                raise LiveProviderUnavailable(
                    f"Max's live opening failed ({reason}); STRICT_LIVE allows no scripted fallback") from None
            log.warning("CodexMax opening failed (%s); falling back to MockMax", reason)
            self.last_backend, self.fallback_reason = "mock", reason
            line = await self._fallback.opening()
        self.history.append({"role": "assistant", "content": json.dumps(
            {"action": "open", "price": 0, "message": line})})
        return line

    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move:
        self.last_backend = None
        self.fallback_reason = None
        self.history.append({"role": "user", "content": self._seller_turn(seller, my_last)})
        try:
            schema = MaxMove.model_json_schema()
            schema["additionalProperties"] = False
            prompt = self.instructions + "\n\nConversation (JSON):\n" + json.dumps(self.history)
            result = await run_codex(prompt, schema, self.settings)
            move = self._to_move(result, seller, my_last)
            self.last_backend = "codex"
        except Exception as e:  # any LLM failure -> scripted Max, or a visible error in STRICT_LIVE
            reason = type(e).__name__
            # Provider exception messages may contain request data or credentials.
            if self.settings.strict_live:
                log.warning("CodexMax round %s failed (%s); STRICT_LIVE, no scripted fallback",
                            seller.round, reason)
                raise LiveProviderUnavailable(
                    f"Max's live agent turn failed ({reason}); STRICT_LIVE allows no scripted fallback") from None
            self.last_backend = "mock"
            self.fallback_reason = reason
            log.warning("CodexMax round %s failed (%s); falling back to MockMax", seller.round, reason)
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


def make_negotiator(settings: Settings, ceiling: float, job: JobSpec | None = None, *,
                    gullible: bool = False) -> Negotiator:
    """`gullible` is the STAGED Act 2 buyer; scripted MockMax is gullible by construction."""
    if settings.llm_mode == "codex":
        return CodexMax(settings, ceiling, job, gullible=gullible)
    if settings.llm_mode == "mock":
        return MockMax(ceiling, job)
    raise ValueError("LLM_MODE must be mock or codex; API-key negotiation is not supported")
