from dataclasses import replace
import json

import httpx
import pytest

from seller import apify
from seller.job import run_job
from shared.config import Settings
from shared.models import DemoMode, JobSpec


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings(tmp_path):
    return Settings(apify_mode="apify", apify_token="test-secret",
                    apify_cache_path=str(tmp_path / "flats.json"))


def row(number=1, **changes):
    return {"title": "Rent apartment 2+kk", "dealType": "rent", "propertyType": "apartment",
            "city": "Praha 7", "locality": "Kamenická, Praha 7", "district": "Holešovice",
            "price": 22000, "currency": "CZK", "priceUnit": "per month",
            "url": f"https://www.sreality.cz/detail/pronajem/byt/2+kk/praha-holesovice/{number}",
            **changes}


def mock_http(monkeypatch, handler):
    constructor = httpx.AsyncClient
    monkeypatch.setattr(apify.httpx, "AsyncClient", lambda **kw: constructor(
        **kw, transport=httpx.MockTransport(handler)))


def success(monkeypatch, items):
    calls = []

    def handle(request):
        calls.append(request)
        if request.url.path.endswith("/runs"):
            return httpx.Response(201, json={"data": {"id": "run1", "status": "SUCCEEDED",
                                                    "defaultDatasetId": "dataset1"}})
        return httpx.Response(200, json=items)

    mock_http(monkeypatch, handle)
    return calls


@pytest.mark.anyio
async def test_live_mapping_cache_and_offline_delivery(monkeypatch, settings):
    calls = success(monkeypatch, [row(), row(2, price=25000)])
    job = JobSpec(count=2)
    result = await run_job(job, DemoMode.honest, settings)
    assert result.source == "apify" and len(result.flats) == 2
    assert result.run_id == "run1" and result.dataset_id == "dataset1" and result.fetched_at
    assert all(r.headers["Authorization"] == "Bearer test-secret" for r in calls)
    assert all("test-secret" not in str(r.url) for r in calls)
    assert calls[0].url.path == "/v2/acts/swerve~sreality-scraper/runs"
    assert json.loads(calls[0].content) == {"location": "Praha", "dealType": "rent",
        "propertyType": "apartment", "maxItems": 200, "maxPrice": 25000, "fetchDetails": False}
    assert calls[0].url.params["timeout"] == "90"
    assert calls[0].url.params["maxTotalChargeUsd"] == "1.1"
    cached = await run_job(job, DemoMode.honest, replace(settings, apify_mode="cached", apify_token=""))
    assert cached.source == "apify_cached" and cached.flats == result.flats
    assert len(calls) == 2


@pytest.mark.parametrize("changes", [
    {"price": 25001}, {"price": -1}, {"price": 0}, {"price": True}, {"price": "22000"},
    {"price": 22000.2}, {"price": float("nan")}, {"currency": "EUR"}, {"priceUnit": "per day"},
    {"dealType": "buy"}, {"propertyType": "house"}, {"title": " "},
    {"city": "Praha 17", "locality": "Praha 17"}, {"city": "Praha 8"},
    {"city": "Praha", "locality": "Holešovice"}, {"url": "https://example.invalid/flat/1"},
    {"url": "https://www.sreality.cz/detail/prodej/byt/2+kk/praha-holesovice/1"},
    {"url": "https://www.sreality.cz@evil.invalid/detail/pronajem/byt/2+kk/praha-holesovice/1"},
])
def test_rejects_unproven_or_nonmatching_listings(changes):
    with pytest.raises(apify.ApifyError, match="Only 0"):
        apify.map_items([row(**changes)], JobSpec(count=1))


def test_duplicate_id_and_malformed_records_do_not_fill_count():
    with pytest.raises(apify.ApifyError, match="Only 1"):
        apify.map_items([None, {}, row(), row(url=row()["url"] + "?tracking=1"),
                         row(url=row()["url"].replace("praha-holesovice", "other"))], JobSpec(count=2))


@pytest.mark.anyio
@pytest.mark.parametrize("response", [httpx.Response(401, text="test-secret"),
    httpx.Response(200, json={"data": {"id": "run1", "status": "FAILED"}}),
    httpx.Response(200, json={"unexpected": "test-secret"})])
async def test_provider_failure_never_substitutes_samples(monkeypatch, settings, response):
    mock_http(monkeypatch, lambda request: response)
    with pytest.raises(apify.ApifyError) as error:
        await run_job(JobSpec(count=1), DemoMode.honest, settings)
    assert "test-secret" not in str(error.value)
    assert "no matching real-data cache" in str(error.value)


