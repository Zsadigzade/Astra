"""Checks a delivery against the job spec using deterministic rules."""

from urllib.parse import urlsplit

from app.core.models import JobResult, JobSpec


def _valid_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not any(c.isspace() for c in url)
    except ValueError:
        return False


def _district(value: str) -> str:
    # Both the sample and Apify adapters append locality after a dash.
    normalized = " ".join(value.casefold().split())
    for separator in (" - ", " — ", " – "):
        normalized = normalized.split(separator, 1)[0]
    return normalized


def verify(result: JobResult | None, job: JobSpec) -> tuple[bool, dict[str, bool]]:
    flats = result.flats if result else []
    urls = [f.url for f in flats]
    checks = {
        "has_result": result is not None,
        f"at_least_{job.count}_flats": len(flats) >= job.count,
        f"all_under_{job.max_price_czk}_czk": bool(flats) and all(0 < f.price_czk <= job.max_price_czk for f in flats),
        f"all_in_{job.district}": bool(flats) and all(_district(job.district) == _district(f.district) for f in flats),
        "urls_valid_and_unique": bool(flats) and all(_valid_url(u) for u in urls) and len(set(urls)) == len(urls),
    }
    return all(checks.values()), checks
