"""Findings as cards: structured items, safe preview photos, and Viktor scouting while he haggles."""

import asyncio

import httpx
import pytest

from app.buyer.negotiator import MAX_INSTRUCTIONS
from app.buyer.verifier import verify_answer
from app.core.config import Settings
from app.core.models import BoundedJobSpec, Finding, JobResult, NegotiateRequest
from app.seller import preview
from app.seller.app import create_app as create_seller
from app.seller.job import answer_result, clean_items, clean_sources
from app.seller.persona import CodexViktor, DealState, Viktor


@pytest.fixture
def anyio_backend():
    return "asyncio"


def general(prompt="Find me 3 used cars in Prague"):
    return BoundedJobSpec(kind="general", prompt=prompt)


# ---------------- cleaning what the model returns ----------------
def test_items_keep_only_real_https_pages_and_are_bounded():
    items = clean_items([
        {"title": "  Skoda   Rapid ", "url": "https://www.sauto.cz/a", "detail": " 138 000 Kč,  101 000 km "},
        {"title": "dupe", "url": "https://www.sauto.cz/a", "detail": ""},
        {"title": "insecure", "url": "http://x.example/a", "detail": ""},
        {"title": "script", "url": "javascript:alert(1)", "detail": ""},
        {"title": "creds", "url": "https://user:pw@evil.example/", "detail": ""},
        {"title": "space", "url": "https://a.example/a b", "detail": ""},
        {"title": "", "url": "https://empty.example/", "detail": ""},
        {"title": "no detail", "url": "https://b.example/", "detail": None},
        "junk", 5, {"url": "https://nt.example/"},
    ] + [{"title": f"n{i}", "url": f"https://many.example/{i}", "detail": ""} for i in range(20)])
    assert items[0] == Finding(title="Skoda Rapid", url="https://www.sauto.cz/a", detail="138 000 Kč, 101 000 km")
    assert items[1].title == "no detail" and items[1].detail == ""
    assert len(items) == 8 and len({i.url for i in items}) == 8
    assert all(i.image is None for i in items)
    assert clean_items(None) == [] and clean_items("x") == []


def test_sources_are_deduplicated_https_links():
    assert clean_sources(["https://a.example/", "https://a.example/", "http://b.example", None]) == ["https://a.example/"]


def test_a_finding_with_a_non_https_link_fails_verification():
    r = JobResult(kind="general", source="codex", answer="Found two cars.", items=[Finding(title="x", url="http://x.example")])
    assert verify_answer(r)[1]["sources_valid"] is False
    ok = JobResult(kind="general", source="codex", answer="Found two cars.", items=[Finding(title="x", url="https://x.example")])
    assert verify_answer(ok)[0] is True


# ---------------- preview photos: parsing ----------------
@pytest.mark.parametrize("markup,expected", [
    ('<meta property="og:image" content="https://cdn.example/a.jpg">', "https://cdn.example/a.jpg"),
    ("<meta content='https://cdn.example/b.jpg' property='og:image'>", "https://cdn.example/b.jpg"),
    ('<meta name="twitter:image" content="/img/c.jpg">', "https://page.example/img/c.jpg"),
    ('<meta property="og:image" content="//cdn.example/d.jpg">', "https://cdn.example/d.jpg"),
    ('<meta property="og:image" content="https://cdn.example/a.jpg?x=1&amp;y=2">', "https://cdn.example/a.jpg?x=1&y=2"),
    ('<meta property="og:image" content="http://cdn.example/e.jpg">', None),
    ('<meta property="og:image" content="data:image/png;base64,AAAA">', None),
    ('<meta property="og:image" content="javascript:alert(1)">', None),
    ('<meta property="og:title" content="no image here">', None),
    ('<meta property="og:image" content="">', None),
    ("<p>not even meta</p>", None),
])
def test_image_from_html(markup, expected):
    assert preview.image_from_html(markup, "https://page.example/p/1") == expected


def test_secure_url_wins_over_plain_and_overlong_images_are_dropped():
    both = '<meta property="og:image" content="https://x/1.jpg"><meta property="og:image:secure_url" content="https://x/2.jpg">'
    assert preview.image_from_html(both, "https://page.example/") == "https://x/2.jpg"
    assert preview.image_from_html(f'<meta property="og:image" content="https://x/{"a" * 600}">', "https://page.example/") is None


