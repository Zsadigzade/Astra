"""Bounded Sreality Actor runs and explicitly labelled, job-specific real-data cache.

Schema: https://apify.com/swerve/sreality-scraper (checked 2026-10-08).
District names alone are ambiguous; require an explicit Prague district number.
"""

import asyncio
import json
import logging
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit, urlunsplit

import httpx

from shared.config import Settings
from shared.models import Flat, JobResult, JobSpec

log = logging.getLogger(__name__)
ACTOR_ID = "swerve/sreality-scraper"
API = "https://api.apify.com/v2"
MAX_CHARGE_USD = 1.10  # Per-run Actor event cap; separate platform usage can still apply.
DISTRICT = re.compile(r"\b(?:praha|prague)\s*(\d+)\b", re.IGNORECASE)


class ApifyError(RuntimeError):
    """Safe for display: never include provider response bodies or credentials."""


def _validate_job(job: JobSpec) -> None:
    if not re.fullmatch(r"(?:praha|prague)\s*7", job.district.strip(), re.IGNORECASE):
        raise ApifyError("The rental integration currently supports Praha 7 only")
    if not 1 <= job.count <= 200 or job.max_price_czk <= 0:
        raise ApifyError("Rental count must be 1–200 and maximum rent must be positive")


def _url(value: object) -> tuple[str, str] | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or parsed.hostname not in {"www.sreality.cz", "sreality.cz"}
                or parsed.username or parsed.password or parsed.port is not None):
            return None
        match = re.fullmatch(r"/detail/pronajem/byt/[^/]+/[^/]+/(\d+)/?", parsed.path)
        if not match:
            return None
        return urlunsplit(("https", "www.sreality.cz", parsed.path.rstrip("/"), "", "")), match[1]
    except ValueError:
        return None


def map_items(items: object, job: JobSpec) -> list[Flat]:
    """Reject unusable records; never invent addresses, prices, URLs or extra flats."""
    _validate_job(job)
    if not isinstance(items, list):
        raise ApifyError("Apify dataset must be a list of rental records")
    flats, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            continue
        if (item.get("dealType") != "rent" or item.get("propertyType") != "apartment"
                or item.get("currency") != "CZK" or item.get("priceUnit") != "per month"):
            continue
        price = item.get("price")
        if (type(price) not in (int, float) or not 0 < price <= job.max_price_czk
                or not float(price).is_integer()):
            continue
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        location = " · ".join(item[k].strip() for k in ("city", "locality", "district")
                              if isinstance(item.get(k), str) and item[k].strip())
        if set(DISTRICT.findall(location)) != {"7"}:
            continue
        url = _url(item.get("url"))
        if url is None or url[1] in seen:
            continue
        seen.add(url[1])
        flats.append(Flat(title=title.strip(), price_czk=int(price),
                          district=f"{job.district} — {location}", url=url[0]))
        if len(flats) == job.count:
            return flats
    raise ApifyError(f"Only {len(flats)} valid unique Praha 7 rentals matched; {job.count} required")


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", value):
        raise ApifyError("Apify returned invalid run or dataset metadata")
    return value


def _run_data(response: httpx.Response) -> dict:
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("data"), dict):
        raise ApifyError("Apify returned invalid run metadata")
    if not isinstance(body["data"].get("status"), str):
        raise ApifyError("Apify returned invalid run status")
    return body["data"]


