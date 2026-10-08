"""Read-only check of the hosted Masumi payment service. Moves no money, registers nothing.

Run: uv run python scripts/masumi_check.py
Prints: health, payment sources (V1/V2, network), and which .env names are still empty.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from shared.config import get_settings  # noqa: E402


async def main() -> int:
    s = get_settings()
    if not s.masumi_payment_url or "localhost" in s.masumi_payment_url:
        print(f"MASUMI_PAYMENT_URL not set to the hosted service yet ({s.masumi_payment_url!r}).")
        return 1
    base, headers = s.masumi_payment_url.rstrip("/"), {"token": s.masumi_api_key}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{base}/health")
        print(f"/health -> {r.status_code} {r.text[:200]}")
        if r.is_error:
            return 1
        r = await c.get(f"{base}/payment-source", headers=headers, params={"take": 10})
        print(f"/payment-source -> {r.status_code}")
        if r.is_error:
            print(r.text[:300])
            return 1
        sources = (r.json().get("data") or {}).get("PaymentSources", [])
        for src in sources:
            print(f"- {src.get('network')} {src.get('paymentSourceType')} contract={src.get('smartContractAddress')}")
        if not sources:
            print("no payment sources: create one in the admin UI (Preprod)")
        # Wallet vkeys: copy from the admin UI. The extended endpoint carries mnemonics; we never call it.
    missing = [n for n, v in {"MASUMI_API_KEY": s.masumi_api_key, "MASUMI_AGENT_ID": s.masumi_agent_id,
                              "SELLER_VKEY": s.seller_vkey}.items() if not v]
    print("still empty in .env:", ", ".join(missing) or "nothing")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
