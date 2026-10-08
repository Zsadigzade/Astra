"""Read-only check of the hosted Masumi payment service. Moves no money, registers nothing.

Run: uv run python scripts/masumi_check.py [--node-only]
Exit 0 means node/configuration checks passed, NOT that a live payment was verified.
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from shared.config import Settings, get_settings  # noqa: E402


def configuration_errors(s: Settings, node_only: bool) -> list[str]:
    errors = []
    try:
        url = urlsplit(s.masumi_payment_url)
        valid_url = (url.scheme in {"http", "https"} and url.hostname and url.port != 0
                     and not url.username and not url.password and not url.query and not url.fragment
                     and url.path.rstrip("/").endswith("/api/v1"))
    except ValueError:
        valid_url = False
    if not valid_url:
        errors.append("MASUMI_PAYMENT_URL must be an HTTP(S) API URL ending in /api/v1, without embedded credentials or query parameters.")
    if not s.masumi_api_key.strip():
        errors.append("MASUMI_API_KEY is missing: use the payment node ADMIN_KEY, not a Sokosumi key.")
    if s.masumi_network != "Preprod":
        errors.append("MASUMI_NETWORK must be Preprod for this demo.")
    if not node_only:
        if not s.masumi_agent_id.strip():
            errors.append("MASUMI_AGENT_ID is missing: register Viktor with Dynamic pricing in the admin UI.")
        if not re.fullmatch(r"[0-9a-fA-F]{56}", s.seller_vkey):
            errors.append("SELLER_VKEY must be the selling wallet's 56-character hexadecimal vkey from the admin UI.")
    return errors


async def check(s: Settings, c: httpx.AsyncClient, node_only: bool = False) -> int:
    errors = configuration_errors(s, node_only)
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1

    base, headers = s.masumi_payment_url.rstrip("/"), {"token": s.masumi_api_key}
    try:
        health = await get_data(c, base, "/health", headers)
        if health.get("status") != "ok":
            raise CheckError("/health did not report status ok.")
        print("OK: node health")

        # Read only the public source listing, never /payment-source-extended (mnemonics).
        sources = []
        cursor = None
        seen = set()
        while True:
            params = {"take": 100}
            if cursor:
                params["cursorId"] = cursor
            data = await get_data(c, base, "/payment-source", headers, params)
            page = data.get("PaymentSources")
            if not isinstance(page, list) or any(not isinstance(src, dict) for src in page):
                raise CheckError("/payment-source returned an unexpected schema.")
            sources.extend(page)
            if len(page) < 100:
                break
            cursor = page[-1].get("id")
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise CheckError("/payment-source pagination did not advance.")
            seen.add(cursor)
        matching = [src for src in sources if src.get("network") == "Preprod"
                    and (src.get("paymentSourceType") or src.get("paymentType"))
                    in {"Web3CardanoV1", "Web3CardanoV2"}
                    and src.get("smartContractAddress")]
        if not matching:
            print("FAIL: no Preprod Cardano payment source with a contract; configure one in the admin UI.")
            return 1
        print(f"OK: {len(matching)} Preprod Cardano payment source(s)")
    except httpx.RequestError:
        # Exception strings and server bodies may echo credentials; do not print them.
        print("FAIL: cannot reach the node; check its URL, deployment logs and network connection.")
        return 1
    except CheckError as error:
        print(f"FAIL: {error}")
        return 1

    print("PASS: node checks" if node_only else "PASS: node and local seller configuration checks")
    print("Not checked: on-chain registration, Dynamic pricing, wallet funding, or a live escrow.")
    if node_only:
        print("Next: register Viktor, set MASUMI_AGENT_ID and SELLER_VKEY, then rerun without --node-only.")
    else:
        print("Next: confirm registration and both wallet balances in the admin UI before live Act 1.")
    if s.payments_mode != "masumi":
        print("Astra payments remain SIMULATED; set PAYMENTS_MODE=masumi only when ready for live Preprod.")
    return 0


class CheckError(Exception):
    pass


async def get_data(c, base, path, headers, params=None) -> dict:
    r = await c.get(f"{base}{path}", headers=headers, params=params)
    if r.status_code != 200:
        hint = " Check MASUMI_API_KEY and its permissions." if r.status_code in {401, 403} else " Check the deployment and /api/v1 URL."
        raise CheckError(f"{path} returned HTTP {r.status_code}.{hint}")
    try:
        body = r.json()
    except ValueError:
        raise CheckError(f"{path} returned non-JSON data; check the /api/v1 URL.") from None
    if not isinstance(body, dict) or body.get("status") != "success" or not isinstance(body.get("data"), dict):
        raise CheckError(f"{path} returned an unexpected Masumi response.")
    return body["data"]


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-only", action="store_true", help="check the node before registering Viktor")
    args = parser.parse_args()
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as c:
        return await check(get_settings(), c, node_only=args.node_only)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