@pytest.mark.anyio
async def test_poll_then_fetch_only_after_success(monkeypatch, settings):
    calls = []

    def handle(request):
        calls.append(request)
        if request.url.path.endswith("/runs"):
            return httpx.Response(201, json={"data": {"id": "run1", "status": "RUNNING"}})
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": {"id": "run1", "status": "SUCCEEDED",
                                                    "defaultDatasetId": "dataset1"}})
        return httpx.Response(200, json=[row()])

    mock_http(monkeypatch, handle)
    assert (await apify.scrape(JobSpec(count=1), settings)).source == "apify"
    assert len(calls) == 3


@pytest.mark.anyio
async def test_timeout_aborts_cloud_run(monkeypatch, settings):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"data": {"id": "run1", "status": "RUNNING"}})

    mock_http(monkeypatch, handle)
    with pytest.raises(apify.ApifyError, match="TimeoutError"):
        await apify.scrape(JobSpec(count=1), replace(settings, apify_timeout_seconds=0.02))
    assert calls[-1].url.path == "/v2/actor-runs/run1/abort"


@pytest.mark.anyio
async def test_failure_uses_labelled_matching_cache(monkeypatch, settings, caplog):
    success(monkeypatch, [row()])
    job = JobSpec(count=1)
    live = await run_job(job, DemoMode.honest, settings)
    cached = await run_job(job, DemoMode.honest, replace(settings, apify_token=""))
    assert cached.source == "apify_cached" and cached.fetched_at == live.fetched_at
    assert "apify_cached" in caplog.text
    with pytest.raises(apify.ApifyError, match="exact job"):
        apify.load_cache(JobSpec(count=2), settings)


@pytest.mark.anyio
async def test_cache_validation_and_failed_scrape_preserve_prior_cache(monkeypatch, settings):
    success(monkeypatch, [row()])
    job = JobSpec(count=1)
    await run_job(job, DemoMode.honest, settings)
    from pathlib import Path
    path = Path(settings.apify_cache_path)
    saved = path.read_text(encoding="utf-8")
    # A failed run must not overwrite the only good offline fallback.
    await run_job(job, DemoMode.honest, replace(settings, apify_token=""))
    assert path.read_text(encoding="utf-8") == saved
    payload = json.loads(saved)
    payload["result"]["flats"][0]["price_czk"] = 99000
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(apify.ApifyError, match="exact job"):
        apify.load_cache(job, settings)


@pytest.mark.anyio
async def test_sample_and_staged_junk_never_call_provider(monkeypatch, settings):
    def fail(request):
        pytest.fail("Unexpected paid API call")
    mock_http(monkeypatch, fail)
    assert (await run_job(JobSpec(), DemoMode.junk, settings)).source == "sample"
    assert (await run_job(JobSpec(), DemoMode.honest, replace(settings, apify_mode="sample"))).source == "sample"
    with pytest.raises(ValueError, match="APIFY_MODE"):
        await run_job(JobSpec(), DemoMode.honest, replace(settings, apify_mode="typo"))


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["sample", "wrong_actor", "no_timestamp", "duplicate", "wrong_district"])
async def test_cache_rejects_untrusted_provenance_and_data(monkeypatch, settings, mutation):
    from pathlib import Path
    success(monkeypatch, [row(), row(2)])
    job = JobSpec(count=2)
    await run_job(job, DemoMode.honest, settings)
    path = Path(settings.apify_cache_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload["result"]
    if mutation == "sample":
        result["source"] = "sample"
    elif mutation == "wrong_actor":
        result["actor_id"] = "other/actor"
    elif mutation == "no_timestamp":
        result["fetched_at"] = None
    elif mutation == "duplicate":
        result["flats"][1] = result["flats"][0]
    else:
        result["flats"][0]["district"] = "Praha 17"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(apify.ApifyError, match="exact job"):
        apify.load_cache(job, settings)


@pytest.mark.anyio
@pytest.mark.parametrize("job,changes", [
    (JobSpec(count=0), {}), (JobSpec(count=201), {}), (JobSpec(district="Praha 8"), {}),
    (JobSpec(), {"apify_max_items": 201}), (JobSpec(), {"apify_max_items": 1}),
    (JobSpec(), {"apify_timeout_seconds": 0}), (JobSpec(), {"apify_actor_id": "other/actor"}),
])
async def test_invalid_job_or_configuration_fails_before_spending(monkeypatch, settings, job, changes):
    def fail(request):
        pytest.fail("Invalid config must not start a paid run")
    mock_http(monkeypatch, fail)
    with pytest.raises(apify.ApifyError):
        await apify.scrape(job, replace(settings, **changes))
