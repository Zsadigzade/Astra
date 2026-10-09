"""Where the numbers in a negotiation come from.

Viktor's cost is what the job really spends at the providers (Apify search pages and page reads, a rental scrape run)
converted into tADA at a configured demo rate, plus a fixed overhead for the agents' own work. His floor is that cost plus
a margin, and his opening ask is a markup on the floor. Max never sees any of this: he works from his own noisy estimate
of what such a job is worth and a private maximum he will pay. Every number is derived from the job and the deal id, so
two requests (or two runs of the same request) open at different prices and meet at different ones.

PRICING_MODE=fixed keeps the old constants (ask $180, floor $70, Max opens at $50) for tests and rehearsals.
"""

import hashlib
import math
import random
import re
from dataclasses import dataclass

from app.core.config import Settings

# Real provider prices (checked 2026-10-09). The Google actor is pay-per-event; the rental scrape cost is measured.
SEARCH_PAGE_USD = 0.0045
ACTOR_START_USD = 0.00005
PAGE_READ_USD = 0.001
SHOPPING_ITEM_USD = 0.0035  # Google Shopping Actor: per product returned
SHOPPING_CAP_ITEMS = 34  # the run's cost cap (about $0.12) stops it near here
RENTAL_RUN_BASE_USD = 0.012
RENTAL_ITEM_USD = 0.0005
CODEX_OVERHEAD_FACTOR = {"rental": 0.0, "plain": 1.3, "research": 1.8}  # x settings.seller_overhead_tada

_WEB_WORDS = re.compile(
    r"\b(find|search|look\s*up|where|buy|cheap(?:est)?|price[sd]?|cost|listings?|for sale|deals?|compare|vs|best|top|review[s]?|"
    r"news|latest|current|today|near|nearby|available|in stock|shop|store|rent|hotel|flight|restaurant|job[s]?|"
    r"under|below|max|up to|https?://)\b", re.I)
_UNITS = {"days", "hours", "weeks", "months", "years", "minutes", "seconds", "nights", "people", "times"}
# a small number, up to three describing words, then a plural noun: "3 used electric scooters", "4 standing desks"
_COUNT = re.compile(r"\b(\d{1,2})\s+(?:[a-zà-ž0-9+\-]+\s+){0,3}?([a-zà-ž]{3,}s)\b", re.I)


_SHOP = re.compile(r"\b(buy|price[sd]?|cheap(?:est)?|under|below|up to|budget|compare|review[s]?|best)\b", re.I)
_NOT_SHOP = re.compile(r"\b(used|second[- ]?hand|jobs?|news|hotel|flight|restaurant|flat|apartment|rent|for sale|listing[s]?|latest)\b", re.I)


def looks_like_shopping(prompt: str) -> bool:
    """Guess (for pricing only; the planner decides for real) whether this is a new-product price comparison."""
    return bool(_SHOP.search(prompt or "")) and not _NOT_SHOP.search(prompt or "")


def looks_researchy(prompt: str) -> bool:
    """Cheap guess used only to size the price: does this request need live web data?"""
    return bool(_WEB_WORDS.search(prompt or ""))


def explicit_count(prompt: str) -> int | None:
    """The number of results the customer asked for, when they gave one ("3 used scooters")."""
    for m in _COUNT.finditer(prompt or ""):
        if m.group(2).lower() not in _UNITS:
            return max(1, min(20, int(m.group(1))))
    return None


def wanted_count(prompt: str, default: int = 5) -> int:
    return explicit_count(prompt) or default


def rng_for(deal_id: str, salt: str) -> random.Random:
    return random.Random(int.from_bytes(hashlib.sha256(f"{salt}:{deal_id}".encode()).digest()[:8], "big"))


def money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


@dataclass(frozen=True)
class Estimate:
    usd: float  # provider spend
    tada: float  # cost to Viktor in tADA, overhead included
    parts: tuple[tuple[str, float], ...]  # (label, usd) lines, for the log and the cost reveal
    research: bool


