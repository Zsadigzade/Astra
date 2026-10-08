"""One bounded live run to validate and save genuine rentals for the demo.

Run: uv run python scripts/scrape_flats.py [--count 20]
Uses up to APIFY_MAX_ITEMS=200 results (check Actor pricing before running).
Fails without a token; never substitutes cached or sample data for a live check.
"""

import argparse
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.core.models import JobSpec
from app.seller.apify import ApifyError, save_cache, scrape


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--max-price", type=int, default=25_000)
    args = parser.parse_args()
    settings = Settings()
    job = JobSpec(count=args.count, max_price_czk=args.max_price)
    try:
        result = await scrape(job, settings)
        save_cache(job, result, settings)
    except (ApifyError, OSError) as exc:
        print(f"Live scrape failed: {exc if isinstance(exc, ApifyError) else 'cannot save offline cache'}")
        return 1
    print(f"Saved {len(result.flats)} real rentals at {result.fetched_at}")
    print(f"Cache: {settings.apify_cache_path}")
    print(f"Run: https://console.apify.com/actors/runs/{result.run_id}")
    print(f"Dataset: https://console.apify.com/storage/datasets/{result.dataset_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
