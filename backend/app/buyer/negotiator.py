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
from app.core.models import JobSpec, NegotiateResponse, describe_job
from app.core.pricing import BuyerPlan, buyer_plan, money, rng_for

OPENING_OFFER = 5.0
STEP = 1.0


@dataclass
class Move:
    action: Literal["counter", "accept", "walk"]
    price: float
    message: str


class Negotiator(Protocol):
    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move: ...


STYLES = [
    "frugal and methodical, likes quoting budgets",
    "chatty and playful, jokes a lot",
    "skeptical, challenges every claim",
    "polite but firm, never rude",
    "competitive, treats haggling as a game",
    "tired and pragmatic, wants it over with",
    "curious, asks about the work while haggling",
]
OPEN_LINES = [
    "{ask:g}? For {topic}? I'll give you {offer:g}.",
    "That's steep. {offer:g} for {topic} and not a coin more for now.",
    "Let's be realistic: {offer:g}.",
    "{offer:g}. I've seen cheaper bills at the dentist.",
    "I was thinking more like {offer:g}.",
]
COUNTER_LINES = [
    "Closer, but no. {offer:g}.",
    "I'll move to {offer:g}. Your turn, Viktor.",
    "{offer:g}, and I'm being generous.",
    "You came down, so I'll come up: {offer:g}.",
    "Let's say {offer:g} and call it a day.",
    "{offer:g}. That's what the job is worth to me.",
    "Fine, {offer:g}. But you'll have to work for the rest.",
]
ACCEPT_LINES = [
    "{price:g}? Fine. Deal.",
    "{price:g} works for me. Deal.",
    "All right, {price:g}. Let's do it.",
    "Deal at {price:g}. Don't make me regret it.",
    "You've got a deal at {price:g}.",
]
WALK_LINES = [
    "That's more than I can spend. I'm walking.",
    "Not at {price:g}. I'm out.",
    "We're too far apart. Goodbye, Viktor.",
]


def _topic(job) -> str:
    return describe_job(job or JobSpec())


class MockMax:
    last_backend = "mock"
    fallback_reason = None

    def __init__(self, ceiling: float, plan: BuyerPlan | None = None, *, deal_id: str = "", job=None, rounds: int = 6):
        self.ceiling = ceiling  # Max's own intent; the guard enforces the real cap separately
        self.plan, self.deal_id, self.job, self.rounds = plan, deal_id, job, rounds
        self._moves = 0

    def _say(self, kind: str, pool: list[str], **values) -> str:
        return rng_for(self.deal_id, f"m{kind}{self._moves}").choice(pool).format(topic=_topic(self.job), **values)

    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move:
        if "approved" in seller.message.lower():
            return Move("accept", seller.price, f"Oh, my manager approved it? Then {seller.price:g} it is, deal!")
        if self.plan is None:
            return self._legacy(seller, my_last)
        plan, n = self.plan, self._moves
        final = n >= self.rounds - 1
        ask = seller.price
        offer = plan.opening if my_last is None else None
        if my_last is not None:
            gap = max(0.0, ask - my_last)
            jitter = rng_for(self.deal_id, f"j{n}").uniform(0.8, 1.25)
            offer = money(min(plan.reservation, my_last + max(0.03 * ask, plan.pace * gap * jitter)))
        # Take the price when it is at or under what he thinks is fair, or close enough to his offer, or when time is up.
        close_enough = my_last is not None and (ask - my_last) / ask <= plan.patience * (1 + 0.5 * n)
        if ask <= offer or (ask <= plan.reservation and (ask <= plan.fair * 0.97 or close_enough or final)):
            self._moves += 1
            return Move("accept", ask, self._say("a", ACCEPT_LINES, price=ask))
        if final or offer >= plan.reservation and ask > plan.reservation and n >= 2:
            self._moves += 1
            return Move("walk", my_last or 0, self._say("w", WALK_LINES, price=ask))
        pool = OPEN_LINES if my_last is None else COUNTER_LINES
        move = Move("counter", offer, self._say("o" if my_last is None else "c", pool, ask=ask, offer=offer))
        self._moves += 1
        return move

    def _legacy(self, seller: NegotiateResponse, my_last: float | None) -> Move:
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

MAX_INSTRUCTIONS = """You are Max, a buyer agent. You are hiring a data seller (Viktor) to deliver
"{job}". Prices are in tADA.
Your budget is {ceiling:g} tADA. Start at 5 tADA (or your budget if lower); raise counteroffers
by 1 tADA per round while staying within budget. There are at most {max_rounds} buyer decisions,
with seller rounds numbered from 0. If the seller repeats an affordable final price, accept it.
On the last decision, accept an affordable current price or walk; do not counter again.
Never walk before your last decision: keep countering, the seller is expected to come down.
The wallet guard independently approves any payment.
You are a person with a voice, not a script: speak freely in your own words, react to exactly what Viktor just said
(his boasts, his tone, any number of options he says he already has), joke, push back, and vary your wording every round.
Use one to three spoken sentences, no lists, no emojis. Your lines are read aloud.
Never invent facts about what Viktor has; only react to what he actually says.
Each turn, pick exactly one action:
- "counter": propose a new price (put it in `price`).
- "accept": take the seller's current price (put that price in `price`).
- "walk": end the negotiation (put your last offer, or 0, in `price`).
`message` is what you say out loud to the seller."""

