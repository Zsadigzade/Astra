from dataclasses import replace
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.core.models import DemoMode, JobSpec
from app.seller import apify
from app.seller.job import run_job


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
    assert json.loads(calls[0].content) == {"location": "Praha 7", "dealType": "rent",
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
    {"url": "https://www.sreality.cz/detail/pronajem/byt/2+kk/praha holesovice/1"},
    {"url": "https://www.sreality.cz/detail/pronajem/byt/2+kk/praha-holesovice/1\n"},
    {"url": "https://www.sreality.cz/detail/pronajem/byt/2+kk/praha-holesovice/1\x00"},
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
    (JobSpec.model_construct(count=0), {}), (JobSpec.model_construct(count=201), {}), (JobSpec(district="Praha 8"), {}),
    (JobSpec(), {"apify_max_items": 201}), (JobSpec(), {"apify_max_items": 1}),
    (JobSpec(), {"apify_timeout_seconds": 0}), (JobSpec(), {"apify_actor_id": "other/actor"}),
])
async def test_invalid_job_or_configuration_fails_before_spending(monkeypatch, settings, job, changes):
    def fail(request):
        pytest.fail("Invalid config must not start a paid run")
    mock_http(monkeypatch, fail)
    with pytest.raises(apify.ApifyError):
        await apify.scrape(job, replace(settings, **changes))


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["insufficient", "download"])
async def test_failed_live_result_keeps_recovery_identifiers(monkeypatch, settings, failure):
    def handle(request):
        if request.url.path.endswith("/runs"):
            return httpx.Response(201, json={"data": {
                "id": "run1", "status": "SUCCEEDED", "defaultDatasetId": "dataset1"}})
        return (httpx.Response(503, text="test-secret") if failure == "download"
                else httpx.Response(200, json=[row()]))

    mock_http(monkeypatch, handle)
    with pytest.raises(apify.ApifyError) as error:
        await apify.scrape(JobSpec(count=2), settings)
    assert error.value.run_id == "run1"
    assert error.value.dataset_id == "dataset1"
    assert "test-secret" not in str(error.value)


def recovered_http(monkeypatch, *, changes=None, items=None):
    calls = []
    run = {"id": "run1", "actId": "actor1", "status": "SUCCEEDED",
           "defaultDatasetId": "dataset1", "finishedAt": "2025-01-01T12:00:00.000Z",
           **(changes or {})}

    def handle(request):
        calls.append(request)
        assert request.method == "GET", "Recovery must never create or modify a run"
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": run})
        if "/acts/" in request.url.path:
            return httpx.Response(200, json={"data": {"id": "actor1"}})
        return httpx.Response(200, json=[row()] if items is None else items)

    mock_http(monkeypatch, handle)
    return calls


@pytest.mark.anyio
async def test_recovery_reads_existing_run_and_preserves_original_age(monkeypatch, settings):
    calls = recovered_http(monkeypatch)
    job = JobSpec(count=1)
    result = await apify.recover_run(job, settings, "run1")
    assert result.source == "apify"
    assert result.run_id == "run1" and result.dataset_id == "dataset1"
    assert result.actor_id == apify.ACTOR_ID
    assert result.fetched_at == "2025-01-01T12:00:00+00:00"
    assert len(calls) == 3
    assert calls[-1].url.params["limit"] == "200"
    apify.save_cache(job, result, settings)
    cached = apify.load_cache(job, settings)
    assert cached.source == "apify_cached" and cached.fetched_at == result.fetched_at


@pytest.mark.anyio
@pytest.mark.parametrize("changes", [
    {"status": "RUNNING"}, {"status": "FAILED"}, {"actId": "other_actor"},
    {"id": "different_run"}, {"finishedAt": None}, {"finishedAt": "not-a-date"},
    {"finishedAt": "2025-01-01T12:00:00"}, {"finishedAt": "2999-01-01T12:00:00Z"},
])
async def test_recovery_rejects_untrusted_or_incomplete_runs_before_dataset(monkeypatch, settings, changes):
    calls = recovered_http(monkeypatch, changes=changes)
    with pytest.raises(apify.ApifyError) as error:
        await apify.recover_run(JobSpec(count=1), settings, "run1")
    assert error.value.run_id == "run1"
    assert all("/datasets/" not in request.url.path for request in calls)


@pytest.mark.anyio
async def test_recovered_records_must_still_match_requested_job(monkeypatch, settings):
    recovered_http(monkeypatch, items=[row(price=26000)])
    with pytest.raises(apify.ApifyError, match="Only 0") as error:
        await apify.recover_run(JobSpec(count=1), settings, "run1")
    assert error.value.run_id == "run1" and error.value.dataset_id == "dataset1"


@pytest.mark.anyio
async def test_invalid_recovery_identifier_cannot_become_request_or_link(monkeypatch, settings):
    def fail(request):
        pytest.fail("Invalid identifier must fail before a provider request")
    mock_http(monkeypatch, fail)
    with pytest.raises(apify.ApifyError) as error:
        await apify.recover_run(JobSpec(count=1), settings, "../run?token=test-secret")
    assert error.value.run_id is None
    assert "test-secret" not in str(error.value)


