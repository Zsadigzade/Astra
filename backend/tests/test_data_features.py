"""Freshness, independent cache entries and explainable rental validation."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.models import JobResult, JobSpec
from app.seller import apify
from tests.test_apify import row, success, recovered_http


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings(tmp_path):
    return Settings(apify_mode="cached", apify_token="fixture-secret",
                    apify_cache_path=str(tmp_path / "cache.json"),
                    apify_cache_max_age_seconds=3600, apify_allow_stale_cache=False)


def result(job, *, age=0, run="run1"):
    return JobResult(flats=apify.map_items([row(i) for i in range(job.count)], job),
                     source="apify", actor_id=apify.ACTOR_ID, run_id=run, dataset_id="dataset1",
                     fetched_at=(datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat())


def test_fresh_cache_retains_original_provenance(settings):
    job = JobSpec(count=2)
    live = result(job, age=30)
    apify.save_cache(job, live, settings)
    loaded = apify.load_cache(job, settings)
    assert not loaded.cache_stale and 30 <= loaded.cache_age_seconds < 60
    assert loaded.fetched_at == live.fetched_at and loaded.run_id == live.run_id
    assert loaded.source == "apify_cached"


def test_expired_refused_and_explicit_override_is_labelled(settings, caplog):
    job = JobSpec(count=1)
    live = result(job, age=7200)
    apify.save_cache(job, live, settings)
    with pytest.raises(apify.ApifyError, match="expired"):
        apify.load_cache(job, settings)
    loaded = apify.load_cache(job, replace(settings, apify_allow_stale_cache=True))
    assert loaded.cache_stale and loaded.cache_age_seconds >= 7200
    assert loaded.fetched_at == live.fetched_at
    assert "STALE CACHED DATA" in caplog.text


@pytest.mark.parametrize("age", [0, -1, float("nan"), float("inf")])
def test_invalid_age_policy_never_bypasses_validation(settings, age):
    with pytest.raises(apify.ApifyError, match="finite and positive"):
        apify.load_cache(JobSpec(count=1), replace(settings, apify_cache_max_age_seconds=age))


def test_future_timestamp_refused_even_with_override(settings):
    job = JobSpec(count=1)
    live = result(job, age=-600)
    path = Path(settings.apify_cache_path)
    path.write_text(json.dumps({"version": 1, "job": job.model_dump(), "result": live.model_dump()}))
    with pytest.raises(apify.ApifyError, match="exact job"):
        apify.load_cache(job, replace(settings, apify_allow_stale_cache=True))
    with pytest.raises(apify.ApifyError):
        apify.save_cache(job, live, settings)


def test_exact_age_boundary(monkeypatch, settings):
    instant = datetime.now(timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant
    monkeypatch.setattr(apify, "datetime", Clock)
    job = JobSpec(count=1)
    live = result(job).model_copy(update={"fetched_at": (instant - timedelta(seconds=3600)).isoformat()})
    apify.save_cache(job, live, settings)
    assert not apify.load_cache(job, settings).cache_stale


def test_multiple_jobs_and_legacy_cache_are_independent(settings):
    jobs = [JobSpec(count=1), JobSpec(count=2, max_price_czk=24000)]
    original = result(jobs[0])
    legacy = Path(settings.apify_cache_path)
    legacy.write_text(json.dumps({"version": 1, "job": jobs[0].model_dump(), "result": original.model_dump()}))
    before = legacy.read_bytes()
    assert apify.load_cache(jobs[0], settings).flats == original.flats
    for job in jobs:
        apify.save_cache(job, result(job), settings)
    assert legacy.read_bytes() == before
    assert apify.cache_path(jobs[0], settings) != apify.cache_path(jobs[1], settings)
    for job in jobs:
        assert len(apify.load_cache(job, settings).flats) == job.count
    with pytest.raises(apify.ApifyError):
        apify.load_cache(JobSpec(count=3), settings)


def test_corrupt_keyed_entry_never_falls_back_to_legacy(settings):
    job = JobSpec(count=1)
    live = result(job)
    Path(settings.apify_cache_path).write_text(json.dumps({"version": 1, "job": job.model_dump(), "result": live.model_dump()}))
    apify.save_cache(job, live, settings)
    apify.cache_path(job, settings).write_text("{}")
    with pytest.raises(apify.ApifyError):
        apify.load_cache(job, settings)


def test_concurrent_writes_publish_whole_independent_entries(settings):
    jobs = [JobSpec(count=1), JobSpec(count=2), JobSpec(count=3, max_price_czk=24000)]
    def write(index):
        job = jobs[index % len(jobs)]
        apify.save_cache(job, result(job, run=f"run{index}"), settings)
        loaded = apify.load_cache(job, settings)
        assert len(loaded.flats) == job.count
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(write, range(24)))
    for job in jobs:
        assert len(apify.load_cache(job, settings).flats) == job.count
    assert not list(apify.cache_path(jobs[0], settings).parent.glob("*.tmp"))


def test_failed_write_preserves_previous_entry(monkeypatch, settings):
    job = JobSpec(count=1)
    apify.save_cache(job, result(job), settings)
    path = apify.cache_path(job, settings)
    before = path.read_bytes()
    def fail(*args):
        raise OSError("disk-full")
    monkeypatch.setattr(apify.os, "replace", fail)
    with pytest.raises(OSError):
        apify.save_cache(job, result(job, run="run2"), settings)
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.tmp"))


def test_validation_report_counts_all_rows_after_requested_count():
    report = {}
    items = [row(1), row(2), row(2), None, row(3, dealType="buy"), row(4, currency="EUR"),
             row(5, price=-1), row(6, title=" "), row(7, city="Praha 8"), row(8, url="invalid")]
    flats = apify.map_items(items, JobSpec(count=1), report=report)
    assert len(flats) == 1
    assert report == {"total": 10, "accepted": 2, "selected": 1, "invalid_record": 1,
                      "wrong_property": 1, "wrong_currency_or_period": 1, "invalid_price": 1,
                      "invalid_title": 1, "wrong_district": 1, "invalid_url": 1, "duplicate": 1,
                      "shortfall": 0}


@pytest.mark.anyio
async def test_failure_report_and_provenance_safe_for_cli(monkeypatch, settings, capsys):
    from scripts import scrape_flats
    calls = recovered_http(monkeypatch, items=[row(), row(2, currency="fixture-secret")])
    monkeypatch.setattr(scrape_flats, "Settings", lambda: settings)
    monkeypatch.setattr("sys.argv", ["scrape_flats.py", "--run-id", "run1", "--count", "2", "--report"])
    assert await scrape_flats.main() == 1
    out = capsys.readouterr().out
    assert "accepted: 1" in out and "shortfall: 1" in out and "wrong_currency_or_period: 1" in out
    assert "fixture-secret" not in out and "run1" in out
    assert all(request.method == "GET" for request in calls)
    assert not apify.cache_path(JobSpec(count=2), settings).exists()


@pytest.mark.anyio
async def test_live_results_cache_two_jobs_without_overwriting(monkeypatch, settings):
    success(monkeypatch, [row(), row(2)])
    live_settings = replace(settings, apify_mode="apify")
    for count in (1, 2):
        await apify.rental_result(JobSpec(count=count), live_settings)
    for count in (1, 2):
        assert len(apify.load_cache(JobSpec(count=count), settings).flats) == count
