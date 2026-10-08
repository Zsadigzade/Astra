"""I-path integration: the dashboard receives actual mode and data provenance."""

import pytest

from app.core.config import Settings
from app.core.models import JobResult
from tests.test_acts import run_task


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_scripted_lines_are_labelled(tmp_path):
    events, _ = await run_task(tmp_path, "honest")
    lines = [e for e in events if e.type == "negotiation"]
    assert lines and all(e.data["backend"] == "mock" for e in lines)


@pytest.mark.anyio
async def test_openai_failure_is_visible_and_guard_still_blocks(tmp_path, monkeypatch):
    import app.buyer.negotiator as neg

    async def fail(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(neg.Runner, "run", fail)
    settings = Settings(llm_mode="openai", ledger_path=str(tmp_path / "buyer.db"),
                        audio_dir=str(tmp_path / "audio"), seller_url="http://seller")
    events, balances = await run_task(tmp_path, "con", settings=settings)
    max_lines = [e for e in events if e.type == "negotiation" and e.data["speaker"] == "max"
                 and e.data["action"] != "walk"]
    assert max_lines and all(e.data["backend"] == "mock" for e in max_lines)
    assert all(e.data["fallback_reason"] for e in max_lines)
    assert "blocked" in {e.type for e in events}
    assert "escrow_locked" not in {e.type for e in events}
    assert balances["buyer"] == 100


@pytest.mark.anyio
async def test_cached_delivery_provenance_survives_seller_buyer_flow(tmp_path, monkeypatch):
    from app.seller.job import sample_flats
    import app.seller.app as seller_app

    async def cached_job(job, mode, settings):
        # Synthetic fixture to verify transport, never saved as a real scrape.
        return JobResult(flats=sample_flats(job), source="apify_cached",
                         fetched_at="2026-10-08T20:00:00+00:00", actor_id="test/actor",
                         dataset_id="test-dataset", run_id="test-run")

    monkeypatch.setattr(seller_app, "run_job", cached_job)
    events, _ = await run_task(tmp_path, "honest")
    delivered = next(e for e in events if e.type == "delivered")
    assert delivered.data["source"] == "apify_cached"
    assert delivered.data["result"]["run_id"] == "test-run"
    assert delivered.data["result"]["fetched_at"] == "2026-10-08T20:00:00+00:00"
    assert "released" in {e.type for e in events}