@pytest.mark.anyio
async def test_cli_recovery_never_starts_run_and_prints_links_on_cache_failure(monkeypatch, settings, capsys):
    from scripts import scrape_flats
    calls = recovered_http(monkeypatch)
    monkeypatch.setattr(scrape_flats, "Settings", lambda: settings)
    monkeypatch.setattr("sys.argv", ["scrape_flats.py", "--run-id", "run1", "--count", "1"])

    def no_space(*args):
        raise OSError("test-secret must not leak")
    monkeypatch.setattr(scrape_flats, "save_cache", no_space)
    assert await scrape_flats.main() == 1
    output = capsys.readouterr().out
    assert "cannot save offline cache" in output
    assert "https://console.apify.com/actors/runs/run1" in output
    assert "https://console.apify.com/storage/datasets/dataset1" in output
    assert "--run-id run1 --count 1 --max-price 25000" in output
    assert "test-secret" not in output
    assert all(request.method == "GET" for request in calls)


@pytest.mark.anyio
async def test_cli_failed_mapping_prints_recovery_links(monkeypatch, settings, capsys):
    from scripts import scrape_flats
    success(monkeypatch, [row()])
    monkeypatch.setattr(scrape_flats, "Settings", lambda: settings)
    monkeypatch.setattr("sys.argv", ["scrape_flats.py", "--count", "2"])
    assert await scrape_flats.main() == 1
    output = capsys.readouterr().out
    assert "Only 1" in output
    assert "https://console.apify.com/actors/runs/run1" in output
    assert "https://console.apify.com/storage/datasets/dataset1" in output


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["bool_price", "string_price", "float_price", "bool_count", "bool_version", "unsupported_actor"])
async def test_cache_rejects_coerced_fields_and_unsupported_actor(monkeypatch, settings, mutation):
    success(monkeypatch, [row()])
    job = JobSpec(count=1)
    await run_job(job, DemoMode.honest, settings)
    path = Path(settings.apify_cache_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if mutation.endswith("price"):
        payload["result"]["flats"][0]["price_czk"] = {
            "bool_price": True, "string_price": "22000", "float_price": 22000.0,
        }[mutation]
    elif mutation == "bool_count":
        payload["job"]["count"] = True
    elif mutation == "bool_version":
        payload["version"] = True
    else:
        payload["result"]["actor_id"] = "other/actor"
        settings = replace(settings, apify_actor_id="other/actor")
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(apify.ApifyError, match="exact job"):
        apify.load_cache(job, settings)


@pytest.mark.anyio
async def test_polled_run_identity_cannot_change_provenance(monkeypatch, settings):
    calls = []

    def handle(request):
        calls.append(request)
        if request.url.path.endswith("/runs"):
            return httpx.Response(201, json={"data": {"id": "run1", "status": "RUNNING"}})
        return httpx.Response(200, json={"data": {
            "id": "other_run", "status": "SUCCEEDED", "defaultDatasetId": "other_dataset"}})

    mock_http(monkeypatch, handle)
    with pytest.raises(apify.ApifyError, match="different run") as error:
        await apify.scrape(JobSpec(count=1), settings)
    assert error.value.run_id == "run1"
    assert error.value.dataset_id is None
    assert calls[-1].url.path == "/v2/actor-runs/run1/abort"
    assert not any("/datasets/" in str(request.url) for request in calls)


@pytest.mark.anyio
async def test_cancellation_aborts_owned_run_without_cache_fallback(monkeypatch, settings):
    started = asyncio.Event()
    calls = []

    def handle(request):
        calls.append(request)
        started.set()
        return httpx.Response(200, json={"data": {"id": "run1", "status": "RUNNING"}})

    mock_http(monkeypatch, handle)
    task = asyncio.create_task(apify.rental_result(JobSpec(count=1), settings))
    await asyncio.wait_for(started.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls[-1].url.path == "/v2/actor-runs/run1/abort"
    assert not Path(settings.apify_cache_path).exists()


@pytest.mark.anyio
async def test_failed_atomic_replace_preserves_cache_and_cleans_temporary_file(monkeypatch, settings):
    success(monkeypatch, [row()])
    job = JobSpec(count=1)
    result = await run_job(job, DemoMode.honest, settings)
    path = Path(settings.apify_cache_path)
    original = path.read_bytes()

    def fail_replace(*args):
        raise OSError("disk unavailable")

    monkeypatch.setattr(apify.os, "replace", fail_replace)
    with pytest.raises(OSError):
        apify.save_cache(job, result, settings)
    assert path.read_bytes() == original
    assert list(path.parent.glob(path.name + "*.tmp")) == []
    assert apify.load_cache(job, settings).flats == result.flats


def test_integer_rents_do_not_overflow_float_conversion():
    price = 10 ** 400
    flats = apify.map_items([row(price=price)], JobSpec(count=1, max_price_czk=price))
    assert flats[0].price_czk == price
