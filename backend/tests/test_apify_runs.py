"""The generic Apify runner: bounded, streams its dataset while running, aborts on timeout, leaks nothing."""

import json

import httpx
import pytest

from app.core.config import Settings
from app.seller import apify_runs
from app.seller.apify import API, ApifyError
from app.seller.apify_runs import run_actor

S = Settings(apify_token="test-token-value")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    monkeypatch.setattr(apify_runs, "POLL_SECONDS", 0)


class Fake:
    """A scripted Apify: the run goes RUNNING for `polls` polls, then ends; the dataset grows as it runs."""

    def __init__(self, batches, polls=2, final="SUCCEEDED", usage=0.0123, run_id="RUN1", dataset="DS1", fail_items=False):
        self.batches, self.polls, self.final, self.usage = batches, polls, final, usage
        self.run_id, self.dataset, self.fail_items = run_id, dataset, fail_items
        self.seen_polls = 0
        self.requests: list[httpx.Request] = []
        self.aborted = False
        self.items: list = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/v2")
        if request.method == "POST" and path.endswith("/runs"):
            return httpx.Response(201, json={"data": {"id": self.run_id, "status": "READY", "defaultDatasetId": self.dataset}})
        if request.method == "POST" and path.endswith("/abort"):
            self.aborted = True
            return httpx.Response(200, json={"data": {}})
        if path == f"/actor-runs/{self.run_id}":
            self.seen_polls += 1
            if self.seen_polls <= len(self.batches):
                self.items.extend(self.batches[self.seen_polls - 1])
            done = self.seen_polls > self.polls
            return httpx.Response(200, json={"data": {"id": self.run_id, "status": self.final if done else "RUNNING",
                                                      "defaultDatasetId": self.dataset, "usageTotalUsd": self.usage}})
        if path == f"/datasets/{self.dataset}/items":
            if self.fail_items:
                return httpx.Response(500, text="secret internals test-token-value")
            offset = int(request.url.params.get("offset", 0))
            return httpx.Response(200, json=self.items[offset:])
        return httpx.Response(404)


def client(fake):
    return httpx.AsyncClient(base_url=API, transport=httpx.MockTransport(fake.handler))


async def go(fake, **kw):
    async with client(fake) as c:
        return await run_actor(S, kw.pop("actor", "apify/google-search-scraper"), kw.pop("payload", {"queries": "x"}),
                               max_charge_usd=kw.pop("cap", 0.5), timeout=kw.pop("timeout", 5), client=c, **kw)


@pytest.mark.anyio
async def test_it_streams_each_batch_while_the_run_works_and_returns_everything():
    fake = Fake([[{"n": 1}], [{"n": 2}, {"n": 3}]], polls=3)
    got = []
    out = await go(fake, on_items=lambda batch: got.append([i["n"] for i in batch]))
    assert got == [[1], [2, 3]] and [i["n"] for i in out.items] == [1, 2, 3]
    assert (out.run_id, out.dataset_id, out.usage_usd) == ("RUN1", "DS1", 0.0123)


@pytest.mark.anyio
async def test_it_starts_the_actor_with_the_payload_a_cost_cap_and_a_server_timeout():
    fake = Fake([[{"n": 1}]], polls=1)
    await go(fake, payload={"queries": "laptops", "countryCode": "cz"}, cap=0.5, timeout=40)
    start = next(r for r in fake.requests if r.method == "POST" and r.url.path.endswith("/runs"))
    assert start.url.path.endswith("/acts/apify~google-search-scraper/runs")
    assert json.loads(start.content) == {"queries": "laptops", "countryCode": "cz"}
    assert start.url.params["maxTotalChargeUsd"] == "0.5" and start.url.params["timeout"] == "40"
    assert not fake.aborted


@pytest.mark.anyio
async def test_a_run_that_never_finishes_is_aborted_when_the_time_is_up():
    fake = Fake([], polls=10_000)
    with pytest.raises(ApifyError) as exc:
        await go(fake, timeout=0.3)
    assert fake.aborted and exc.value.run_id == "RUN1" and "TimeoutError" in str(exc.value)


@pytest.mark.anyio
@pytest.mark.parametrize("final", ["FAILED", "TIMED-OUT", "ABORTED"])
async def test_a_run_that_does_not_succeed_is_an_error_not_partial_data(final):
    fake = Fake([[{"n": 1}]], polls=1, final=final)
    with pytest.raises(ApifyError, match="did not succeed") as exc:
        await go(fake)
    assert exc.value.run_id == "RUN1" and not fake.aborted  # it ended by itself: nothing left to abort


@pytest.mark.anyio
async def test_provider_error_bodies_and_the_token_never_reach_the_message():
    fake = Fake([[{"n": 1}]], polls=1, fail_items=True)
    with pytest.raises(ApifyError) as exc:
        await go(fake)
    assert "secret internals" not in str(exc.value) and "test-token-value" not in str(exc.value)
    assert "HTTPStatusError" in str(exc.value)


@pytest.mark.anyio
async def test_a_different_run_id_while_polling_is_rejected():
    fake = Fake([], polls=1)
    original = fake.handler

    def swapped(request):
        r = original(request)
        if request.method == "GET" and request.url.path.endswith("/actor-runs/RUN1"):
            return httpx.Response(200, json={"data": {"id": "OTHER", "status": "RUNNING", "defaultDatasetId": "DS1"}})
        return r

    fake.handler = swapped
    with pytest.raises(ApifyError, match="different run"):
        await go(fake)


@pytest.mark.anyio
@pytest.mark.parametrize("actor", ["", "no-slash", "a/b/c", "bad actor/name", "../x/y", "x/y?z=1"])
async def test_only_well_formed_actor_ids_are_run(actor):
    with pytest.raises(ApifyError, match="Invalid Apify Actor id"):
        await go(Fake([]), actor=actor)


@pytest.mark.anyio
async def test_a_missing_token_and_unbounded_timeouts_are_refused_before_any_request():
    fake = Fake([])
    with pytest.raises(ApifyError, match="APIFY_TOKEN"):
        async with client(fake) as c:
            await run_actor(Settings(apify_token=""), "a/b", {}, max_charge_usd=0.5, timeout=5, client=c)
    for bad in (0, -1, float("inf"), float("nan"), 301):
        with pytest.raises(ApifyError, match="timeout"):
            async with client(fake) as c:
                await run_actor(S, "a/b", {}, max_charge_usd=0.5, timeout=bad, client=c)
    assert fake.requests == []


@pytest.mark.anyio
async def test_a_malformed_usage_figure_is_treated_as_zero_not_trusted():
    for weird in (None, "5", -1, True, [], {"usd": 1}):
        fake = Fake([[{"n": 1}]], polls=1, usage=weird)
        assert (await go(fake)).usage_usd == 0.0
