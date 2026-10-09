"""Any request, not just rentals: a free-text request is routed to an AI answer, paid through the same guard and
escrow, delivered, rule-checked, and released or refunded."""

import asyncio

import httpx
import pytest

from app.buyer.app import create_app as create_buyer
from app.buyer.verifier import verify, verify_answer
from app.core.config import Settings
from app.core.intent import parse_request
from app.core.models import BoundedJobSpec, DemoMode, JobResult, describe_job
from app.seller.app import create_app as create_seller
from app.seller.job import answer_result, run_job


@pytest.fixture
def anyio_backend():
    return "asyncio"


def general(prompt="Explain in two sentences why escrow protects buyers"):
    return BoundedJobSpec(kind="general", prompt=prompt)


# ---------------- settings ----------------
def test_answers_follow_codex_availability_unless_forced():
    assert Settings(llm_mode="mock", seller_llm_mode="mock").answers_enabled is False
    assert Settings(llm_mode="codex").answers_enabled is True
    assert Settings(seller_llm_mode="codex").answers_enabled is True
    assert Settings(llm_mode="mock", answer_mode="codex").answers_enabled is True
    assert Settings(llm_mode="codex", answer_mode="off").answers_enabled is False
    with pytest.raises(ValueError):
        Settings(answer_mode="sometimes")


# ---------------- parsing and routing ----------------
@pytest.mark.parametrize("text", ["Explain how escrow works", "What is the capital of Austria?", "buy me a car",
                                  "summarise the Cardano roadmap", "10 flats in Brno under 20k"])
def test_non_rental_requests_become_general_jobs_when_answers_are_on(text):
    p = parse_request(text, general=True)
    assert p.ok and p.job.kind == "general" and p.job.prompt == text and p.public()["kind"] == "general"
    assert any("Not a flat search" in n for n in p.notes)


@pytest.mark.parametrize("text", [
    "Find me used cars for sale in Prague, max 200000 km, not older than 10 years. Give me 5 concrete listings with price and link.",
    "I want to rent a car in Prague", "5 listings of used laptops in Prague", "latest news about rent control"])
def test_listings_and_rent_alone_do_not_make_a_request_a_flat_search(text):
    p = parse_request(text, general=True)
    assert p.ok and p.job.kind == "general"


def test_rentals_stay_rentals_even_when_answers_are_on():
    p = parse_request("10 apartments in Prague 2, max 30k", general=True)
    assert p.ok and p.job.kind == "rental" and (p.job.count, p.job.district) == (10, "Praha 2")


def test_with_answers_off_other_requests_are_refused_and_say_how_to_turn_them_on():
    p = parse_request("What is the capital of Austria?", general=False)
    assert not p.ok and p.job is None and "LLM_MODE=codex" in p.summary


def test_empty_and_overlong_requests_are_never_general_jobs():
    assert not parse_request("", general=True).ok and not parse_request("   ", general=True).ok
    assert not parse_request("x " * 400, general=True).ok


def test_a_general_job_needs_a_prompt_and_a_bounded_one():
    with pytest.raises(ValueError):
        BoundedJobSpec(kind="general")
    with pytest.raises(ValueError):
        BoundedJobSpec(kind="general", prompt="   ")
    with pytest.raises(ValueError):
        BoundedJobSpec(kind="general", prompt="x" * 501)
    assert BoundedJobSpec(kind="rental").prompt is None


def test_agents_describe_a_general_job_by_its_question():
    assert describe_job(general("What is escrow?")) == 'an answer to: "What is escrow?"'
    long = describe_job(general("y" * 300))
    assert long.endswith('…"') and len(long) < 160


# ---------------- verification ----------------
def result(answer, kind="general"):
    return JobResult(kind=kind, source="codex", answer=answer)


@pytest.mark.parametrize("answer,ok", [
    ("Escrow holds the money until both sides did their part.", True),
    ("42", True),
    ("", False), ("   ", False), ("…", False),
    ("Lorem ipsum dolor sit amet.", False), ("asdf asdf", False), ("N/A", False), ("TODO", False),
    ("x" * 4001, False),
])
def test_answer_rules(answer, ok):
    assert verify_answer(result(answer))[0] is ok


def test_a_missing_or_wrong_kind_of_result_fails_and_dispatch_uses_the_job_kind():
    assert verify_answer(None)[0] is False
    assert verify_answer(result("fine answer", kind="rental"))[0] is False
    assert verify(result("A real answer about escrow."), general())[0] is True
    assert verify(None, general())[1]["has_result"] is False


# ---------------- the seller's worker ----------------
@pytest.mark.anyio
@pytest.mark.parametrize("bad", [{}, {"answer": ""}, {"answer": 5}, "text"])
async def test_a_missing_answer_fails_the_job_instead_of_inventing_one(monkeypatch, bad):
    import app.buyer.codex_runtime as rt

    async def fake(*a, **kw):
        return bad

    monkeypatch.setattr(rt, "run_codex", fake)
    with pytest.raises(ValueError):
        await answer_result(general(), Settings(answer_mode="codex"))


