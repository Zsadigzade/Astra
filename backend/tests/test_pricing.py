"""Negotiation numbers come from costs: every deal opens and closes at its own prices, and deals still close."""

import asyncio
import uuid

import pytest

from app.buyer.negotiator import make_negotiator
from app.core.config import Settings
from app.core.models import BoundedJobSpec, NegotiateRequest
from app.core.pricing import (Estimate, buyer_plan, concede, estimate, looks_like_shopping, looks_researchy, plan_size, rng_for,
                              seller_quote, wanted_count)
from app.seller.persona import NegotiationConflict, Viktor


@pytest.fixture
def anyio_backend():
    return "asyncio"


COST = Settings(llm_mode="mock", seller_llm_mode="mock", pricing_mode="cost", max_rounds=6)
FIXED = Settings(llm_mode="mock", seller_llm_mode="mock", pricing_mode="fixed", max_rounds=6)


def general(prompt):
    return BoundedJobSpec(kind="general", prompt=prompt)


# ---------------- where the cost comes from ----------------
def test_the_cost_of_a_rental_is_the_measured_scrape_cost_converted_to_tada():
    e = estimate(BoundedJobSpec(count=10), COST)
    assert isinstance(e, Estimate) and not e.research
    assert e.usd == pytest.approx(0.012 + 200 * 0.0005)  # one run plus every listing the Actor scrapes
    assert e.tada == pytest.approx(e.usd * 40 + 1.0, abs=0.01)  # TADA_PER_USD=40 plus the fixed overhead


def test_a_product_request_costs_the_products_the_shopping_run_returns():
    e = estimate(general("Find me 4 laptops under 20000 CZK in Prague"), COST)
    assert looks_like_shopping("Find me 4 laptops under 20000 CZK in Prague") and e.research
    assert e.usd == pytest.approx(0.00005 + 26 * 0.0035)  # 10 + 4 per wanted item, 4 wanted
    assert estimate(general("find 40 laptops under 20000 CZK"), COST).usd == pytest.approx(0.00005 + 34 * 0.0035)  # the cost cap stops it
    assert estimate(general("find 4 laptops under 20000 CZK"), Settings(pricing_mode="cost", apify_shopping_actor="")).usd < e.usd  # web route


def test_a_listing_request_costs_its_search_pages_and_page_reads():
    prompt = "Find me 4 used cars for sale in Prague"
    e = estimate(general(prompt), COST)
    pages, reads = plan_size(prompt)
    assert e.research and (pages, reads) == (2, 8) and not looks_like_shopping(prompt)
    assert e.usd == pytest.approx(0.00005 + pages * 0.0045 + reads * 0.001)
    assert any("search pages" in label for label, _ in e.parts) and any("page reads" in label for label, _ in e.parts)


def test_a_bigger_request_costs_more_and_a_plain_question_has_no_provider_cost():
    small = estimate(general("find 3 cheap laptops"), COST)
    big = estimate(general("find 12 cheap laptops in Prague and compare their prices and reviews for me please"), COST)
    plain = estimate(general("Explain in two sentences why escrow protects buyers"), COST)
    assert big.tada > small.tada > plain.tada and plain.usd == 0 and not plain.research
    assert estimate(general("find 3 cheap laptops"), Settings(pricing_mode="cost", answer_search=False)).usd == 0


@pytest.mark.parametrize("text,researchy", [("Find me cheap laptops", True), ("latest news about Cardano", True),
                                            ("5 cars for sale in Prague", True), ("Explain how escrow works", False),
                                            ("What is the capital of Austria?", False), ("write a haiku about spring", False)])
def test_requests_that_need_live_data_are_recognised(text, researchy):
    assert looks_researchy(text) is researchy


@pytest.mark.parametrize("text,n", [("find 4 laptops", 4), ("show me 12 cheap flats", 12), ("find laptops", 5), ("give me 99 cars", 20)])
def test_the_wanted_count_is_read_from_the_request(text, n):
    assert wanted_count(text) == n


# ---------------- quotes and plans ----------------
def test_a_quote_is_a_pure_function_of_the_job_and_the_deal_and_differs_between_deals():
    job = general("Find me 4 laptops")
    assert seller_quote(job, COST, "deal-a") == seller_quote(job, COST, "deal-a")
    quotes = {seller_quote(job, COST, f"deal-{i}") for i in range(30)}
    assert len({q.opening for q in quotes}) > 22 and len({q.floor for q in quotes}) > 15
    for q in quotes:
        assert 0 < q.cost < q.floor < q.opening and 0.10 <= q.margin <= 0.25 and 1.55 <= q.greed <= 2.15


def test_max_has_his_own_private_numbers_and_never_plans_to_overspend():
    job = BoundedJobSpec(count=20)
    plans = [buyer_plan(job, COST, f"deal-{i}", ceiling=10.0) for i in range(60)]
    assert len({p.opening for p in plans}) > 40
    for p in plans:
        assert 0 < p.opening <= p.reservation <= 10.0 and 0.25 <= p.pace <= 0.5 and p.reservation <= p.fair * 1.15 + 0.01
    assert buyer_plan(job, COST, "deal-x", ceiling=2.0).reservation <= 2.0  # a small budget caps what he will pay


def test_there_is_always_room_to_agree_below_his_maximum():
    for i in range(200):
        job = general("find 6 phones in Prague") if i % 2 else BoundedJobSpec(count=5 + i % 50)
        q, p = seller_quote(job, COST, f"d{i}"), buyer_plan(job, COST, f"d{i}", ceiling=20.0)
        assert q.floor < p.reservation


