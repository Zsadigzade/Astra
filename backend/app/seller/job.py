"""The actual work Viktor sells: Prague flats.

APIFY_MODE=sample returns canned flats, labelled source="sample" (UI must show it).
APIFY_MODE=apify runs a real rental Actor; cached uses a matching saved real scrape.
"""

from app.core.config import Settings
from app.core.models import DemoMode, Flat, JobResult, JobSpec
from app.seller.apify import rental_result, scrape

STREETS = ["Milady Horákové", "Dukelských hrdinů", "Kamenická", "Letohradská", "Šimáčkova",
           "Komunardů", "Veletržní", "Jana Zajíce", "Ovenecká", "Tusarova"]
AREAS = ["Holešovice", "Letná", "Bubeneč"]  # Praha 7
AREAS_BY_DISTRICT = {
    1: ["Staré Město", "Malá Strana", "Josefov"], 2: ["Vinohrady", "Vyšehrad", "Nové Město"],
    3: ["Žižkov", "Vinohrady", "Olšany"], 4: ["Nusle", "Podolí", "Krč"], 5: ["Smíchov", "Košíře", "Motol"],
    6: ["Dejvice", "Břevnov", "Vokovice"], 7: AREAS, 8: ["Karlín", "Libeň", "Kobylisy"],
    9: ["Vysočany", "Prosek", "Střížkov"], 10: ["Vršovice", "Strašnice", "Záběhlice"],
}


def _areas(district: str) -> list[str]:
    digits = "".join(c for c in district if c.isdigit())
    return AREAS_BY_DISTRICT.get(int(digits), [district]) if digits else [district]


def sample_flats(job: JobSpec) -> list[Flat]:
    areas = _areas(job.district)
    return [
        Flat(
            title=f"{1 + i % 3}+kk, {STREETS[i % len(STREETS)]}, {areas[i % len(areas)]}",
            price_czk=min(job.max_price_czk, 16_500 + (i * 437) % 8_000),
            district=f"{job.district} - {areas[i % len(areas)]}",
            url=f"https://example.invalid/sample/flat-{i + 1}",
        )
        for i in range(job.count)
    ]


def junk_flats() -> list[Flat]:
    """STAGED Act 4: garbage delivery the verifier must reject."""
    return [Flat(title="Luxury villa (trust me)", price_czk=99_999, district="Praha 10", url="") for _ in range(3)]


async def scrape_apify(job: JobSpec, settings: Settings) -> list[Flat]:
    return (await scrape(job, settings)).flats


async def run_job(job: JobSpec, mode: DemoMode, settings: Settings) -> JobResult:
    if mode == DemoMode.junk:
        return JobResult(flats=junk_flats(), source="sample")
    if settings.apify_mode in {"apify", "cached"}:
        return await rental_result(job, settings)
    if settings.apify_mode != "sample":
        raise ValueError("APIFY_MODE must be sample, apify or cached")
    return JobResult(flats=sample_flats(job), source="sample")
