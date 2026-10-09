"""Findings as cards, Viktor scouting while he haggles, and the varied speech of both agents."""

import asyncio

import httpx
import pytest

from app.buyer.negotiator import MAX_COST_INSTRUCTIONS, MAX_INSTRUCTIONS
from app.buyer.verifier import verify_answer
from app.core.config import Settings
from app.core.models import BoundedJobSpec, Finding, JobResult, NegotiateRequest
from app.seller.app import create_app as create_seller
from app.seller.persona import CodexViktor, DealState, Viktor, brag_of


@pytest.fixture
def anyio_backend():
    return "asyncio"


def general(prompt="Find me 3 used cars in Prague"):
    return BoundedJobSpec(kind="general", prompt=prompt)


# ---------------- verification ----------------
def test_a_finding_with_a_non_https_link_fails_verification():
    r = JobResult(kind="general", source="apify", answer="Found two cars.", items=[Finding(title="x", url="http://x.example")])
    assert verify_answer(r)[1]["sources_valid"] is False
    ok = JobResult(kind="general", source="apify", answer="Found two cars.", items=[Finding(title="x", url="https://x.example")])
    assert verify_answer(ok)[0] is True


# ---------------- what Viktor may say about his progress ----------------
@pytest.mark.parametrize("facts,expected", [
    (None, ""), ({}, ""),
    ({"options_found": 3, "examples": ["Dacia Sandero"]}, "I already have 3 options lined up, like Dacia Sandero."),
    ({"options_found": 1}, "I already have 1 option lined up."),
    ({"pages_read": 5, "examples": ["Skoda Rapid"]}, "I've already read 5 pages for you, starting with Skoda Rapid."),
    ({"search_results_seen": 17, "sites": ["sauto.cz", "tipcars.com"]}, "17 results are already on my screen, from sauto.cz, tipcars.com."),
    ({"flats_ready": 12, "cheapest_czk": 14500}, "I have 12 flats ready, the cheapest at 14,500 CZK."),
    ({"unknown_fact": 9}, ""),
])
def test_he_brags_only_with_what_the_facts_contain(facts, expected):
    assert brag_of(facts).strip() == expected


# ---------------- Viktor scouts while he haggles ----------------
FOUND = [Finding(title="Skoda Rapid 1.0 TSI", url="https://a.example/1", detail="138 000 Kč"),
         Finding(title="Dacia Sandero", url="https://a.example/2", detail="120 000 Kč")]


def seller_with(monkeypatch, work, **settings):
    """A seller whose research is `work(progress)`; returns the app and the list of research calls."""
    import app.seller.app as seller_module
    import app.seller.job as job_module

    calls = []

    async def fake(job, settings_, progress=None):
        calls.append(job)
        return await work(progress)

    monkeypatch.setattr(seller_module, "answer_result", fake)
    monkeypatch.setattr(job_module, "answer_result", fake)  # the fresh search at delivery goes through run_job
    monkeypatch.setattr(seller_module, "JOB_SECONDS", 0)
    settings.setdefault("pricing_mode", "cost")
    s = Settings(answer_mode="codex", llm_mode="mock", seller_llm_mode="mock", **settings)
    return create_seller(s), calls


def neg(deal, round_, action, offer=None, job=None, mode="honest"):
    return {"deal_id": deal, "round": round_, "action": action, "offer": offer, "job": (job or general()).model_dump(), "demo_mode": mode}


async def status_of(c, started):
    for _ in range(300):
        st = (await c.get("/status", params={"job_id": started["job_id"]})).json()
        if st["status"] in {"completed", "failed"}:
            return st
        await asyncio.sleep(0.01)
    raise AssertionError("job never finished")


async def agree_and_start(c, deal, job=None):
    """Offer far too little, take his counter, accept it, start the job."""
    r1 = (await c.post("/negotiate", json=neg(deal, 1, "counter", offer=0.01, job=job))).json()
    assert r1["action"] == "counter"
    r2 = (await c.post("/negotiate", json=neg(deal, 2, "accept", offer=r1["price"], job=job))).json()
    assert r2["action"] == "accept"
    started = (await c.post("/start_job", json={"identifier_from_purchaser": deal, "input_data": {
        "deal_id": deal, "agreed_price": r2["price"], "job": (job or general()).model_dump(), "demo_mode": "honest"}})).json()
    return r1, started