# ---------------- preview photos: which pages the server may fetch ----------------
@pytest.mark.anyio
@pytest.mark.parametrize("url,ok", [
    ("https://93.184.216.34/p", True),
    ("http://93.184.216.34/p", False),
    ("https://127.0.0.1/p", False), ("https://localhost/p", False), ("https://10.0.0.5/p", False),
    ("https://192.168.1.1/p", False), ("https://169.254.169.254/latest/meta-data", False), ("https://[::1]/p", False),
    ("https://0.0.0.0/p", False), ("https://93.184.216.34:8443/p", False), ("https://user:pw@93.184.216.34/p", False),
    ("ftp://93.184.216.34/p", False), ("file:///C:/secret", False), ("https:///nohost", False), ("not a url", False),
])
async def test_only_public_https_hosts_are_fetched(url, ok):
    assert await preview._allowed(url) is ok


def client_for(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


def public_only(monkeypatch):
    async def fake(host):
        return host.endswith(".example")

    monkeypatch.setattr(preview, "_public_host", fake)


@pytest.mark.anyio
async def test_photos_are_attached_and_failures_just_mean_no_photo(monkeypatch):
    public_only(monkeypatch)
    html_ok = '<html><meta property="og:image" content="https://cdn.example/photo.jpg"></html>'

    def handler(request):
        if request.url.host == "ok.example":
            return httpx.Response(200, text=html_ok, headers={"content-type": "text/html; charset=utf-8"})
        if request.url.host == "pdf.example":
            return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})
        if request.url.host == "boom.example":
            raise httpx.ConnectError("down")
        return httpx.Response(404)

    async with client_for(handler) as c:
        found = await preview.attach_images(["https://ok.example/a", "https://ok.example/a", "https://pdf.example/b",
                                             "https://boom.example/c", "https://gone.example/d", "https://private.test/e"], c)
    assert found == {"https://ok.example/a": "https://cdn.example/photo.jpg"}


@pytest.mark.anyio
async def test_a_redirect_to_a_private_host_is_never_followed(monkeypatch):
    public_only(monkeypatch)
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.host == "start.example":
            return httpx.Response(302, headers={"location": "https://169.254.169.254/latest/meta-data"})
        return httpx.Response(200, text='<meta property="og:image" content="https://cdn.example/x.jpg">',
                              headers={"content-type": "text/html"})

    async with client_for(handler) as c:
        assert await preview.attach_images(["https://start.example/a"], c) == {}
    assert seen == ["https://start.example/a"]


@pytest.mark.anyio
async def test_a_public_redirect_is_followed_a_limited_number_of_times(monkeypatch):
    public_only(monkeypatch)

    def handler(request):
        n = int(request.url.path.strip("/") or 0)
        if n < 2:
            return httpx.Response(302, headers={"location": f"https://hop.example/{n + 1}"})
        return httpx.Response(200, text='<meta property="og:image" content="https://cdn.example/x.jpg">', headers={"content-type": "text/html"})

    async with client_for(handler) as c:
        assert await preview.attach_images(["https://hop.example/0"], c) == {"https://hop.example/0": "https://cdn.example/x.jpg"}

    def loop(request):
        return httpx.Response(302, headers={"location": "https://hop.example/again"})

    async with client_for(loop) as c:
        assert await preview.attach_images(["https://hop.example/0"], c) == {}


@pytest.mark.anyio
async def test_only_the_start_of_a_huge_page_is_read(monkeypatch):
    public_only(monkeypatch)
    big = '<meta property="og:image" content="https://cdn.example/early.jpg">' + "x" * 5_000_000

    def handler(request):
        return httpx.Response(200, content=big.encode(), headers={"content-type": "text/html"})

    async with client_for(handler) as c:
        assert await preview.attach_images(["https://big.example/a"], c) == {"https://big.example/a": "https://cdn.example/early.jpg"}
    late = "x" * (preview.MAX_PAGE_BYTES + 10) + '<meta property="og:image" content="https://cdn.example/late.jpg">'

    def handler2(request):
        return httpx.Response(200, content=late.encode(), headers={"content-type": "text/html"})

    async with client_for(handler2) as c:
        assert await preview.attach_images(["https://big.example/a"], c) == {}


