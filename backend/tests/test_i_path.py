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
async def test_codex_failure_is_visible_in_honest_negotiation(tmp_path, monkeypatch):
    import app.buyer.negotiator as neg

    async def fail(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(neg, "run_codex", fail)
    settings = Settings(llm_mode="codex", ledger_path=str(tmp_path / "buyer.db"),
                        audio_dir=str(tmp_path / "audio"), seller_url="http://seller")
    events, balances = await run_task(tmp_path, "honest", settings=settings)
    # Max's opening question is a fixed template (action "open"), not a model call, so it has no fallback reason.
    max_lines = [e for e in events if e.type == "negotiation" and e.data["speaker"] == "max"
                 and e.data["action"] not in {"walk", "open"}]
    assert max_lines and all(e.data["backend"] == "mock" for e in max_lines)
    assert all(e.data["fallback_reason"] for e in max_lines)
    assert "released" in {e.type for e in events}
    assert balances["buyer"] == 93


@pytest.mark.anyio
@pytest.mark.parametrize("stale", [False, True])
async def test_cached_delivery_provenance_survives_seller_buyer_flow(tmp_path, monkeypatch, stale):
    from app.seller.job import sample_flats
    import app.seller.app as seller_app

    async def cached_job(job, mode, settings):
        # Synthetic fixture to verify transport, never saved as a real scrape.
        return JobResult(flats=sample_flats(job), source="apify_cached",
                         fetched_at="2026-10-08T20:00:00+00:00", actor_id="test/actor",
                         dataset_id="test-dataset", run_id="test-run",
                         cache_stale=stale, cache_age_seconds=90000 if stale else 10)

    monkeypatch.setattr(seller_app, "run_job", cached_job)
    events, _ = await run_task(tmp_path, "honest")
    delivered = next(e for e in events if e.type == "delivered")
    assert delivered.data["source"] == "apify_cached"
    assert delivered.data["result"]["run_id"] == "test-run"
    assert delivered.data["result"]["fetched_at"] == "2026-10-08T20:00:00+00:00"
    assert delivered.data["result"]["cache_stale"] is stale
    assert delivered.data["result"]["cache_age_seconds"] == (90000 if stale else 10)
    assert "released" in {e.type for e in events}


@pytest.mark.anyio
async def test_staged_con_is_scripted_even_when_codex_configured(tmp_path, monkeypatch):
    import app.buyer.negotiator as neg
    import app.seller.persona as persona

    async def unexpected_call(*args, **kwargs):
        pytest.fail("Staged con must not invoke Codex")

    monkeypatch.setattr(neg, "run_codex", unexpected_call)
    monkeypatch.setattr(persona, "run_codex", unexpected_call)
    settings = Settings(llm_mode="codex", seller_llm_mode="codex", ledger_path=str(tmp_path / "buyer.db"),
                        audio_dir=str(tmp_path / "audio"), seller_url="http://seller")
    events, balances = await run_task(tmp_path, "con", settings=settings)
    lines = [e for e in events if e.type == "negotiation" and e.data["speaker"] == "max"
             and e.data["action"] != "walk"]
    assert lines and all(e.data["backend"] == "mock" for e in lines)
    assert "blocked" in {e.type for e in events}
    assert "escrow_locked" not in {e.type for e in events}
    assert balances["buyer"] == 100


@pytest.mark.anyio
@pytest.mark.parametrize("failure", [False, True])
async def test_viktor_model_provenance_survives_full_settlement(tmp_path, monkeypatch, failure):
    import app.seller.persona as persona

    moves = iter([("counter", 18), ("counter", 11), ("counter", 8), ("accept", 7)])

    async def run(*args):
        if failure:
            raise TimeoutError("private-provider-diagnostics")
        action, price = next(moves)
        return {"action": action, "price": price, "message": f"{price} for the rentals."}

    monkeypatch.setattr(persona, "run_codex", run)
    settings = Settings(llm_mode="mock", seller_llm_mode="codex",
                        ledger_path=str(tmp_path / "buyer.db"),
                        audio_dir=str(tmp_path / "audio"), seller_url="http://seller")
    events, balances = await run_task(tmp_path, "honest", settings=settings)
    lines = [e.data for e in events if e.type == "negotiation" and e.data["speaker"] == "viktor"]
    assert lines and all(line["backend"] == ("mock" if failure else "codex") for line in lines)
    assert all(bool(line.get("fallback_reason")) == failure for line in lines)
    assert "private-provider-diagnostics" not in str([e.model_dump() for e in events])
    assert "released" in {e.type for e in events}
    assert (balances["buyer"], balances["seller"], balances["escrow"]) == (93, 7, 0)