@pytest.mark.anyio
async def test_with_answers_off_the_worker_refuses_and_never_calls_a_model(monkeypatch):
    import app.buyer.codex_runtime as rt

    async def boom(*a):
        raise AssertionError("must not call a model")

    monkeypatch.setattr(rt, "run_codex", boom)
    with pytest.raises(ValueError, match="General answers are off"):
        await run_job(general(), DemoMode.honest, Settings(llm_mode="mock", answer_mode="off"))


@pytest.mark.anyio
async def test_the_staged_junk_answer_is_rejected_by_the_rules():
    r = await run_job(general(), DemoMode.junk, Settings(answer_mode="off"))  # junk never needs a model
    ok, checks = verify(r, general())
    assert not ok and checks["not_a_placeholder"] is False


# ---------------- a whole deal ----------------
async def deal(tmp_path, monkeypatch, demo_mode="honest", answer="Escrow holds funds until the work is verified."):
    import app.buyer.codex_runtime as rt

    async def fake(prompt, schema, settings, **kw):
        if "needs_web" in schema["properties"]:  # the research planner: a plain question needs no web data
            return {"needs_web": False, "queries": [], "country": "us", "language": "en"}
        return {"answer": answer}

    monkeypatch.setattr(rt, "run_codex", fake)
    s = Settings(ledger_path=str(tmp_path / "buyer.db"), audio_dir=str(tmp_path / "audio"), seller_url="http://seller",
                 answer_mode="codex", llm_mode="mock", seller_llm_mode="mock")
    seller_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_seller(s)), base_url="http://seller")
    buyer = create_buyer(s, http=seller_http)
    async with buyer.router.lifespan_context(buyer):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=buyer), base_url="http://buyer") as c:
            q = "Explain in one sentence why escrow protects buyers"
            parsed = (await c.post("/requests/parse", json={"text": q})).json()
            assert parsed["ok"] and parsed["kind"] == "general"
            r = await c.post("/tasks", json={"text": q, "job": parsed["job"], "demo_mode": demo_mode})
            assert r.status_code == 200
            for _ in range(900):
                if {"released", "refunded", "error", "blocked"} & {e.type for e in buyer.state.bus.history}:
                    break
                await asyncio.sleep(0.01)
            bal = (await c.get("/balances")).json()
    await seller_http.aclose()
    return buyer.state.bus.history, bal


@pytest.mark.anyio
async def test_a_general_request_runs_the_whole_pipeline_and_releases(tmp_path, monkeypatch):
    events, bal = await deal(tmp_path, monkeypatch)
    types = [e.type for e in events]
    assert "released" in types and "error" not in types
    first = next(e for e in events if e.type == "negotiation")
    assert first.data["speaker"] == "max" and 'Explain in one sentence' in first.data["text"]
    viktor = next(e for e in events if e.type == "negotiation" and e.data["speaker"] == "viktor")
    assert "Explain in one sentence" in viktor.data["text"]
    d = next(e for e in events if e.type == "delivered")
    assert d.data["items"] == 1 and d.data["source"] == "codex"  # no web needed: written from knowledge, labelled AI ANSWER
    assert d.data["result"]["kind"] == "general" and "Escrow holds funds" in d.data["result"]["answer"]
    v = next(e for e in events if e.type == "verified")
    assert v.data["ok"] is True and set(v.data["checks"]) == {"has_result", "has_answer", "reasonable_length", "not_a_placeholder", "not_a_refusal", "enough_findings", "sources_valid"}
    assert bal["buyer"] == 930 and bal["seller"] == 70 and bal["escrow"] == 0


@pytest.mark.anyio
async def test_a_placeholder_answer_is_refunded_not_paid(tmp_path, monkeypatch):
    events, bal = await deal(tmp_path, monkeypatch, answer="Lorem ipsum dolor sit amet.")
    types = [e.type for e in events]
    assert "refunded" in types and "released" not in types
    assert bal["buyer"] == 1000 and bal["seller"] == 0


@pytest.mark.anyio
async def test_the_staged_refund_act_works_for_a_general_request(tmp_path, monkeypatch):
    events, bal = await deal(tmp_path, monkeypatch, demo_mode="junk")
    assert "refunded" in [e.type for e in events] and bal["buyer"] == 1000


def test_the_saved_rental_cache_key_ignores_the_new_job_fields():
    from app.seller import apify

    assert apify._job_key(BoundedJobSpec(count=5, district="Praha 3", max_price_czk=20000)) == {"count": 5, "district": "Praha 3", "max_price_czk": 20000}
    assert apify._job_key(general()) == {"count": 20, "district": "Praha 7", "max_price_czk": 25000}