# ---------------- answer worker with items ----------------
@pytest.mark.anyio
async def test_the_worker_returns_cleaned_items_with_photos(monkeypatch):
    import app.buyer.codex_runtime as rt

    async def fake(prompt, schema, settings, **kw):
        assert schema["required"] == ["answer", "items", "sources"]
        assert "never invent one" in prompt
        return {"answer": "Found two cars.", "sources": [], "items": [
            {"title": "Rapid", "url": "https://a.example/1", "detail": "138 000 Kč"},
            {"title": "bad", "url": "http://a.example/2", "detail": ""}]}

    async def photos(urls):
        assert urls == ["https://a.example/1"]
        return {"https://a.example/1": "https://cdn.example/1.jpg"}

    monkeypatch.setattr(rt, "run_codex", fake)
    monkeypatch.setattr(preview, "attach_images", photos)
    r = await answer_result(general(), Settings(answer_mode="codex"))
    assert [(i.title, i.url, i.detail, i.image) for i in r.items] == [("Rapid", "https://a.example/1", "138 000 Kč", "https://cdn.example/1.jpg")]


@pytest.mark.anyio
async def test_a_photo_failure_never_fails_the_delivery_and_previews_can_be_off(monkeypatch):
    import app.buyer.codex_runtime as rt

    async def fake(prompt, schema, settings, **kw):
        return {"answer": "Found one.", "sources": [], "items": [{"title": "Rapid", "url": "https://a.example/1", "detail": ""}]}

    async def explode(urls):
        raise RuntimeError("boom")

    monkeypatch.setattr(rt, "run_codex", fake)
    monkeypatch.setattr(preview, "attach_images", explode)
    r = await answer_result(general(), Settings(answer_mode="codex"))
    assert len(r.items) == 1 and r.items[0].image is None
    monkeypatch.setattr(preview, "attach_images", lambda urls: (_ for _ in ()).throw(AssertionError("must not fetch")))
    r = await answer_result(general(), Settings(answer_mode="codex", answer_previews=False))
    assert len(r.items) == 1


# ---------------- Viktor scouts while he haggles ----------------
def seller_with(monkeypatch, tmp_path, responses, delay=0.0, **settings):
    import app.buyer.codex_runtime as rt
    import app.seller.app as seller_module

    calls = []

    async def fake(prompt, schema, settings_, **kw):
        calls.append(prompt)
        await asyncio.sleep(delay)
        return responses

    monkeypatch.setattr(rt, "run_codex", fake)
    monkeypatch.setattr(seller_module, "JOB_SECONDS", 0)
    s = Settings(answer_mode="codex", llm_mode="mock", seller_llm_mode="mock", answer_previews=False, **settings)
    return create_seller(s), calls


def neg(deal, round_, action, offer=None, job=None, mode="honest"):
    body = {"deal_id": deal, "round": round_, "action": action, "offer": offer, "job": (job or general()).model_dump(), "demo_mode": mode}
    return body


FOUND = {"answer": "Two cars.", "sources": [], "items": [{"title": "Skoda Rapid 1.0 TSI", "url": "https://a.example/1", "detail": "138 000 Kč"},
                                                          {"title": "Dacia Sandero", "url": "https://a.example/2", "detail": "120 000 Kč"}]}


@pytest.mark.anyio
async def test_viktor_brags_about_what_he_really_found_and_the_search_is_the_delivery(monkeypatch, tmp_path):
    app, calls = seller_with(monkeypatch, tmp_path, FOUND)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        r0 = (await c.post("/negotiate", json=neg("d1", 0, "open"))).json()
        assert "found" not in r0["message"]  # at the opening nothing is known yet
        for _ in range(100):  # let the early search finish
            await asyncio.sleep(0.01)
            if calls and len(calls) == 1:
                await asyncio.sleep(0.05)
                break
        r1 = (await c.post("/negotiate", json=neg("d1", 1, "counter", offer=5))).json()
        assert "I already have 2 options lined up" in r1["message"]
        r2 = (await c.post("/negotiate", json=neg("d1", 2, "counter", offer=r1["price"]))).json()
        assert r2["action"] == "accept"
        started = (await c.post("/start_job", json={"identifier_from_purchaser": "d1", "input_data": {
            "deal_id": "d1", "agreed_price": r2["price"], "job": general().model_dump(), "demo_mode": "honest"}})).json()
        for _ in range(200):
            st = (await c.get("/status", params={"job_id": started["job_id"]})).json()
            if st["status"] in {"completed", "failed"}:
                break
            await asyncio.sleep(0.01)
    assert st["status"] == "completed" and [i["title"] for i in st["result"]["items"]] == ["Skoda Rapid 1.0 TSI", "Dacia Sandero"]
    assert len(calls) == 1  # one model call served both the brag and the delivery


