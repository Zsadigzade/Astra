"""Run any Apify Actor with a bounded budget and stream its dataset while it works.

Used for web research: a search Actor, then a page-preview Actor. Nothing here interprets the items; callers must treat
them as untrusted web data. Error messages never include provider response bodies or credentials.
"""

import asyncio
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from app.core.config import Settings
from app.seller.apify import API, ApifyError, _identifier

log = logging.getLogger(__name__)
ACTIVE = {"READY", "RUNNING", "TIMING-OUT", "ABORTING"}
TERMINAL = {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}
POLL_SECONDS = 1.5
MAX_ITEMS = 500
_ACTOR = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


@dataclass
class RunResult:
    items: list[Any] = field(default_factory=list)
    usage_usd: float = 0.0
    run_id: str = ""
    dataset_id: str = ""


def _data(response: httpx.Response) -> dict:
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("data"), dict):
        raise ApifyError("Apify returned invalid metadata")
    return body["data"]


def _usd(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else 0.0


async def run_actor(settings: Settings, actor_id: str, payload: dict, *, max_charge_usd: float, timeout: float,
                    on_items: Callable[[list], None] | None = None,
                    client: httpx.AsyncClient | None = None) -> RunResult:
    """Start `actor_id`, poll it, hand each batch of new dataset items to `on_items`, return everything at the end."""
    if not _ACTOR.fullmatch(actor_id or ""):
        raise ApifyError("Invalid Apify Actor id")
    if not settings.apify_token.strip():
        raise ApifyError("Web research needs APIFY_TOKEN")
    if not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise ApifyError("Research timeout must be positive and at most 300 seconds")
    own = client is None
    http = client or httpx.AsyncClient(base_url=API, timeout=min(timeout, 20),
                                       headers={"Authorization": f"Bearer {settings.apify_token}",
                                                "User-Agent": "apify-agent-skills/apify-ultimate-scraper"})
    out = RunResult()
    terminal = False
    seen = 0

    async def drain(final: bool = False) -> None:
        nonlocal seen
        while out.dataset_id and seen < MAX_ITEMS:
            response = await http.get(f"/datasets/{out.dataset_id}/items",
                                      params={"format": "json", "clean": "true", "offset": seen, "limit": MAX_ITEMS - seen})
            response.raise_for_status()
            batch = response.json()
            if not isinstance(batch, list):
                raise ApifyError("Apify dataset must be a list")
            if not batch:
                return
            seen += len(batch)
            out.items.extend(batch)
            if on_items:
                on_items(batch)
            if not final:
                return

    try:
        async with asyncio.timeout(timeout):
            run = _data(await http.post(f"/acts/{actor_id.replace('/', '~')}/runs",
                                        params={"timeout": math.ceil(timeout), "maxTotalChargeUsd": max_charge_usd},
                                        json=payload))
            out.run_id, out.dataset_id = _identifier(run.get("id")), _identifier(run.get("defaultDatasetId"))
            while run.get("status") in ACTIVE:
                await asyncio.sleep(POLL_SECONDS)
                run = _data(await http.get(f"/actor-runs/{out.run_id}", params={"waitForFinish": 1}))
                if _identifier(run.get("id")) != out.run_id:
                    raise ApifyError("Apify polling returned a different run")
                await drain()
            terminal = run.get("status") in TERMINAL
            if run.get("status") != "SUCCEEDED":
                raise ApifyError(f"Apify {actor_id} run did not succeed")
            await drain(final=True)
            out.usage_usd = _usd(run.get("usageTotalUsd"))
            return out
    except ApifyError as exc:
        raise ApifyError(str(exc), run_id=out.run_id or None, dataset_id=out.dataset_id or None) from None
    except (httpx.HTTPError, TimeoutError, ValueError) as exc:
        raise ApifyError(f"Apify request failed ({type(exc).__name__})", run_id=out.run_id or None,
                         dataset_id=out.dataset_id or None) from None
    finally:
        if out.run_id and not terminal:
            try:
                async with asyncio.timeout(3):
                    (await http.post(f"/actor-runs/{out.run_id}/abort")).raise_for_status()
            except (httpx.HTTPError, TimeoutError, asyncio.CancelledError):
                log.warning("Apify abort unavailable; the server-side run timeout remains active")
        if own:
            await http.aclose()