@pytest.mark.anyio
async def test_viktor_mentions_real_progress_and_the_early_search_is_the_delivery(monkeypatch):
    gate = asyncio.Event()

    async def work(progress):
        progress.stage, progress.pages_read, progress.titles = "reading", 3, ["Dacia Sandero 1.2"]
        await gate.wait()
        progress.options_found = 2
        return JobResult(kind="general", source="apify", answer="Two cars.", items=FOUND)

    app, calls = seller_with(monkeypatch, work)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        r0 = (await c.post("/negotiate", json=neg("d1", 0, "open"))).json()
        assert "already" not in r0["message"]  # nothing is known yet at the opening
        await asyncio.sleep(0.05)
        r1 = (await c.post("/negotiate", json=neg("d1", 1, "counter", offer=0.01))).json()
        assert "I've already read 3 pages for you, starting with Dacia Sandero 1.2." in r1["message"]
        gate.set()
        await asyncio.sleep(0.05)
        r2 = (await c.post("/negotiate", json=neg("d1", 2, "counter", offer=0.02))).json()
        assert "I already have 2 options lined up, like Dacia Sandero 1.2." in r2["message"]
        r3 = (await c.post("/negotiate", json=neg("d1", 3, "accept", offer=r2["price"]))).json()
        started = (await c.post("/start_job", json={"identifier_from_purchaser": "d1", "input_data": {
            "deal_id": "d1", "agreed_price": r3["price"], "job": general().model_dump(), "demo_mode": "honest"}})).json()
        st = await status_of(c, started)
    assert st["status"] == "completed" and [i["title"] for i in st["result"]["items"]] == ["Skoda Rapid 1.0 TSI", "Dacia Sandero"]
    assert len(calls) == 1  # one research run served both the talk and the delivery


@pytest.mark.anyio
async def test_a_buyer_who_walks_cancels_the_early_search(monkeypatch):
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def work(progress):
        started.set()
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled.set()  # the runner's own cleanup aborts the Apify run when this happens
            raise

    app, calls = seller_with(monkeypatch, work)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("d2", 0, "open"))
        await asyncio.wait_for(started.wait(), 2)
        r = (await c.post("/negotiate", json=neg("d2", 1, "walk"))).json()
        assert r["action"] == "walk"
        await asyncio.wait_for(cancelled.wait(), 2)
    assert len(calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("kw,job,mode", [({"answer_scout": False}, None, "honest"), ({}, BoundedJobSpec(count=3), "honest"),
                                        ({}, None, "junk")])
async def test_no_early_search_when_off_for_live_rentals_or_for_the_staged_junk_act(monkeypatch, kw, job, mode):
    async def work(progress):
        raise AssertionError("must not start")

    app, calls = seller_with(monkeypatch, work, apify_mode="apify", **kw)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("d3", 0, "open", job=job, mode=mode))
        await asyncio.sleep(0.1)
    assert calls == []


@pytest.mark.anyio
async def test_a_failed_early_search_falls_back_to_a_fresh_one_at_delivery(monkeypatch):
    n = []

    async def work(progress):
        n.append(1)
        if len(n) == 1:
            raise RuntimeError("scout blew up")
        return JobResult(kind="general", source="apify", answer="Two cars.", items=FOUND)

    app, calls = seller_with(monkeypatch, work)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("d4", 0, "open"))
        await asyncio.sleep(0.05)
        r1, started = await agree_and_start(c, "d4")
        assert "already" not in r1["message"]  # nothing was found, so nothing is claimed
        st = await status_of(c, started)
    assert st["status"] == "completed" and len(calls) == 2 and len(n) == 2


# ---------------- rentals: scouted for free from the cache ----------------
@pytest.mark.anyio
async def test_viktor_knows_how_many_flats_he_has_ready():
    app = create_seller(Settings(llm_mode="mock", seller_llm_mode="mock", pricing_mode="cost", apify_mode="sample"))
    job = BoundedJobSpec(count=4, district="Praha 3")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("r1", 0, "open", job=job))
        await asyncio.sleep(0.2)
        r1 = (await c.post("/negotiate", json=neg("r1", 1, "counter", offer=0.01, job=job))).json()
    assert "I have 4 flats ready, the cheapest at" in r1["message"]