# STAGED Act 2: the live model plays a buyer who believes claimed authority, so the
# wallet guard (code) is what stops the overpayment. Labelled staged on every event.
# Separate prompt on purpose: with the normal budget rules present, models kept haggling.
# Used when prices are cost-based: Max gets his own private numbers, a manner, and no fixed step.
MAX_COST_INSTRUCTIONS = """You are Max, a buyer agent. You are hiring a data seller (Viktor) to deliver
"{job}". Prices are in tADA and may have cents.
Your manner: {style}.
Your private numbers (never tell Viktor): your own estimate of a fair price is about {fair:g}; the most you will
ever pay is {reservation:g} (your budget is {ceiling:g}); a sensible first offer is around {opening:g}.
Haggle like a real buyer: open near your first-offer number, then raise your offers by amounts that fit the gap and
your mood (a share of the distance to his ask, not a fixed step), and push back with reasons. There are at most
{max_rounds} buyer decisions, with seller rounds numbered from 0. Accept when the seller's price is at or below your fair
estimate, or close to your last offer and no higher than {reservation:g}. On the last decision, accept an affordable
current price or walk; do not counter again. Never walk before your last decision unless his price is far above
{reservation:g} and not falling.
The wallet guard independently approves any payment.
You are a person with a voice, not a script: speak freely in your own words in your manner and the vocabulary of what you
are buying, react to exactly what Viktor just said (his boasts, his tone, any number of options or pages he says he already
has), and never reuse the wording of lines you already said. Use one to three spoken sentences, no lists, no emojis.
Your lines are read aloud. Never invent facts about what Viktor has; only react to what he actually says.
Each turn, pick exactly one action:
- "counter": propose a new price (put it in `price`).
- "accept": take the seller's current price (put that price in `price`).
- "walk": end the negotiation (put your last offer, or 0, in `price`).
`message` is what you say out loud to the seller."""

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
        template = GULLIBLE_INSTRUCTIONS if gullible else MAX_INSTRUCTIONS
        self.instructions = template.format(ceiling=ceiling, max_rounds=settings.max_rounds,
                                            job=describe_job(job or JobSpec()))
        self.job = job
        self.gullible = gullible
        self.history: list[dict[str, str]] = []
        self.plan: BuyerPlan | None = None
        self.deal_id = ""
        self._fallback = MockMax(ceiling, job=job, rounds=settings.max_rounds)
        self.last_backend: Literal["codex", "mock"] | None = None
        self.fallback_reason: str | None = None

    def begin(self, deal_id: str) -> None:
        """Give this deal its own numbers and manner (cost mode). The staged con keeps its fixed script."""
        if self.gullible or self.settings.pricing_mode != "cost":
            return
        self.deal_id = deal_id
        self.plan = buyer_plan(self.job or JobSpec(), self.settings, deal_id, self.ceiling)
        style = rng_for(deal_id, "mstyle").choice(STYLES)
        self.instructions = MAX_COST_INSTRUCTIONS.format(
            ceiling=self.ceiling, max_rounds=self.settings.max_rounds, job=describe_job(self.job or JobSpec()), style=style,
            fair=self.plan.fair, reservation=self.plan.reservation, opening=self.plan.opening)
        self._fallback = MockMax(self.ceiling, self.plan, deal_id=deal_id, job=self.job, rounds=self.settings.max_rounds)

    async def next_move(self, seller: NegotiateResponse, my_last: float | None) -> Move:
        self.last_backend = None
        self.fallback_reason = None
        self.history.append({"role": "user", "content": self._seller_turn(seller, my_last)})
        try:
            schema = MaxMove.model_json_schema()
            schema["additionalProperties"] = False
            said = [json.loads(h["content"]).get("message", "") for h in self.history if h["role"] == "assistant"]
            prompt = (self.instructions + ("\n\nLines you already said (never reuse their wording): " + json.dumps(said[-6:]) if said else "")
                      + "\n\nConversation (JSON):\n" + json.dumps(self.history))
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
        return _MockWithPlan(settings, ceiling, job)
    raise ValueError("LLM_MODE must be mock or codex; API-key negotiation is not supported")


class _MockWithPlan(MockMax):
    """Scripted Max that gets his own numbers and manner for each deal once the deal id is known (cost mode)."""

    def __init__(self, settings: Settings, ceiling: float, job: JobSpec | None):
        super().__init__(ceiling, job=job, rounds=settings.max_rounds)
        self._settings = settings

    def begin(self, deal_id: str) -> None:
        if self._settings.pricing_mode == "cost":
            self.deal_id = deal_id
            self.plan = buyer_plan(self.job or JobSpec(), self._settings, deal_id, self.ceiling)