async def scrape(job: JobSpec, settings: Settings) -> JobResult:
    _validate_job(job)
    if settings.apify_actor_id != ACTOR_ID:
        raise ApifyError(f"Only {ACTOR_ID} has a supported input/output mapping")
    if not settings.apify_token.strip():
        raise ApifyError("APIFY_TOKEN is required for live rental data")
    if not job.count <= settings.apify_max_items <= 200:
        raise ApifyError("APIFY_MAX_ITEMS must cover the requested count and be at most 200")
    timeout = settings.apify_timeout_seconds
    if not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise ApifyError("APIFY_TIMEOUT_SECONDS must be positive and at most 300")
    run_id = None
    terminal = False
    async with httpx.AsyncClient(
        base_url=API, timeout=min(timeout, 15),
        headers={"Authorization": f"Bearer {settings.apify_token}",
                 "User-Agent": "apify-agent-skills/apify-ultimate-scraper"},
    ) as client:
        try:
            async with asyncio.timeout(timeout):
                run = _run_data(await client.post(
                    f"/acts/{ACTOR_ID.replace('/', '~')}/runs",
                    params={"timeout": math.ceil(timeout), "waitForFinish": 1,
                            "maxTotalChargeUsd": MAX_CHARGE_USD},
                    json={"location": "Praha", "dealType": "rent", "propertyType": "apartment",
                          "maxItems": settings.apify_max_items, "maxPrice": job.max_price_czk,
                          "fetchDetails": False},
                ))
                run_id = _identifier(run.get("id"))
                while run.get("status") in {"READY", "RUNNING", "TIMING-OUT", "ABORTING"}:
                    await asyncio.sleep(0.5)
                    run = _run_data(await client.get(f"/actor-runs/{run_id}", params={"waitForFinish": 1}))
                terminal = run.get("status") in {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}
                if run.get("status") != "SUCCEEDED":
                    raise ApifyError("Apify rental run did not succeed")
                dataset_id = _identifier(run.get("defaultDatasetId"))
                response = await client.get(f"/datasets/{dataset_id}/items", params={
                    "format": "json", "clean": "true", "limit": settings.apify_max_items,
                })
                response.raise_for_status()
                flats = map_items(response.json(), job)
                return JobResult(flats=flats, source="apify", actor_id=ACTOR_ID,
                                 run_id=run_id, dataset_id=dataset_id,
                                 fetched_at=datetime.now(timezone.utc).isoformat())
        except (httpx.HTTPError, TimeoutError, ValueError) as exc:
            # Response bodies and exception strings can contain secrets; expose only the class.
            raise ApifyError(f"Apify rental request failed ({type(exc).__name__})") from None
        finally:
            if run_id and not terminal:
                try:
                    async with asyncio.timeout(3):
                        response = await client.post(f"/actor-runs/{run_id}/abort")
                        response.raise_for_status()
                except (httpx.HTTPError, TimeoutError):
                    log.warning("Apify abort unavailable; server-side run timeout remains active")


def save_cache(job: JobSpec, result: JobResult, settings: Settings) -> None:
    path = Path(settings.apify_cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "job": job.model_dump(), "result": result.model_dump()}
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name, suffix=".tmp", delete=False) as handle:
            temp = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temp, path)
    finally:
        if temp and temp.exists():
            temp.unlink()


def load_cache(job: JobSpec, settings: Settings) -> JobResult:
    _validate_job(job)
    try:
        payload = json.loads(Path(settings.apify_cache_path).read_text(encoding="utf-8"))
        if (not isinstance(payload, dict) or payload.get("version") != 1
                or payload.get("job") != job.model_dump()):
            raise ValueError("wrong cache job")
        result = JobResult.model_validate(payload["result"])
        if result.source != "apify" or result.actor_id != settings.apify_actor_id:
            raise ValueError("wrong provenance")
        _identifier(result.run_id)
        _identifier(result.dataset_id)
        timestamp = datetime.fromisoformat(result.fetched_at or "")
        if timestamp.tzinfo is None or timestamp > datetime.now(timezone.utc):
            raise ValueError("invalid timestamp")
        # Recheck values on disk before trusting a cached delivery.
        rows = [{"title": f.title, "price": f.price_czk, "locality": f.district, "url": f.url,
                 "dealType": "rent", "propertyType": "apartment", "currency": "CZK",
                 "priceUnit": "per month"} for f in result.flats]
        map_items(rows, job)
        if len(result.flats) != job.count:
            raise ValueError("wrong cached count")
        return result.model_copy(update={"source": "apify_cached"})
    except (OSError, ValueError, KeyError, TypeError, ApifyError):
        raise ApifyError("No valid saved Apify rental cache matches this exact job") from None


async def rental_result(job: JobSpec, settings: Settings) -> JobResult:
    if settings.apify_mode == "cached":
        result = load_cache(job, settings)
        log.warning("Using apify_cached rentals fetched at %s", result.fetched_at)
        return result
    try:
        result = await scrape(job, settings)
    except ApifyError as exc:
        try:
            result = load_cache(job, settings)
        except ApifyError:
            raise ApifyError(f"{exc}; no matching real-data cache available") from None
        log.warning("Live rental data unavailable; using apify_cached data from %s", result.fetched_at)
        return result
    try:
        save_cache(job, result, settings)
    except OSError:
        log.warning("Live Apify rentals delivered, but saving their offline cache failed")
    return result
