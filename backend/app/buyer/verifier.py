"""Checks a delivery against the job spec. Hard checks only; an LLM judge can be added later."""

from app.core.models import JobResult, JobSpec


def verify(result: JobResult | None, job: JobSpec) -> tuple[bool, dict[str, bool]]:
    flats = result.flats if result else []
    urls = [f.url for f in flats]
    checks = {
        "has_result": result is not None,
        f"at_least_{job.count}_flats": len(flats) >= job.count,
        f"all_under_{job.max_price_czk}_czk": bool(flats) and all(f.price_czk <= job.max_price_czk for f in flats),
        f"all_in_{job.district}": bool(flats) and all(job.district.lower() in f.district.lower() for f in flats),
        "urls_valid_and_unique": bool(flats) and all(u.startswith("http") for u in urls) and len(set(urls)) == len(urls),
    }
    return all(checks.values()), checks