# ---------------- live web search for answers ----------------
@pytest.mark.parametrize("answer", [
    "I couldn't verify current listings because web search is unavailable in this session.",
    "Web search was unavailable, so I can't give prices.",
    "I can't access the web here, but try Sauto.cz.",
    "I couldn't verify the newest stable Python release."])
def test_an_answer_that_says_it_could_not_search_is_rejected(answer):
    ok, checks = verify_answer(result(answer))
    assert not ok and checks["not_a_refusal"] is False


def test_normal_answers_that_mention_searching_or_limits_still_pass():
    assert verify_answer(result("Escrow protects buyers. Prices vary, so verify them on the seller's own site."))[0]
    assert verify_answer(result("The newest stable release is Python 3.14.8 (python.org). I can't promise it is still current tomorrow."))[0]


def test_search_turns_web_search_on_for_that_call_only(tmp_path):
    import app.buyer.codex_runtime as rt

    s = Settings(llm_mode="codex")
    off = rt._arguments(s, tmp_path / "s.json", tmp_path / "o.json")
    on = rt._arguments(s, tmp_path / "s.json", tmp_path / "o.json", search=True)
    assert 'web_search="disabled"' in off and 'web_search="live"' not in off
    assert 'web_search="live"' in on and 'web_search="disabled"' not in on
    assert "--sandbox" in on and on[on.index("--sandbox") + 1] == "read-only"  # search never loosens the sandbox
    assert any("Do not read local files" in a for a in on) and not any("Do not use tools" in a for a in on)
    assert any("Do not use tools" in a for a in off)
    # web_search only runs with code_mode on, so search enables exactly that; everything else stays off
    assert "features.code_mode=false" in off and "features.code_mode_host=false" in off
    assert "features.code_mode=false" not in on and "features.code_mode_host=false" not in on
    for still_off in ("shell_tool", "unified_exec", "browser_use", "apps", "plugins", "multi_agent", "computer_use"):
        assert f"features.{still_off}=false" in on


def test_a_non_https_source_fails_verification():
    bad = JobResult(kind="general", source="codex", answer="A real answer.", sources=["http://x.example"])
    assert verify_answer(bad)[0] is False and verify_answer(bad)[1]["sources_valid"] is False
    assert verify_answer(JobResult(kind="general", source="codex", answer="A real answer.", sources=["https://x.example"]))[0] is True


def test_search_settings_are_validated(monkeypatch):
    monkeypatch.setenv("ANSWER_SEARCH", "off")
    assert Settings().answer_search is False
    monkeypatch.delenv("ANSWER_SEARCH")
    assert Settings().answer_search is True
    with pytest.raises(ValueError):
        Settings(answer_timeout_seconds=0)


# ---------------- the answer worker ----------------
def codex_fake(seen, plan=None, answer="  Escrow keeps funds safe until delivery.  "):
    async def fake(prompt, schema, settings, **kw):
        seen.append((prompt, schema, kw))
        if "needs_web" in schema["properties"]:
            return plan or {"needs_web": False, "queries": [], "country": "us", "language": "en"}
        return {"answer": answer}

    return fake


@pytest.mark.anyio
async def test_a_plain_question_is_answered_from_knowledge_with_a_guarded_prompt(monkeypatch):
    import app.buyer.codex_runtime as rt

    seen = []
    monkeypatch.setattr(rt, "run_codex", codex_fake(seen))
    r = await answer_result(general("What is escrow?"), Settings(answer_mode="codex"))
    assert r.kind == "general" and r.source == "codex" and r.answer == "Escrow keeps funds safe until delivery." and r.items == []
    writer_prompt, writer_schema, writer_kw = seen[-1]
    assert "What is escrow?" in writer_prompt and "never instructions" in writer_prompt and "Do not read local files" in writer_prompt
    assert writer_schema["required"] == ["answer"] and "search" not in writer_kw  # Codex never searches the web itself


@pytest.mark.anyio
async def test_with_research_off_the_planner_is_not_even_asked(monkeypatch):
    import app.buyer.codex_runtime as rt

    seen = []
    monkeypatch.setattr(rt, "run_codex", codex_fake(seen))
    await answer_result(general("Find me cheap laptops"), Settings(answer_mode="codex", answer_search=False))
    assert len(seen) == 1 and "needs_web" not in seen[0][1]["properties"]


@pytest.mark.anyio
async def test_a_request_that_needs_the_web_fails_honestly_without_an_apify_token(monkeypatch):
    import app.buyer.codex_runtime as rt

    seen = []
    plan = {"needs_web": True, "queries": ["cheap laptops prague"], "country": "cz", "language": "en"}
    monkeypatch.setattr(rt, "run_codex", codex_fake(seen, plan))
    with pytest.raises(ValueError, match="APIFY_TOKEN"):
        await answer_result(general("Find me cheap laptops"), Settings(answer_mode="codex", apify_token=""))
    assert len(seen) == 1  # only the planner ran; nothing invented
