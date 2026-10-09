"""Checks a delivery against the job spec using deterministic rules."""

import re
from urllib.parse import urlsplit

from app.core.models import JobResult, JobSpec


def _valid_url(url: str) -> bool:
    # urlsplit strips leading C0 controls and embedded tabs/newlines. Validate
    # the original delivery so malformed links cannot authorize a release.
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url):
        return False
    try:
        parsed = urlsplit(url)
        # Accessing .port performs validation that urlsplit itself defers.
        port = parsed.port
        return (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                and (port is None or 0 < port <= 65535))
    except ValueError:
        return False


def _district(value: str) -> str:
    # Both the sample and Apify adapters append locality after a dash.
    normalized = " ".join(value.casefold().split())
    for separator in (" - ", " — ", " – "):
        normalized = normalized.split(separator, 1)[0]
    return normalized


# The writer saying it could not do the job (e.g. web search was unavailable) is not a delivered answer.
_REFUSAL = re.compile(
    r"web (search|access|browsing) (is |was |were )?(unavailable|not available|disabled|failed)"
    r"|(unavailable|not available|disabled) in this (session|environment)"
    r"|(couldn.t|could not|can.t|cannot|unable to) (access|use|run|reach) (the )?(web|internet|web search|live)"
    r"|(couldn.t|could not|can.t|cannot|unable to) (verify|find|provide) (the )?(current|live|latest|newest)", re.IGNORECASE)
_PLACEHOLDER = re.compile(r"lorem ipsum|\basdf|\btodo\b|\bplaceholder\b|^\W*(n/?a|none|null|tbd)\W*$", re.IGNORECASE)


def verify_answer(result: JobResult | None) -> tuple[bool, dict[str, bool]]:
    """Rule checks for a general answer. They catch missing, empty, absurdly long or placeholder text.
    They do not prove the answer is correct: that is why the UI labels it an AI answer, not verified data."""
    text = (result.answer or "").strip() if result else ""
    checks = {
        "has_result": result is not None and result.kind == "general",
        "has_answer": sum(c.isalnum() for c in text) >= 2,
        "reasonable_length": 0 < len(text) <= 4000,
        "not_a_placeholder": bool(text) and not _PLACEHOLDER.search(text),
        "not_a_refusal": not _REFUSAL.search(text),
        "sources_valid": result is None or all(isinstance(u, str) and u.lower().startswith("https://")
                                               for u in [*result.sources, *(i.url for i in result.items)]),
    }
    return all(checks.values()), checks


def verify(result: JobResult | None, job: JobSpec) -> tuple[bool, dict[str, bool]]:
    if getattr(job, "kind", "rental") == "general":
        return verify_answer(result)
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