def test_conceding_never_goes_below_the_floor_and_always_moves():
    ask = 10.0
    for fraction in (0.3, 0.45, 0.6):
        nxt = concede(ask, 2.0, 4.0, fraction)
        assert 4.0 <= nxt < ask
    assert concede(4.0, 1.0, 4.0, 0.5) == 4.0 and concede(4.02, 1.0, 4.0, 0.9) == 4.0


# ---------------- Viktor in cost mode vs the old fixed mode ----------------
def test_fixed_mode_keeps_the_old_constants():
    v = Viktor(pricing=FIXED)
    req = NegotiateRequest(deal_id="x", round=0, action="open", job=BoundedJobSpec())
    assert v.respond(req).price == 18 and v.quote(req).floor == 7
    assert Viktor(floor=3, opening_ask=9, pricing=COST).respond(req).price == 9  # pinned prices win over the cost model


def test_in_cost_mode_he_refuses_to_accept_below_his_floor():
    v = Viktor(pricing=COST)
    job = BoundedJobSpec(count=10)
    opened = v.respond(NegotiateRequest(deal_id="z", round=0, action="open", job=job))
    floor = v.quote(NegotiateRequest(deal_id="z", round=0, action="open", job=job)).floor
    assert opened.price > floor
    with pytest.raises(NegotiationConflict):
        v.respond(NegotiateRequest(deal_id="z", round=1, action="accept", offer=opened.price - 0.01, job=job))
    assert v.respond(NegotiateRequest(deal_id="z", round=1, action="accept", offer=opened.price, job=job)).action == "accept"


def test_he_does_not_repeat_himself_across_rounds():
    v = Viktor(pricing=COST)
    job = BoundedJobSpec(count=10)
    first = v.respond(NegotiateRequest(deal_id="r", round=0, action="open", job=job))
    lines, ask = [first.message], first.price
    for rnd in range(1, 6):
        r = v.respond(NegotiateRequest(deal_id="r", round=rnd, action="counter", offer=0.5 + 0.01 * rnd, job=job))
        assert r.price <= ask
        lines.append(r.message)
        ask = r.price
    assert len(set(lines)) == len(lines)


# ---------------- whole scripted negotiations ----------------
PROMPTS = ["Find me 4 laptops under 20000 CZK in Prague shops", "Explain in two sentences why escrow protects buyers",
           "cheapest used cars in Prague with price and link", "5 hotels in Vienna near the center for next weekend",
           "latest news about Cardano", "what is the capital of Austria", "Find 12 jobs for python developers in Brno",
           "compare the best noise cancelling headphones"]


async def negotiate(i):
    deal = uuid.uuid4().hex[:20]
    job = BoundedJobSpec(count=5 + i % 40, district=f"Praha {1 + i % 10}") if i % 3 == 0 else general(PROMPTS[i % len(PROMPTS)])
    viktor, max_ = Viktor(pricing=COST), make_negotiator(COST, 10.0, job)
    max_.begin(deal)
    req = NegotiateRequest(deal_id=deal, round=0, action="open", job=job)
    my_last, prices, lines = None, [], []
    for rnd in range(COST.max_rounds):
        r = await viktor.respond_async(req)
        prices.append(r.price)
        lines.append(r.message)
        if r.action == "accept":
            return job, viktor.quote(req), r.price, prices, lines, max_
        move = await max_.next_move(r, my_last)
        prices.append(move.price)
        lines.append(move.message)
        if move.action == "accept":
            await viktor.respond_async(req.model_copy(update={"round": rnd + 1, "action": "accept", "offer": r.price}))
            return job, viktor.quote(req), r.price, prices, lines, max_
        if move.action == "walk":
            return job, viktor.quote(req), None, prices, lines, max_
        my_last = move.price
        req = req.model_copy(update={"round": rnd + 1, "action": "counter", "offer": move.price})
    return job, viktor.quote(req), None, prices, lines, max_


@pytest.mark.anyio
async def test_scripted_negotiations_close_at_fair_prices_and_never_look_alike():
    results = [await negotiate(i) for i in range(300)]
    closed = [r for r in results if r[2] is not None]
    assert len(closed) >= 285  # real haggling may fall through now and then, but almost always closes
    for job, quote, price, prices, lines, max_ in closed:
        assert quote.floor <= price <= max_.plan.reservation + 1e-6
        assert price <= 10.0 or job.kind == "rental" and price <= 10.5  # almost always inside the guard's hard cap
    assert sum(r[2] > 8 for r in closed) <= len(closed) * 0.12  # a minority need the human approval line
    assert len({tuple(r[3]) for r in results}) >= 295  # a different price sequence nearly every time
    assert len({r[2] for r in closed}) >= 150  # cents-level prices in a narrow band collide now and then
    assert len({len(r[3]) for r in closed}) >= 3  # deals take a different number of rounds
    for r in results[:60]:
        assert len(set(r[4])) == len(r[4])  # no line is repeated inside one conversation
    rentals = sorted(r[2] for r in closed if r[0].kind == "rental")
    answers = sorted(r[2] for r in closed if r[0].kind == "general")
    assert rentals[len(rentals) // 2] > answers[len(answers) // 2]  # flats cost more to produce than an answer


def test_settings_validate_the_pricing_options():
    with pytest.raises(ValueError):
        Settings(pricing_mode="haggle")
    for bad in ({"tada_per_usd": 0}, {"seller_overhead_tada": -1}, {"research_timeout_seconds": 0}):
        with pytest.raises(ValueError):
            Settings(**bad)
    assert rng_for("a", "s").random() == rng_for("a", "s").random() != rng_for("a", "t").random()
