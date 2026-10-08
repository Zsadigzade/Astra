"""The actual work Viktor sells: Prague flats (owner: murad).

APIFY_MODE=sample returns canned flats, labelled source="sample" (UI must show it).
APIFY_MODE=apify is TODO: run a real-estate actor with APIFY_TOKEN and map items to Flat.
"""

from shared.config import Settings
from shared.models import DemoMode, Flat, JobResult, JobSpec

STREETS = ["Milady Horákové", "Dukelských hrdinů", "Kamenická", "Letohradská", "Šimáčkova",
           "Komunardů", "Veletržní", "Jana Zajíce", "Ovenecká", "Tusarova"]
AREAS = ["Holešovice", "Letná", "Bubeneč"]


def sample_flats(job: JobSpec) -> list[Flat]:
    return [
        Flat(
            title=f"{1 + i % 3}+kk, {STREETS[i % len(STREETS)]}, {AREAS[i % len(AREAS)]}",
            price_czk=min(job.max_price_czk, 16_500 + (i * 437) % 8_000),
            district=f"{job.district} - {AREAS[i % len(AREAS)]}",
            url=f"https://example.invalid/sample/flat-{i + 1}",
        )
        for i in range(job.count)
    ]


def junk_flats() -> list[Flat]:
    """STAGED Act 4: garbage delivery the verifier must reject."""
    return [Flat(title="Luxury villa (trust me)", price_czk=99_999, district="Praha 10", url="") for _ in range(3)]


async def scrape_apify(job: JobSpec, settings: Settings) -> list[Flat]:
    raise NotImplementedError("TODO(murad): call an Apify real-estate actor, map results to Flat")


async def run_job(job: JobSpec, mode: DemoMode, settings: Settings) -> JobResult:
    if mode == DemoMode.junk:
        return JobResult(flats=junk_flats(), source="sample")
    if settings.apify_mode == "apify":
        return JobResult(flats=await scrape_apify(job, settings), source="apify")
    return JobResult(flats=sample_flats(job), source="sample")