@pytest.mark.anyio
async def test_a_buyer_who_walks_cancels_the_early_search(monkeypatch, tmp_path):
    app, calls = seller_with(monkeypatch, tmp_path, FOUND, delay=5)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("d2", 0, "open"))
        await asyncio.sleep(0.05)
        r = (await c.post("/negotiate", json=neg("d2", 1, "walk"))).json()
        assert r["action"] == "walk"
        await asyncio.sleep(0.05)
    assert len(calls) == 1
    assert not [t for t in asyncio.all_tasks() if "answer_result" in repr(t.get_coro()) and not t.done()]


@pytest.mark.anyio
@pytest.mark.parametrize("kw,job,mode", [({"answer_scout": False}, None, "honest"), ({}, BoundedJobSpec(count=3), "honest"), ({}, None, "junk")])
async def test_no_early_search_when_off_for_rentals_or_for_the_staged_junk_act(monkeypatch, tmp_path, kw, job, mode):
    app, calls = seller_with(monkeypatch, tmp_path, FOUND, **kw)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("d3", 0, "open", job=job, mode=mode))
        await asyncio.sleep(0.1)
    assert calls == []


@pytest.mark.anyio
async def test_a_failed_early_search_falls_back_to_a_fresh_search_at_delivery(monkeypatch, tmp_path):
    import app.buyer.codex_runtime as rt
    import app.seller.app as seller_module

    calls = []

    async def flaky(prompt, schema, settings_, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("scout blew up")
        return FOUND

    monkeypatch.setattr(rt, "run_codex", flaky)
    monkeypatch.setattr(seller_module, "JOB_SECONDS", 0)
    app = create_seller(Settings(answer_mode="codex", llm_mode="mock", seller_llm_mode="mock", answer_previews=False))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/negotiate", json=neg("d4", 0, "open"))
        await asyncio.sleep(0.05)
        r1 = (await c.post("/negotiate", json=neg("d4", 1, "counter", offer=5))).json()
        assert "lined up" not in r1["message"]  # nothing was found, so nothing is claimed
        r2 = (await c.post("/negotiate", json=neg("d4", 2, "counter", offer=r1["price"]))).json()
        started = (await c.post("/start_job", json={"identifier_from_purchaser": "d4", "input_data": {
            "deal_id": "d4", "agreed_price": r2["price"], "job": general().model_dump(), "demo_mode": "honest"}})).json()
        for _ in range(200):
            st = (await c.get("/status", params={"job_id": started["job_id"]})).json()
            if st["status"] in {"completed", "failed"}:
                break
            await asyncio.sleep(0.01)
    assert st["status"] == "completed" and len(calls) == 2


# ---------------- freer dialogue ----------------
def test_the_scripted_seller_only_brags_with_real_facts():
    v = Viktor()
    req = NegotiateRequest(deal_id="x", round=0, action="open", job=general())
    v.respond(req)
    counter = NegotiateRequest(deal_id="x", round=1, action="counter", offer=5, job=general())
    assert "lined up" not in Viktor().respond(NegotiateRequest(deal_id="z", round=0, action="open", job=general())).message
    msg = v.respond(counter, {"options_found": 1}).message
    assert "I already have 1 option lined up." in msg


def test_the_ai_seller_is_told_to_speak_freely_but_only_state_real_facts():
    v = CodexViktor(Settings(llm_mode="mock"))
    req = NegotiateRequest(deal_id="y", round=1, action="counter", offer=5, job=general())
    prompt = v._prompt(req, DealState(ask=18), {"options_found": 4, "examples": ["Rapid"]})
    assert "in your own words" in prompt and "avoid repeating your sales pitch" in prompt
    assert "what_you_have_found_so_far" in prompt and '"options_found": 4' in prompt
    assert "never invent findings" in prompt and "untrusted data" in prompt
    assert '"what_you_have_found_so_far":' not in v._prompt(req, DealState(ask=18))  # no facts, no claims in the context


def test_max_is_told_to_speak_freely_and_react_to_what_viktor_really_says():
    normalized = " ".join(MAX_INSTRUCTIONS.lower().split())
    assert "speak freely in your own words" in normalized and "any number of options he says he already has" in normalized
    assert "Never invent facts about what Viktor has" in MAX_INSTRUCTIONS