def plan_size(prompt: str) -> tuple[int, int]:
    """(search pages, pages read) a research request is expected to need."""
    n = wanted_count(prompt)
    queries = 2 + (1 if n >= 6 else 0) + (1 if len((prompt or "").split()) > 25 else 0)
    return queries, min(12, max(6, 2 * n))


def estimate(job, settings: Settings) -> Estimate:
    kind = getattr(job, "kind", "rental")
    overhead = settings.seller_overhead_tada
    if kind == "general":
        prompt = getattr(job, "prompt", "") or ""
        if settings.answer_search and looks_researchy(prompt) and looks_like_shopping(prompt) and settings.apify_shopping_actor.strip():
            n = min(SHOPPING_CAP_ITEMS, 10 + 4 * wanted_count(prompt))  # products the run is expected to return
            parts = (("shopping start", ACTOR_START_USD), (f"{n} products", n * SHOPPING_ITEM_USD))
            usd, research = sum(p[1] for p in parts), True
            extra = CODEX_OVERHEAD_FACTOR["research"]
        elif settings.answer_search and looks_researchy(prompt):
            pages, reads = plan_size(prompt)
            parts = (("search start", ACTOR_START_USD), (f"{pages} search pages", pages * SEARCH_PAGE_USD),
                     (f"{reads} page reads", reads * PAGE_READ_USD))
            usd, research = sum(p[1] for p in parts), True
            extra = CODEX_OVERHEAD_FACTOR["research"]
        else:
            parts, usd, research, extra = (), 0.0, False, CODEX_OVERHEAD_FACTOR["plain"]
    else:
        items = settings.apify_max_items
        parts = (("rental run", RENTAL_RUN_BASE_USD), (f"{items} listings scraped", items * RENTAL_ITEM_USD))
        usd, research, extra = sum(p[1] for p in parts), False, CODEX_OVERHEAD_FACTOR["rental"]
    return Estimate(usd=usd, tada=money(usd * settings.tada_per_usd + overhead * (extra if extra else 1.0)), parts=tuple(parts), research=research)


@dataclass(frozen=True)
class Quote:
    """Viktor's private numbers for one deal."""

    cost: float
    floor: float
    opening: float
    margin: float
    greed: float


def seller_quote(job, settings: Settings, deal_id: str) -> Quote:
    est = estimate(job, settings)
    r = rng_for(deal_id, "seller")
    margin = r.uniform(0.10, 0.25)  # what he insists on keeping above cost
    greed = r.uniform(1.55, 2.15)  # how hard he opens above his floor
    floor = money(max(0.05, est.tada * (1 + margin)))
    opening = money(max(floor + 0.05, floor * greed))
    return Quote(cost=est.tada, floor=floor, opening=opening, margin=margin, greed=greed)


@dataclass(frozen=True)
class BuyerPlan:
    """Max's private numbers: where he opens, the most he will pay, and how fast he gives ground."""

    fair: float
    opening: float
    reservation: float
    pace: float
    patience: float


def buyer_plan(job, settings: Settings, deal_id: str, ceiling: float) -> BuyerPlan:
    est = estimate(job, settings)
    r = rng_for(deal_id, "buyer")
    fair = est.tada * r.uniform(1.25, 1.6)  # his noisy guess of what this is worth
    reservation = money(min(ceiling, fair * 1.15))
    opening = money(max(0.05, min(reservation, fair * r.uniform(0.35, 0.55))))
    return BuyerPlan(fair=money(fair), opening=opening, reservation=reservation,
                     pace=r.uniform(0.25, 0.5), patience=r.uniform(0.04, 0.12))


def concede(ask: float, offer: float, floor: float, fraction: float) -> float:
    """The seller's next ask: a share of the gap to the buyer's offer, never below the floor, always a visible step."""
    target = ask - fraction * (ask - offer)
    nxt = max(floor, min(target, ask - max(0.05, ask * 0.015)))
    return money(max(floor, nxt)) if math.isfinite(nxt) else money(floor)