# ---------------- varied speech ----------------
def test_the_ai_seller_gets_his_own_style_numbers_and_memory_without_giving_away_his_floor():
    v = CodexViktor(Settings(llm_mode="mock", pricing_mode="cost"))
    req = NegotiateRequest(deal_id="y", round=1, action="counter", offer=1, job=general("cheap laptops in Prague"))
    q = v.quote(req)
    v.said["y"] = ["Earlier line one.", "Earlier line two."]
    prompt = v._prompt(req, DealState(ask=q.opening), {"pages_read": 4, "examples": ["Lenovo V15"]})
    assert "in your own words" in prompt and "never reuse the wording of `lines_you_already_said`" in prompt
    assert "vocabulary of what is being sold" in prompt and "never state your exact cost or your floor" in prompt
    assert '"what_you_have_found_so_far": {"pages_read": 4' in prompt and "Earlier line two." in prompt
    assert f'"floor": {q.floor}' in prompt and '"your_style":' in prompt and "never invent any other fact" in prompt
    assert '"what_you_have_found_so_far":' not in v._prompt(req, DealState(ask=q.opening))


def test_viktor_gets_a_different_manner_per_deal():
    v = Viktor(pricing=Settings(pricing_mode="cost"))
    assert len({v.style(f"deal{i}") for i in range(40)}) >= 5


def test_the_buyer_prompts_are_cost_aware_and_free_in_voice():
    assert "speak freely in your own words" in " ".join(MAX_INSTRUCTIONS.lower().split())
    assert "Open around 5" in MAX_INSTRUCTIONS  # fixed pricing keeps its simple opening guidance
    for needle in ("{fair:g}", "{reservation:g}", "{opening:g}", "{style}", "never reuse the wording of lines you already said",
                   "Never invent facts about what Viktor has"):
        assert needle in MAX_COST_INSTRUCTIONS
    assert "raise your offers by amounts that fit the gap" in MAX_COST_INSTRUCTIONS and "Open around 5" not in MAX_COST_INSTRUCTIONS


# ---------------- progress while Viktor works ----------------
@pytest.mark.anyio
async def test_status_reports_real_progress_while_running_and_not_after(monkeypatch):
    gate = asyncio.Event()

    async def work(progress):
        progress.stage, progress.results_seen, progress.sites, progress.queries = "searching", 12, ["alza.cz"], ["standing desks"]
        await gate.wait()
        return JobResult(kind="general", source="apify", answer="Two cars.", items=FOUND)

    app, calls = seller_with(monkeypatch, work)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("p1", 0, "open"))
        await asyncio.sleep(0.05)
        r1, started = await agree_and_start(c, "p1")
        await asyncio.sleep(0.05)
        st = (await c.get("/status", params={"job_id": started["job_id"]})).json()
        assert st["status"] == "running" and st["result"] is None
        assert st["progress"]["stage"] == "searching" and st["progress"]["results_seen"] == 12 and st["progress"]["sites"] == ["alza.cz"]
        gate.set()
        done = await status_of(c, started)
    assert done["status"] == "completed" and done["progress"] is None


@pytest.mark.anyio
async def test_research_does_not_wait_out_the_simulated_work_time_and_unscouted_jobs_still_report_progress(monkeypatch):
    import app.seller.app as seller_module

    async def work(progress):
        progress.stage, progress.pages_read = "reading", 4
        await asyncio.sleep(0.05)
        return JobResult(kind="general", source="apify", answer="Two cars.", items=FOUND)

    app, calls = seller_with(monkeypatch, work, answer_scout=False)
    monkeypatch.setattr(seller_module, "JOB_SECONDS", 30)  # a rental-style fake wait would make this test time out
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("p2", 0, "open"))
        r1, started = await agree_and_start(c, "p2")
        await asyncio.sleep(0.02)
        mid = (await c.get("/status", params={"job_id": started["job_id"]})).json()
        assert mid["progress"] is not None and mid["progress"]["pages_read"] == 4
        done = await asyncio.wait_for(status_of(c, started), 5)
    assert done["status"] == "completed" and len(calls) == 1


