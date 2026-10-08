"""One bounded live run to validate and save genuine rentals for the demo.

Run: uv run python scripts/scrape_flats.py [--count 20] [--run-id EXISTING_RUN]
Uses up to APIFY_MAX_ITEMS=200 results (check Actor pricing before running).
Fails without a token; never substitutes cached or sample data for a live check.
With --run-id, reads an existing successful run without starting another paid run.
"""

import argparse
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.core.models import JobSpec
from app.seller.apify import ApifyError, recover_run, save_cache, scrape


def print_provenance(run_id: str | None, dataset_id: str | None) -> None:
    if run_id:
        print(f"Run: https://console.apify.com/actors/runs/{run_id}")
    if dataset_id:
        print(f"Dataset: https://console.apify.com/storage/datasets/{dataset_id}")


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--max-price", type=int, default=25_000)
    parser.add_argument("--run-id", help="Recover an existing successful run; no new Actor run")
    args = parser.parse_args()
    settings = Settings()
    job = JobSpec(count=args.count, max_price_czk=args.max_price)
    result = None
    try:
        result = (await recover_run(job, settings, args.run_id) if args.run_id
                  else await scrape(job, settings))
        save_cache(job, result, settings)
    except (ApifyError, OSError) as exc:
        print(f"Rental {'recovery' if args.run_id else 'scrape'} failed: {exc if isinstance(exc, ApifyError) else 'cannot save offline cache'}")
        run_id = result.run_id if result is not None else getattr(exc, "run_id", None)
        dataset_id = result.dataset_id if result is not None else getattr(exc, "dataset_id", None)
        print_provenance(run_id, dataset_id)
        if run_id:
            print(f"Reuse this run without starting another: --run-id {run_id} --count {args.count} --max-price {args.max_price}")
        return 1
    print(f"Saved {len(result.flats)} real rentals at {result.fetched_at}")
    print(f"Cache: {settings.apify_cache_path}")
    print_provenance(result.run_id, result.dataset_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