@pytest.mark.anyio
async def test_the_buyer_relays_progress_as_clean_deduplicated_events_before_the_delivery(monkeypatch, tmp_path):
    import app.seller.job as job_module
    from app.buyer.app import create_app as create_buyer

    async def work(progress):
        progress.stage, progress.results_seen = "searching", 7
        await asyncio.sleep(0.15)
        progress.stage, progress.pages_read, progress.reads_total, progress.sites = "reading", 3, 8, ["alza.cz", "kaufland.cz"]
        await asyncio.sleep(0.15)
        return JobResult(kind="general", source="apify", answer="Two cars found for you.", items=FOUND)

    seller_app, _ = seller_with(monkeypatch, work)
    monkeypatch.setattr(job_module, "answer_result", lambda *a, **k: work(a[2] if len(a) > 2 else k.get("progress")))
    s = Settings(ledger_path=str(tmp_path / "b.db"), audio_dir=str(tmp_path / "a"), seller_url="http://seller", answer_mode="codex",
                 llm_mode="mock", seller_llm_mode="mock", pricing_mode="cost")
    seller_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=seller_app), base_url="http://seller")
    buyer = create_buyer(s, http=seller_http)
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            q = "Find me 2 used cars in Prague"
            parsed = (await c.post("/requests/parse", json={"text": q})).json()
            await c.post("/tasks", json={"text": q, "job": parsed["job"], "demo_mode": "honest"})
            for _ in range(600):
                if {"released", "refunded", "error"} & {e.type for e in buyer.state.bus.history}:
                    break
                await asyncio.sleep(0.01)
    await seller_http.aclose()
    events = buyer.state.bus.history
    types = [e.type for e in events]
    progress = [e for e in events if e.type == "job_progress"]
    assert progress and types.index("job_progress") > types.index("escrow_locked") and types.index("job_progress") < types.index("delivered")
    assert len({str(e.data) for e in progress}) == len(progress)  # an unchanged report is not repeated
    assert any(e.data["stage"] == "reading" and e.data["pages_read"] == 3 and e.data["sites"] == ["alza.cz", "kaufland.cz"] for e in progress)


def test_progress_from_the_seller_is_cleaned_before_it_reaches_the_dashboard():
    from app.buyer.orchestrator import Orchestrator

    clean = Orchestrator._clean_progress
    assert clean(None) is None and clean("x") is None and clean([1]) is None
    got = clean({"stage": "<script>", "queries": ["a" * 500, 5, "b", "c", "d", "e"], "results_seen": -3, "sites": ["x"] * 20,
                 "pages_done": True, "pages_total": 10**9, "pages_read": "7", "reads_total": 8, "options_found": 2.5, "evil": "<img onerror=1>"})
    assert got["stage"] == "starting" and len(got["queries"]) == 4 and len(got["queries"][0]) == 80 and len(got["sites"]) == 5
    assert (got["results_seen"], got["pages_done"], got["pages_total"], got["pages_read"], got["options_found"]) == (0, 0, 0, 0, 0)
    assert got["reads_total"] == 8 and "evil" not in got


@pytest.mark.anyio
async def test_an_early_search_that_found_nothing_is_not_run_a_second_time(monkeypatch):
    n = []

    async def work(progress):
        n.append(1)
        raise ValueError("The research found nothing that matches the request")

    app, calls = seller_with(monkeypatch, work)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("n1", 0, "open"))
        await asyncio.sleep(0.05)
        r1, started = await agree_and_start(c, "n1")
        st = await status_of(c, started)
    assert st["status"] == "failed" and len(n) == 1  # one attempt: repeating it would only double the wait and the cost


@pytest.mark.anyio
async def test_an_early_search_that_fails_is_logged_not_swallowed(monkeypatch, caplog):
    async def work(progress):
        raise RuntimeError("Apify request failed (TimeoutError)")

    app, calls = seller_with(monkeypatch, work)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        with caplog.at_level("WARNING", logger="astra.seller"):
            await c.post("/negotiate", json=neg("l1", 0, "open"))
            await asyncio.sleep(0.1)
    assert any("early work for deal l1 failed: RuntimeError: Apify request failed (TimeoutError)" in r.message for r in caplog.records)


def test_max_is_told_to_speak_freely_and_react_to_what_viktor_really_says():
    normalized = " ".join(MAX_INSTRUCTIONS.lower().split())
    assert "speak freely in your own words" in normalized and "any number of options he says he already has" in normalized
    assert "Never invent facts about what Viktor has" in MAX_INSTRUCTIONS
